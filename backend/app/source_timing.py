"""Decoder provenance for new normalizations, separate from evaluation time.

FFmpeg's encoder-pre statistics carry input frame metadata through fps/drop/dup.
No source position is inferred from average frame rate or image similarity.
"""

import hashlib
import re
from fractions import Fraction
from pathlib import Path
from typing import Any


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def build_timing(
    source: Path,
    normalized: Path,
    log: str,
    statistics: str,
    segment_start_s: float,
    segment_duration_s: float | None,
    filter_chain: str,
    ffmpeg_version: str,
) -> dict[str, Any]:
    bases = re.findall(r"showinfo@source[^\n]*config in time_base: (\d+/\d+)", log)
    decoded = re.findall(r"showinfo@source[^\n]*\bn:\s*(\d+)\s+pts:\s*(-?\d+)", log)
    if not bases or len(set(bases)) != 1 or not decoded:
        raise ValueError("Source presentation timestamps unavailable or discontinuous time base")
    base = Fraction(bases[0])
    source_frames = [{"index": int(n), "pts": int(pts)} for n, pts in decoded]
    if [f["index"] for f in source_frames] != list(range(len(source_frames))):
        raise ValueError("Incomplete source frame inventory")
    if any(b["pts"] <= a["pts"] for a, b in zip(source_frames, source_frames[1:], strict=False)):
        raise ValueError("Ambiguous/nonmonotonic source PTS; normalization rejected")
    frames: list[dict[str, Any]] = []
    for line in statistics.splitlines():
        n, ni, tb, pts, tbi, ptsi = line.split()
        index, original = int(n), int(ni)
        if (
            index != len(frames)
            or original < 0
            or original >= len(source_frames)
            or Fraction(tbi) != base
            or source_frames[original]["pts"] != int(ptsi)
            or Fraction(tb) * int(pts) != Fraction(index, 24)
        ):
            raise ValueError(
                "Encoder input provenance does not match decoded source/24fps timeline"
            )
        frames.append(
            {
                "normalized_index": index,
                "normalized_time_s": index / 24,
                "source_index": original,
                "source_pts": int(ptsi),
                "source_time_s": float(Fraction(ptsi) * base),
            }
        )
    if not frames:
        raise ValueError("No normalized frames have source provenance")
    return {
        "version": "1.0",
        "method": "ffmpeg_decoder_frame_metadata",
        "source_sha256": digest(source),
        "normalized_sha256": digest(normalized),
        "source_time_base": bases[0],
        "source_start_time_s": float(source_frames[0]["pts"] * base),
        "segment_start_s": segment_start_s,
        "segment_duration_s": segment_duration_s,
        "parent_source_offset_s": None,
        "parent_source_note": "Mapping refers only to exact upload bytes; prior edits are unknown.",
        "normalized_time_base": "1/24",
        "filter_chain": filter_chain,
        "ffmpeg_version": ffmpeg_version,
        "source_frames": source_frames,
        "frames": frames,
    }
