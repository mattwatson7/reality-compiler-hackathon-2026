import json
import math
import os
import shutil
import subprocess
from pathlib import Path

import cv2
import imageio_ffmpeg

from backend.app.source_timing import build_timing


class InvalidMedia(ValueError):
    pass


def ffmpeg_binary() -> str:
    return (
        os.getenv("FFMPEG_BINARY") or shutil.which("ffmpeg") or str(imageio_ffmpeg.get_ffmpeg_exe())
    )


def probe_video(path: Path, max_duration_s: int) -> float:
    try:
        with path.open("rb") as source:
            header = source.read(32)
    except OSError as exc:
        raise InvalidMedia("Video file is unavailable") from exc
    # Reject text playlists before any decoder can follow referenced URLs/paths.
    if not (
        header[4:8] == b"ftyp"
        or header[:4] == b"\x1a\x45\xdf\xa3"
        or (header[:4] == b"RIFF" and header[8:12] == b"AVI ")
    ):
        raise InvalidMedia("Expected an MP4/MOV, WebM or AVI video container")
    capture = cv2.VideoCapture(str(path))
    try:
        fps = capture.get(cv2.CAP_PROP_FPS)
        count = capture.get(cv2.CAP_PROP_FRAME_COUNT)
        width, height = (
            capture.get(cv2.CAP_PROP_FRAME_WIDTH),
            capture.get(cv2.CAP_PROP_FRAME_HEIGHT),
        )
        if not all(math.isfinite(value) and value > 0 for value in (fps, count, width, height)):
            raise InvalidMedia("Video has no usable frame rate, dimensions or duration")
        duration = count / fps
        if duration > max_duration_s or max(width, height) > 4096:
            raise InvalidMedia(f"Video exceeds {max_duration_s}s or 4096px dimension limit")
        ok, frame = capture.read()
        if not ok or frame is None:
            raise InvalidMedia("Video does not contain decodable frames")
        return duration
    finally:
        capture.release()


def normalize_video(
    source: Path,
    destination: Path,
    max_duration_s: int,
    *,
    local_cv: bool = False,
    segment_start_s: float = 0,
    segment_duration_s: float | None = None,
) -> float:
    probe_video(source, max_duration_s)
    if (
        not math.isfinite(segment_start_s)
        or segment_start_s < 0
        or (
            segment_duration_s is not None
            and (not math.isfinite(segment_duration_s) or segment_duration_s <= 0)
        )
    ):
        raise InvalidMedia("Invalid normalization segment")
    statistics = destination.with_suffix(".stats.tmp")
    timing_path = destination.with_suffix(".timing.json")
    scale = (
        "scale=w=1280:h=720:force_original_aspect_ratio=decrease:force_divisible_by=2"
        if local_cv
        else "scale=trunc(min(1280\\,iw)/2)*2:-2"
    )
    trim = f"trim=start={segment_start_s}"
    if segment_duration_s is not None:
        trim += f":end={segment_start_s + segment_duration_s}"
    filters = (
        "showinfo@source=checksum=0,setpts=PTS-STARTPTS,"
        + trim
        + ",setpts=PTS-STARTPTS,fps=fps=24:round=near:eof_action=round,"
        + scale
    )
    try:
        completed = subprocess.run(
            [
                ffmpeg_binary(),
                "-nostdin",
                "-v",
                "info",
                "-y",
                "-threads",
                "2",
                "-protocol_whitelist",
                "file,pipe",
                "-copyts",
                "-i",
                str(source),
                "-map",
                "0:v:0",
                "-an",
                "-t",
                str(max_duration_s + 1),
                "-vf",
                filters,
                "-fps_mode",
                "passthrough",
                "-stats_enc_pre",
                str(statistics),
                "-stats_enc_pre_fmt",
                "{n} {ni} {tb} {pts} {tbi} {ptsi}",
                "-c:v",
                "libx264",
                "-threads",
                "2",
                "-preset",
                "fast",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                str(destination),
            ],
            check=True,
            capture_output=True,
            timeout=120,
        )
        duration = probe_video(destination, max_duration_s)
        log = completed.stderr.decode(errors="replace")
        timing = build_timing(
            source,
            destination,
            log,
            statistics.read_text(),
            segment_start_s,
            segment_duration_s,
            filters,
            log.splitlines()[0],
        )
        capture = cv2.VideoCapture(str(destination))
        try:
            if int(capture.get(cv2.CAP_PROP_FRAME_COUNT)) != len(timing["frames"]):
                raise ValueError("Encoded frame count differs from source timing map")
        finally:
            capture.release()
        timing_path.write_text(json.dumps(timing, sort_keys=True), encoding="utf-8")
        return duration
    except (subprocess.SubprocessError, OSError, ValueError) as exc:
        destination.unlink(missing_ok=True)
        timing_path.unlink(missing_ok=True)
        raise InvalidMedia("Video could not be normalized to browser-playable MP4") from exc
    finally:
        statistics.unlink(missing_ok=True)
