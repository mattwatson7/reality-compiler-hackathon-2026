"""Hosted SAM 3.1 contract adapter; live inference remains separately gated.

Contract checked 2026-10-27: dev.meta.ai/docs/sam/{segmenting,reading-segmentation}
and github.com/meta-models/meta-sam/blob/main/protocol/sam3.md. The bounded
one-bit arithmetic codec follows that protocol, validated against its synthetic
conformance vector. Lossless masks are deliberately rejected rather than guessed.
No credentials, network implementation or final verdict logic belong here.
"""

import base64
import math
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import cv2
import numpy as np

from backend.app.perception import (
    Box,
    Initialization,
    VisualSample,
    VisualTrack,
    inspect_video,
    validate_selection,
)
from backend.app.schemas import TaskGraph

MODEL = "sam-3.1"
MAX_TEXT_BYTES = 8_000_000
MAX_TOTAL_PIXELS = 32_000_000
MAX_MASK_PIXELS = 1280 * 720
MASK32 = (1 << 32) - 1
ALPHABET = "!#$%&'()*+-./0123456789:=?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[]^_`abcdefghijklmnopqrstuvwxyz{"
DIGITS = {character: index for index, character in enumerate(ALPHABET)}


class SAMContractError(ValueError):
    """Safe diagnostics contain no raw model output, video or credentials."""


class SAMTransport(Protocol):
    def dispatch(
        self, path: str, body: dict[str, Any], *, model: str, upper_bound_microusd: int
    ) -> dict[str, Any]: ...


def _pack(data: bytes) -> str:
    def digits(value: int, count: int) -> str:
        result = []
        for _ in range(count):
            value, remainder = divmod(value, 85)
            result.append(ALPHABET[remainder])
        if value:
            raise SAMContractError("Mask packed integer exceeds format bounds")
        return "".join(reversed(result))

    packed = digits(len(data), 5)
    for index in range(0, len(data), 4):
        chunk = data[index : index + 4]
        encoded = digits(int.from_bytes(chunk.ljust(4, b"\0"), "big"), 5)
        packed += encoded if len(chunk) == 4 else encoded[: len(chunk) + 1]
    return packed


def _unpack(text: str) -> bytes:
    if len(text) < 5 or len(text) > MAX_TEXT_BYTES:
        raise SAMContractError("Mask packed size is invalid")

    def number(group: str) -> int:
        value = 0
        for character in group:
            if character not in DIGITS:
                raise SAMContractError("Mask alphabet is invalid")
            value = value * 85 + DIGITS[character]
        return value

    length = number(text[:5])
    if not 4 <= length <= MAX_MASK_PIXELS * 2:
        raise SAMContractError("Mask declared byte length exceeds limit")
    full, tail = divmod(length, 4)
    if len(text) != 5 + full * 5 + (tail + 1 if tail else 0):
        raise SAMContractError("Mask length prefix does not match payload")
    data = bytearray()
    for index in range(5, len(text), 5):
        group = text[index : index + 5]
        padded = group + ALPHABET[84] * (5 - len(group))
        value = number(padded)
        if value > MASK32:
            raise SAMContractError("Mask packed value is out of range")
        data.extend(value.to_bytes(4, "big")[: min(4, length - len(data))])
    if _pack(bytes(data)) != text:
        raise SAMContractError("Mask payload is noncanonical")
    return bytes(data)


def _context(padded: bytearray, position: int, stride: int) -> int:
    # The protocol's 12-neighbour causal context, from left/above/above-above.
    offsets = [
        -1,
        -2,
        -stride - 2,
        -stride - 1,
        -stride,
        -stride + 1,
        -stride + 2,
        -2 * stride - 2,
        -2 * stride - 1,
        -2 * stride,
        -2 * stride + 1,
        -2 * stride + 2,
    ]
    return sum(padded[position + offset] << bit for bit, offset in enumerate(offsets))


def _arithmetic(data: bytes, width: int, height: int, *, encode: bool, deadline: float) -> bytes:
    """Adaptive binary range coding with unsigned 32-bit normalization."""
    low, interval, code, cursor = 0, MASK32, 0, 4
    output = bytearray()
    if not encode:
        if len(data) < 4:
            raise SAMContractError("Mask arithmetic finalization is missing")
        code = int.from_bytes(data[:4], "big")
    counts = [[1, 1] for _ in range(4096)]
    stride = width + 4
    pixels = bytearray(stride * (height + 2))
    for y in range(height):
        if time.monotonic() > deadline:
            raise SAMContractError("Mask decoding exceeds CPU time bound")
        for x in range(width):
            position = (y + 2) * stride + x + 2
            count = counts[_context(pixels, position, stride)]
            zero, one = count
            scale = interval // (zero + one)
            if scale == 0:
                raise SAMContractError("Mask arithmetic state is invalid")
            if encode:
                bit = data[y * width + x]
            else:
                frequency = min(zero + one - 1, ((code - low) & MASK32) // scale)
                bit = int(frequency >= zero)
                output.append(bit)
            low = (low + scale * (zero if bit else 0)) & MASK32
            interval = scale * (one if bit else zero)
            while True:
                if (low ^ ((low + interval) & MASK32)) < (1 << 24):
                    pass
                elif interval < (1 << 16):
                    interval = (-low) & ((1 << 16) - 1)
                else:
                    break
                if encode:
                    output.append(low >> 24)
                else:
                    if cursor >= len(data):
                        raise SAMContractError("Mask arithmetic payload is truncated")
                    code = ((code << 8) | data[cursor]) & MASK32
                    cursor += 1
                low = (low << 8) & MASK32
                interval = (interval << 8) & MASK32
            pixels[position] = bit
            count[bit] += 14
            if sum(count) >= 4096:
                count[0] = max(1, count[0] >> 1)
                count[1] = max(1, count[1] >> 1)
    if encode:
        output.extend(low.to_bytes(4, "big"))
    return bytes(output)


def decode_one_bit(payload: str, width: int, height: int) -> Any:
    if not (
        type(width) is int
        and type(height) is int
        and 0 < width <= 1280
        and 0 < height <= 720
        and width * height <= MAX_MASK_PIXELS
    ):
        raise SAMContractError("Mask raster dimensions exceed local bounds")
    if not payload.startswith("!"):
        raise SAMContractError("Only documented one_bit box-prompt masks are supported")
    packed = _unpack(payload[1:])
    deadline = time.monotonic() + 15
    raster = _arithmetic(packed, width, height, encode=False, deadline=deadline)
    if "!" + _pack(_arithmetic(raster, width, height, encode=True, deadline=deadline)) != payload:
        raise SAMContractError("Mask arithmetic finalization or canonical form is invalid")
    return np.frombuffer(raster, dtype=np.uint8).reshape(height, width)


@dataclass
class MaskRecord:
    object_id: int
    x: int
    y: int
    width: int
    height: int
    mask: Any
    confidence: float


def _fields(body: str, required: set[str]) -> dict[str, str]:
    result = {}
    for field in body.split(";"):
        name, separator, value = field.partition("=")
        if not separator or name in result or name not in required | {"c"}:
            raise SAMContractError("Segmentation token fields are malformed")
        result[name] = value
    if not required <= result.keys():
        raise SAMContractError("Segmentation token fields are incomplete")
    return result


def _confidence(fields: dict[str, str]) -> float:
    try:
        value = float(fields.get("c", "nan"))
    except ValueError:
        return 0.0
    return value if math.isfinite(value) and 0 <= value <= 1 else 0.0


def parse_segmentation(
    text: str, width: int, height: int, frame_count: int, object_ids: set[int]
) -> dict[int, dict[int, MaskRecord]]:
    if not isinstance(text, str) or len(text.encode("utf-8")) > MAX_TEXT_BYTES:
        raise SAMContractError("Segmentation text exceeds response limit")
    frames: dict[int, dict[int, MaskRecord]] = {}
    total_pixels = 0
    started = time.monotonic()
    for line in text.splitlines():
        if not line:
            continue
        header = re.match(r"<([0-9]+)f>", line)
        if not header:
            raise SAMContractError("Segmentation frame marker is malformed")
        if len(header[1]) > 4:
            raise SAMContractError("Segmentation frame index exceeds local bounds")
        index = int(header[1])
        if index >= frame_count or index in frames or len(frames) >= 720:
            raise SAMContractError("Segmentation frame index is duplicate or out of range")
        records: dict[int, MaskRecord] = {}
        position = header.end()
        while position < len(line):
            match = re.match(r"([0-9]+)<\|box;([^|]+)\|><\|mask;([^|]+)\|>", line[position:])
            if not match:
                raise SAMContractError("Segmentation record is malformed")
            if len(match[1]) > 3:
                raise SAMContractError("Segmentation identity exceeds prompt bounds")
            object_id = int(match[1])
            if object_id not in object_ids or object_id in records:
                raise SAMContractError("Segmentation identity is duplicate or unknown")
            box = _fields(match[2], {"x1", "y1", "x2", "y2", "w", "h"})
            mask = _fields(match[3], {"x", "y", "data"})
            try:
                geometry = [box[k] for k in ("x1", "y1", "x2", "y2", "w", "h")]
                if any(re.fullmatch(r"[0-9]+", v) is None for v in geometry):
                    raise ValueError
                x1, y1, x2, y2, frame_w, frame_h = map(int, geometry)
                mh, mw, payload = mask["data"].split(",", 2)
                h, w = int(mh), int(mw)
                if not (
                    frame_w == width
                    and frame_h == height
                    and 0 <= x1 <= x2 < width
                    and 0 <= y1 <= y2 < height
                    and w == x2 - x1 + 1
                    and h == y2 - y1 + 1
                    and mask["x"] == mask["y"] == "0"
                ):
                    raise ValueError
            except (ValueError, KeyError):
                raise SAMContractError("Segmentation mask/box geometry is invalid") from None
            total_pixels += w * h
            if total_pixels > MAX_TOTAL_PIXELS or time.monotonic() - started > 90:
                raise SAMContractError("Segmentation decoding exceeds CPU/pixel bound")
            raster = decode_one_bit(payload, w, h)
            records[object_id] = MaskRecord(
                object_id,
                x1,
                y1,
                w,
                h,
                raster,
                min(_confidence(box), _confidence(mask)),
            )
            position += match.end()
            if position < len(line):
                if line[position] != ",":
                    raise SAMContractError("Segmentation record separator is invalid")
                position += 1
                if position == len(line):
                    raise SAMContractError("Segmentation record is missing after separator")
        if not records:
            raise SAMContractError("Segmentation frame contains no records")
        frames[index] = records
    return frames


def _output_text(response: dict[str, Any]) -> str:
    try:
        if response["model"] != MODEL or response["status"] != "completed":
            raise ValueError
        output = response["output"]
        messages = [item for item in output if item.get("type") == "message"]
        if len(messages) != 1 or any(
            item.get("type") not in {"message", "reasoning"} for item in output
        ):
            raise ValueError
        message = messages[0]
        if message.get("role") != "assistant" or message.get("status", "completed") != "completed":
            raise ValueError
        content = message["content"]
        if len(content) != 1 or content[0]["type"] != "output_text":
            raise ValueError
        text = content[0]["text"]
        if not isinstance(text, str):
            raise ValueError
        return text
    except (KeyError, TypeError, AttributeError, ValueError):
        raise SAMContractError("SAM response incomplete, refused or malformed") from None


class SAMTrackerProvider:
    def __init__(self, initialization: Initialization, transport: SAMTransport) -> None:
        self.initialization = initialization
        self.transport = transport
        self.segmentation_text: str | None = None

    def track(self, video: Path, graph: TaskGraph) -> list[VisualTrack]:
        self.segmentation_text = None
        metadata = inspect_video(video)
        validate_selection(self.initialization, graph, metadata["frame_reference"])
        width, height, count = metadata["width"], metadata["height"], metadata["frame_count"]
        ids = {index + 1: obj.id for index, obj in enumerate(graph.objects)}
        if not 1 <= len(ids) <= 16 or video.stat().st_size > 32_000_000:
            raise SAMContractError("SAM supports 1–16 selected objects and bounded local media")
        prompts = []
        for identifier, object_id in ids.items():
            x1, y1, x2, y2 = self.initialization.objects[object_id].pixels(width, height)
            prompts.append(
                f"{identifier}<|box;x1={x1};y1={y1};x2={x2 - 1};y2={y2 - 1};w={width};h={height}|>"
            )
        body = {
            "model": MODEL,
            "input": [
                {
                    "type": "message",
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": "<0f>" + ",".join(prompts)},
                        {
                            "type": "input_video",
                            "video_url": "data:video/mp4;base64,"
                            + base64.b64encode(video.read_bytes()).decode("ascii"),
                        },
                    ],
                }
            ],
            "stream": False,
            "metadata": {
                "include_confidence": "true",
                "mask_encoding": "one_bit",
                "propagation_direction": "forward",
            },
        }
        # Forward propagation covers each source frame once. Published minimum is
        # 50 billed frames; $0.20/1000 frames = 200 integer micro-USD/frame.
        response = self.transport.dispatch(
            "/v1/responses", body, model=MODEL, upper_bound_microusd=max(50, count) * 200
        )
        frames = parse_segmentation(_output_text(response), width, height, count, set(ids))
        tracks = {
            key: VisualTrack(
                object_id=value,
                source="meta_sam",
                model_id=MODEL,
                provenance="meta.sam-3.1.box_prompt.one_bit.v1",
            )
            for key, value in ids.items()
        }
        lost: dict[int, str] = {}
        conversion_started = time.monotonic()
        for index in range(count):
            if time.monotonic() - conversion_started > 90:
                raise SAMContractError("SAM track conversion exceeds CPU time bound")
            records = frames.get(index, {})
            occupancy = np.zeros((height, width), dtype=np.uint8)
            collisions: set[int] = set()
            full_masks: dict[int, Any] = {}
            for identifier, candidate in records.items():
                full = np.zeros_like(occupancy)
                full[
                    candidate.y : candidate.y + candidate.height,
                    candidate.x : candidate.x + candidate.width,
                ] = candidate.mask
                if np.any(occupancy & full):
                    collisions.add(identifier)
                    collisions.update(k for k, other in full_masks.items() if np.any(other & full))
                occupancy |= full
                full_masks[identifier] = full
            for identifier, track in tracks.items():
                record = records.get(identifier)
                if identifier in collisions:
                    lost.setdefault(identifier, "Masks overlap; identity is ambiguous")
                if record is None:
                    lost.setdefault(
                        identifier, "Missing source-frame mask; identity cannot recover"
                    )
                elif record.confidence < 0.8 or not np.any(record.mask):
                    lost.setdefault(identifier, "Missing/low confidence or empty foreground mask")
                elif record.width / width < 0.01 or record.height / height < 0.01:
                    lost.setdefault(identifier, "Foreground geometry is below the minimum size")
                elif index == 0:
                    prompt = self.initialization.objects[ids[identifier]]
                    x1, y1, x2, y2 = prompt.pixels(width, height)
                    mask = full_masks[identifier]
                    agreement = int(np.count_nonzero(mask[y1:y2, x1:x2])) / max(
                        1, int(np.count_nonzero(mask))
                    )
                    if agreement < 0.5:
                        lost.setdefault(
                            identifier, "First-frame mask disagrees with selected identity"
                        )
                elif track.samples[-1].box is not None:
                    previous = track.samples[-1].box
                    assert previous is not None
                    if (
                        math.hypot(record.x / width - previous.x, record.y / height - previous.y)
                        > 0.2
                    ):
                        lost.setdefault(
                            identifier, "Identity displacement exceeds continuity bound"
                        )
                if identifier in lost:
                    track.samples.append(
                        VisualSample(
                            frame_index=index,
                            time_s=index / metadata["fps"],
                            confidence=0.0,
                            status="ambiguous" if record else "missing",
                            provenance=track.provenance,
                        )
                    )
                    continue
                assert record is not None
                mask = full_masks[identifier]
                box = Box(
                    x=record.x / width,
                    y=record.y / height,
                    width=record.width / width,
                    height=record.height / height,
                )
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                contour = cv2.approxPolyDP(max(contours, key=cv2.contourArea), 2.0, True).reshape(
                    -1, 2
                )
                overlaps = {}
                area = int(np.count_nonzero(mask))
                for region_id, region in self.initialization.regions.items():
                    x1, y1, x2, y2 = region.pixels(width, height)
                    overlaps[region_id] = int(np.count_nonzero(mask[y1:y2, x1:x2])) / area
                track.samples.append(
                    VisualSample(
                        frame_index=index,
                        time_s=index / metadata["fps"],
                        box=box,
                        contour=[(float(x) / width, float(y) / height) for x, y in contour],
                        confidence=record.confidence,
                        status="reliable",
                        region_overlap=overlaps,
                        quality_components={"model_confidence": record.confidence},
                        provenance=track.provenance,
                    )
                )
        for identifier, reason in lost.items():
            track = tracks[identifier]
            start = next(s.time_s for s in track.samples if s.status != "reliable")
            track.diagnostics.append(reason)
            track.invalid_intervals.append(
                {"start_s": start, "end_s": metadata["duration_s"], "reason": reason}
            )
        acknowledge = getattr(self.transport, "acknowledge", None)
        if acknowledge is not None and not lost:
            acknowledge(response)
        # Preserve validated mask geometry, including nondecisive tracking runs.
        # Only the service writes artifacts beneath its internally generated ID.
        self.segmentation_text = _output_text(response)
        return list(tracks.values())
