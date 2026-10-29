"""Bounded, manually initialized color tracking over decoded video pixels.

Quality is a conservative minimum of measured heuristics, not a probability.
No model, network transport, manual event times or identity recovery is used.
"""

import hashlib
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Self, TypedDict

import cv2
import numpy as np
from pydantic import Field, model_validator

from backend.app.schemas import (
    Evidence,
    ObjectVisible,
    Observation,
    RegionTransition,
    StrictModel,
    TaskGraph,
)


class Box(StrictModel):
    x: float = Field(ge=0, le=1, allow_inf_nan=False)
    y: float = Field(ge=0, le=1, allow_inf_nan=False)
    width: float = Field(ge=0.01, le=1, allow_inf_nan=False)
    height: float = Field(ge=0.01, le=1, allow_inf_nan=False)

    @model_validator(mode="after")
    def bounds(self) -> Self:
        if self.x + self.width > 1 + 1e-9 or self.y + self.height > 1 + 1e-9:
            raise ValueError("Selection must lie within the normalized frame")
        return self

    def pixels(self, width: int, height: int) -> tuple[int, int, int, int]:
        return (
            int(self.x * width),
            int(self.y * height),
            min(width, math.ceil((self.x + self.width) * width)),
            min(height, math.ceil((self.y + self.height) * height)),
        )


class Initialization(StrictModel):
    frame_reference: str = Field(min_length=1, max_length=100)
    objects: dict[str, Box] = Field(max_length=30)
    regions: dict[str, Box] = Field(max_length=30)


def validate_selection(initialization: Initialization, graph: TaskGraph, reference: str) -> None:
    initialization = Initialization.model_validate_json(initialization.model_dump_json())
    if initialization.frame_reference != reference:
        raise ValueError("Selections must reference this job's immutable first frame")
    if set(initialization.objects) != {obj.id for obj in graph.objects}:
        raise ValueError("Select each compiled object exactly once")
    if set(initialization.regions) != {region.id for region in graph.regions}:
        raise ValueError("Select each compiled region exactly once")
    boxes = list(initialization.objects.values())
    for i, box in enumerate(boxes):
        for other in boxes[i + 1 :]:
            if max(box.x, other.x) < min(box.x + box.width, other.x + other.width) and max(
                box.y, other.y
            ) < min(box.y + box.height, other.y + other.height):
                raise ValueError("Object selections must not overlap")


class VisualSample(StrictModel):
    frame_index: int = Field(ge=0)
    time_s: float = Field(ge=0, allow_inf_nan=False)
    box: Box | None = None
    contour: list[tuple[float, float]] = Field(default_factory=list)
    quality_components: dict[str, float] = Field(default_factory=dict)
    confidence: float = Field(ge=0, le=1, allow_inf_nan=False)
    status: Literal["reliable", "missing", "ambiguous"]
    region_overlap: dict[str, float] = Field(default_factory=dict)
    provenance: str = "local_cv.fixed_hsv.v1"


class VisualTrack(StrictModel):
    object_id: str
    source: Literal["local_cv", "meta_sam"] = "local_cv"
    model_id: str | None = None
    samples: list[VisualSample] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)
    invalid_intervals: list[dict[str, float | str]] = Field(default_factory=list)
    provenance: str = "local_cv.fixed_hsv.v1"


class VideoMetadata(TypedDict):
    width: int
    height: int
    fps: float
    frame_count: int
    duration_s: float
    last_frame_s: float
    sha256: str
    frame_reference: str


def inspect_video(video: Path) -> VideoMetadata:
    with video.open("rb") as source:
        digest = hashlib.file_digest(source, "sha256").hexdigest()
    cap = cv2.VideoCapture(str(video))
    started = time.monotonic()
    try:
        fps = float(cap.get(cv2.CAP_PROP_FPS))
        width, height = (
            int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        )
        if (
            not cap.isOpened()
            or abs(fps - 24) > 0.01
            or not (0 < width <= 1280 and 0 < height <= 720)
        ):
            raise ValueError("Local CV requires normalized 24 fps video within 1280x720")
        count = 0
        while True:
            ok, _ = cap.read()
            if not ok:
                break
            count += 1
            if count > 720 or time.monotonic() - started > 45:
                raise ValueError("Local CV decode exceeded 30 seconds or wall-time bound")
        if count == 0:
            raise ValueError("No video frames decoded")
        return {
            "width": width,
            "height": height,
            "fps": fps,
            "frame_count": count,
            "duration_s": count / fps,
            "last_frame_s": (count - 1) / fps,
            "sha256": digest,
            "frame_reference": f"{digest}:0",
        }
    finally:
        cap.release()


@dataclass
class Appearance:
    hue: float
    area: int
    aspect: float
    box: Box


def hue_distance(hue: Any, reference: float) -> Any:
    difference = np.abs(hue.astype(float) - reference)
    return np.minimum(difference, 180 - difference)


def learn(frame: Any, box: Box) -> Appearance | None:
    height, width = frame.shape[:2]
    x1, y1, x2, y2 = box.pixels(width, height)
    patch = cv2.cvtColor(frame[y1:y2, x1:x2], cv2.COLOR_BGR2HSV)
    saturated = (patch[:, :, 1] >= 80) & (patch[:, :, 2] >= 40)
    if int(np.count_nonzero(saturated)) < max(24, patch.shape[0] * patch.shape[1] * 0.2):
        return None
    histogram = np.bincount(patch[:, :, 0][saturated], minlength=180)
    peak = int(np.argmax(histogram))
    chosen = saturated & (hue_distance(patch[:, :, 0], peak) <= 10)
    if np.count_nonzero(chosen) / np.count_nonzero(saturated) < 0.65:
        return None
    return Appearance(float(peak), int(np.count_nonzero(chosen)), box.width / box.height, box)


def mask_for(hsv: Any, appearance: Appearance) -> Any:
    mask = (
        (hue_distance(hsv[:, :, 0], appearance.hue) <= 10)
        & (hsv[:, :, 1] >= 80)
        & (hsv[:, :, 2] >= 40)
    ).astype(np.uint8)
    # Opening removes isolated compression noise; never merge disconnected objects.
    return cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), dtype=np.uint8))


class LocalCVTracker:
    def __init__(self, initialization: Initialization) -> None:
        self.initialization = initialization

    def track(self, video: Path, graph: TaskGraph) -> list[VisualTrack]:
        metadata = inspect_video(video)
        validate_selection(self.initialization, graph, metadata["frame_reference"])
        cap = cv2.VideoCapture(str(video))
        tracks = {obj.id: VisualTrack(object_id=obj.id) for obj in graph.objects}
        appearances: dict[str, Appearance | None] = {}
        previous: dict[str, Box] = dict(self.initialization.objects)
        lost: dict[str, str] = {}
        first_gray: Any = None
        started = time.monotonic()
        try:
            for index in range(metadata["frame_count"]):
                ok, frame = cap.read()
                if not ok or time.monotonic() - started > 90:
                    raise ValueError("Tracking decode interrupted or exceeded wall-time bound")
                if index % 2 and index != metadata["frame_count"] - 1:
                    continue
                hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                height, width = frame.shape[:2]
                if index == 0:
                    first_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    appearances = {key: learn(frame, box) for key, box in previous.items()}
                    for key, appearance in appearances.items():
                        if appearance is None:
                            lost[key] = (
                                "Initialization lacks one dominant saturated foreground color"
                            )
                    keys = list(appearances)
                    for i, key in enumerate(keys):
                        for other in keys[i + 1 :]:
                            a, b = appearances[key], appearances[other]
                            if a and b and min(abs(a.hue - b.hue), 180 - abs(a.hue - b.hue)) <= 20:
                                lost[key] = lost[other] = "Object appearance models collide"
                candidates: dict[str, tuple[VisualSample, Any]] = {}
                for key, track in tracks.items():
                    appearance = appearances[key]
                    if key in lost or appearance is None:
                        candidates[key] = (
                            VisualSample(
                                frame_index=index,
                                time_s=index / 24,
                                confidence=0.0,
                                status="missing",
                            ),
                            None,
                        )
                        continue
                    sample, mask, reason = self._sample(
                        frame, hsv, index, appearance, previous[key]
                    )
                    if reason:
                        lost[key] = reason
                        track.diagnostics.append(f"frame {index}: {reason}")
                    candidates[key] = (sample, mask)
                # Shared pixels cannot be assigned to two stable identities.
                keys = list(candidates)
                for i, key in enumerate(keys):
                    for other in keys[i + 1 :]:
                        mask_a, mask_b = candidates[key][1], candidates[other][1]
                        if mask_a is not None and mask_b is not None and np.any(mask_a & mask_b):
                            lost[key] = lost[other] = (
                                "Shared foreground masks make identity ambiguous"
                            )
                exterior = np.ones((height, width), dtype=np.uint8)
                for box in [
                    *self.initialization.objects.values(),
                    *previous.values(),
                    *(s.box for s, _ in candidates.values() if s.box is not None),
                ]:
                    x1, y1, x2, y2 = box.pixels(width, height)
                    exterior[
                        max(0, y1 - 12) : min(height, y2 + 12),
                        max(0, x1 - 12) : min(width, x2 + 12),
                    ] = 0
                difference = cv2.absdiff(first_gray, cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
                camera_quality = 1 - float(
                    np.count_nonzero((difference > 30) & (exterior > 0))
                ) / max(1, int(np.count_nonzero(exterior)))
                if camera_quality < 0.9:
                    for key in tracks:
                        lost[key] = "Scene motion invalidates fixed-camera assumptions"
                for key, (sample, _) in candidates.items():
                    sample.quality_components["static_background"] = camera_quality
                    sample.confidence = min(sample.confidence, camera_quality)
                    if key in lost:
                        sample.status = "ambiguous" if sample.box else "missing"
                        sample.confidence = 0.0
                        # No overlay should visually imply identity after invalidation.
                        sample.box = None
                        sample.contour = []
                        sample.region_overlap = {}
                    elif sample.box:
                        previous[key] = sample.box
                    tracks[key].samples.append(sample)
            for key, track in tracks.items():
                if key in lost:
                    first = next(s for s in track.samples if s.status != "reliable")
                    track.invalid_intervals = [
                        {
                            "start_s": first.time_s,
                            "end_s": metadata["duration_s"],
                            "reason": lost[key],
                        }
                    ]
                    if not track.diagnostics:
                        track.diagnostics.append(lost[key])
            return list(tracks.values())
        finally:
            cap.release()

    def _sample(
        self, frame: Any, hsv: Any, index: int, appearance: Appearance, previous: Box
    ) -> tuple[VisualSample, Any, str | None]:
        height, width = frame.shape[:2]
        mask = mask_for(hsv, appearance)
        count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
        components = [
            i for i in range(1, count) if stats[i, cv2.CC_STAT_AREA] >= appearance.area * 0.3
        ]
        empty = VisualSample(frame_index=index, time_s=index / 24, confidence=0.0, status="missing")
        if len(components) != 1:
            return empty, None, "Missing or competing appearance components"
        component = components[0]
        x, y, w, h, area = (int(v) for v in stats[component])
        region_mask = (labels == component).astype(np.uint8)
        box = Box(x=x / width, y=y / height, width=w / width, height=h / height)
        area_ratio = area / appearance.area
        aspect_ratio = (box.width / box.height) / appearance.aspect
        displacement = math.hypot(box.x - previous.x, box.y - previous.y)
        if not 0.55 <= area_ratio <= 1.8 or not 0.5 <= aspect_ratio <= 2 or displacement > 0.12:
            return empty, None, "Area, shape or displacement violates identity bound"
        contours, _ = cv2.findContours(region_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contour = max(contours, key=cv2.contourArea)
        solidity = cv2.contourArea(contour) / max(1.0, cv2.contourArea(cv2.convexHull(contour)))
        color = 1 - float(np.mean(hue_distance(hsv[:, :, 0][region_mask > 0], appearance.hue))) / 90
        quality = {
            "area_consistency": min(area_ratio, 1 / area_ratio),
            "shape_solidity": float(solidity),
            "appearance_agreement": color,
            "displacement_consistency": max(0.0, 1 - displacement),
        }
        overlaps = {}
        for key, selected in self.initialization.regions.items():
            x1, y1, x2, y2 = selected.pixels(width, height)
            overlaps[key] = float(np.count_nonzero(region_mask[y1:y2, x1:x2])) / area
        points = cv2.approxPolyDP(contour, 2.0, True).reshape(-1, 2)
        sample = VisualSample(
            frame_index=index,
            time_s=index / 24,
            box=box,
            contour=[(float(p[0]) / width, float(p[1]) / height) for p in points],
            quality_components=quality,
            confidence=min(quality.values()),
            status="reliable",
            region_overlap=overlaps,
        )
        if sample.confidence < 0.8:
            sample.status = "ambiguous"
            return sample, region_mask, "Measured quality is below the decisive threshold"
        return sample, region_mask, None


class LocalRegionObserver:
    def __init__(self, initialization: Initialization) -> None:
        self.initialization = initialization

    def observe(
        self, video: Path, graph: TaskGraph, tracks: list[VisualTrack]
    ) -> list[Observation]:
        metadata = inspect_video(video)
        validate_selection(self.initialization, graph, metadata["frame_reference"])
        observations = []
        for track in tracks:
            samples = track.samples
            if (
                not samples
                or samples[0].frame_index != 0
                or samples[-1].frame_index != metadata["frame_count"] - 1
                or any(
                    s.frame_index >= metadata["frame_count"]
                    or not math.isclose(
                        s.time_s, s.frame_index / metadata["fps"], rel_tol=0, abs_tol=1e-6
                    )
                    for s in samples
                )
            ):
                reason = "Sample frame references do not cover the decoded clip"
                track.diagnostics.append(reason)
                track.invalid_intervals.append(
                    {"start_s": 0.0, "end_s": metadata["duration_s"], "reason": reason}
                )
            for region_id in self.initialization.regions:
                observations.extend(self._transitions(track, region_id, graph))
            # Local visibility is conservative sampled image visibility, not
            # object permanence. SAM final-state interpretation stays with Spark
            # to avoid duplicate claims from independent observers.
            if track.source == "local_cv" and (
                bool(samples)
                and not track.invalid_intervals
                and all(s.status == "reliable" and s.box and s.confidence >= 0.8 for s in samples)
                and all(
                    0 < b.time_s - a.time_s <= 0.15
                    for a, b in zip(samples, samples[1:], strict=False)
                )
            ):
                support = samples[-3:]
                for condition in graph.conditions:
                    predicate = condition.predicate
                    if (
                        condition.scope != "final"
                        or condition.observability != "SUPPORTED"
                        or not isinstance(predicate, ObjectVisible)
                        or predicate.object_id != track.object_id
                    ):
                        continue
                    identifier = f"visible_{condition.id}"
                    indices = [s.frame_index for s in support]
                    observations.append(
                        Observation(
                            occurrence_id=identifier,
                            event_id=condition.id,
                            predicate=predicate,
                            start_s=support[0].time_s,
                            end_s=metadata["duration_s"],
                            confidence=min(s.confidence for s in samples),
                            frame_indices=indices,
                            provenance=f"{track.provenance};observer=sampled_visibility.v1",
                            evidence=Evidence(
                                id=identifier,
                                source="local_cv",
                                frame_indices=indices,
                                frame_reference=self.initialization.frame_reference,
                                start_s=support[0].time_s,
                                end_s=metadata["duration_s"],
                                description=(
                                    "Object visible in final samples, including last frame; "
                                    "unbroken sampled identity required. No hidden-state claim."
                                ),
                            ),
                        )
                    )
        return observations

    def _transitions(
        self, track: VisualTrack, region_id: str, graph: TaskGraph
    ) -> list[Observation]:
        observations: list[Observation] = []
        samples = track.samples
        boundary_start: float | None = None
        boundary_uncertain = False
        for sample in samples:
            overlap = sample.region_overlap.get(region_id)
            if overlap is not None and 0.1 < overlap < 0.85:
                if boundary_start is None:
                    boundary_start = sample.time_s
                if sample.time_s - boundary_start > 2:
                    boundary_uncertain = True
            else:
                boundary_start = None
        if boundary_uncertain:
            diagnostic = f"Region {region_id}: boundary dwell >2s prevents decisive uniqueness"
            if diagnostic not in track.diagnostics:
                track.diagnostics.append(diagnostic)
        whole_track_valid = (
            bool(samples)
            and samples[0].frame_index == 0
            and not track.invalid_intervals
            and not boundary_uncertain
            and all(
                s.status == "reliable"
                and math.isfinite(s.confidence)
                and s.confidence >= 0.8
                and region_id in s.region_overlap
                and math.isfinite(s.region_overlap[region_id])
                and 0 <= s.region_overlap[region_id] <= 1
                for s in samples
            )
            and all(
                0 < b.time_s - a.time_s <= 0.15 for a, b in zip(samples, samples[1:], strict=False)
            )
        )
        side: str | None = None
        stable_indices: list[int] = []
        pending_side: str | None = None
        pending: list[int] = []
        for i, sample in enumerate(samples):
            if (
                sample.status != "reliable"
                or region_id not in sample.region_overlap
                or not math.isfinite(sample.region_overlap[region_id])
                or not 0 <= sample.region_overlap[region_id] <= 1
                or (i and sample.time_s - samples[i - 1].time_s > 0.15)
            ):
                side, pending_side, stable_indices, pending = None, None, [], []
                continue
            overlap = sample.region_overlap[region_id]
            current = "outside" if overlap <= 0.1 else "inside" if overlap >= 0.85 else None
            if current is None:
                pending_side, pending = None, []
                continue
            if current == side:
                stable_indices = (stable_indices + [i])[-3:]
                pending_side, pending = None, []
                continue
            if pending_side != current:
                pending_side, pending = current, []
            pending.append(i)
            if len(pending) < 3 or sample.time_s - samples[pending[0]].time_s < 0.15:
                continue
            if side is not None and stable_indices:
                start, end = stable_indices[-1], pending[0]
                support = samples[stable_indices[0] : i + 1]
                usable = whole_track_valid and samples[end].time_s - samples[start].time_s <= 2
                predicate = RegionTransition(
                    type="object_entered_region" if current == "inside" else "object_exited_region",
                    object_id=track.object_id,
                    region_id=region_id,
                )
                matches = [
                    event.id
                    for event in [*graph.events, *graph.conditions]
                    if event.predicate == predicate and event.observability == "SUPPORTED"
                ]
                if not matches:
                    matches = [f"unmatched_{track.object_id}_{region_id}"[:64]]
                occurrence = f"cv_{track.object_id}_{region_id}_{start}_{end}"[:56]
                quality = min(s.confidence for s in support)
                for match_index, event_id in enumerate(matches):
                    identifier = f"{occurrence}_{match_index}"
                    observations.append(
                        Observation(
                            occurrence_id=identifier,
                            event_id=event_id,
                            predicate=predicate,
                            start_s=samples[start].time_s,
                            end_s=samples[end].time_s,
                            confidence=quality,
                            usable=usable,
                            frame_indices=[s.frame_index for s in support],
                            quality_components={"minimum_support_quality": quality},
                            provenance=f"{track.provenance};observer=mask_hysteresis.v1",
                            model_id=track.model_id,
                            evidence=Evidence(
                                id=identifier,
                                start_s=support[0].time_s,
                                end_s=support[-1].time_s,
                                source=track.source,
                                model_id=track.model_id,
                                frame_indices=[s.frame_index for s in support],
                                frame_reference=self.initialization.frame_reference,
                                description=(
                                    f"{predicate.type}: {track.object_id} / {region_id}; "
                                    "mask overlap <=10% outside, >=85% inside; three samples "
                                    "spanning >=0.15s; quality=min measured support components. "
                                    + (
                                        ""
                                        if usable
                                        else "UNUSABLE: identity/gap or boundary dwell uncertainty."
                                    )
                                ),
                            ),
                        )
                    )
            side, stable_indices = current, pending[-3:]
            pending_side, pending = None, []
        return observations
