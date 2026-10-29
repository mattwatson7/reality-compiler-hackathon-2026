"""Exercise real ffmpeg timestamp conversion; no provider calls."""

import json
import subprocess
from fractions import Fraction
from pathlib import Path

import cv2
import pytest

from backend.app.media import ffmpeg_binary, normalize_video


def make_video(path: Path, rate: str, duration: str = "1", *, vfr: bool = False) -> None:
    subprocess.run(
        [
            ffmpeg_binary(),
            "-nostdin",
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"testsrc2=size=160x120:rate={rate}:duration={duration}",
            *(
                [
                    "-vf",
                    "select='if(lt(n,15),not(mod(n,2)),not(mod(n,3)))',setpts=PTS+2/TB",
                    "-fps_mode",
                    "vfr",
                ]
                if vfr
                else []
            ),
            "-c:v",
            "libx264",
            "-threads",
            "2",
            str(path),
        ],
        check=True,
        capture_output=True,
    )


@pytest.mark.parametrize("rate", ["25", "30000/1001", "30", "12"])
def test_exact_decoder_attribution_and_terminal_bounds(tmp_path: Path, rate: str) -> None:
    source, dest = tmp_path / "input.mp4", tmp_path / "video.mp4"
    make_video(source, rate)
    normalize_video(source, dest, 30, local_cv=True)
    timing = json.loads(dest.with_suffix(".timing.json").read_text())
    assert timing["version"] == "1.0"
    assert timing["method"] == "ffmpeg_decoder_frame_metadata"
    capture = cv2.VideoCapture(str(dest))
    count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    capture.release()
    assert len(timing["frames"]) == count == 24
    assert timing["frames"][0]["source_index"] == 0
    indices = []
    for index, frame in enumerate(timing["frames"]):
        assert frame["normalized_index"] == index
        assert frame["normalized_time_s"] == pytest.approx(index / 24)
        assert frame["source_pts"] == timing["source_frames"][frame["source_index"]]["pts"]
        assert frame["source_time_s"] == pytest.approx(
            float(Fraction(frame["source_pts"]) * Fraction(timing["source_time_base"]))
        )
        indices.append(frame["source_index"])
    assert indices == sorted(indices)
    if rate == "12":
        assert len(set(indices)) < len(indices)  # duplicated frames retain their source identity
    else:
        assert len(set(indices)) == len(indices)  # dropped source frames remain inventoried
    assert timing["source_sha256"] != timing["normalized_sha256"]


def test_variable_pts_nonzero_start_and_trim(tmp_path: Path) -> None:
    source, dest = tmp_path / "input.mp4", tmp_path / "video.mp4"
    make_video(source, "30", "2", vfr=True)
    normalize_video(source, dest, 30, local_cv=True, segment_start_s=0.3, segment_duration_s=0.7)
    timing = json.loads(dest.with_suffix(".timing.json").read_text())
    assert timing["source_start_time_s"] == 2
    assert timing["segment_start_s"] == 0.3
    assert timing["segment_duration_s"] == 0.7
    assert timing["frames"][0]["source_time_s"] == pytest.approx(2 + 1 / 3)
    assert all(2.3 <= frame["source_time_s"] < 3 for frame in timing["frames"])
    assert timing["frames"][0]["normalized_time_s"] == 0
    pts = [frame["pts"] for frame in timing["source_frames"]]
    assert len({b - a for a, b in zip(pts, pts[1:], strict=False)}) > 1


def test_short_single_frame_clip(tmp_path: Path) -> None:
    source, dest = tmp_path / "input.mp4", tmp_path / "video.mp4"
    make_video(source, "30", "0.02")
    normalize_video(source, dest, 30)
    timing = json.loads(dest.with_suffix(".timing.json").read_text())
    assert timing["frames"]
    assert max(frame["source_index"] for frame in timing["frames"]) < len(timing["source_frames"])
