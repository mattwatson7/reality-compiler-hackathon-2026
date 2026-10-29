"""Generate three explicitly SYNTHETIC Reality Compiler temporal-order MP4s.

Run from the repository root with:
    uv run python -m scripts.generate_synthetic_trio

Not genuine-camera originals; do not use for physical-camera acceptance.
"""

# mypy: ignore-errors
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import cv2
import numpy as np
from imageio_ffmpeg import get_ffmpeg_exe

W, H, FPS, SECONDS = 1280, 720, 30, 15
DEST = Path("recordings/synthetic")
REGION = (704, 180, 1152, 540)
BLUE_START, BLUE_END = (230, 252), (845, 274)
CUP_START, CUP_END = (230, 504), (1024, 446)


def ease(f: float) -> float:
    f = min(1.0, max(0.0, f))
    return f * f * (3 - 2 * f)


def move(
    a: tuple[int, int], b: tuple[int, int], t: float, start: float, end: float
) -> tuple[int, int]:
    f = ease((t - start) / (end - start))
    return (round(a[0] + (b[0] - a[0]) * f), round(a[1] + (b[1] - a[1]) * f))


def make_background() -> np.ndarray:
    img = np.full((H, W, 3), (32, 34, 37), dtype=np.uint8)
    yy, xx = np.ogrid[:H, :W]
    spot = (16 * np.exp(-(((xx - 630) / 850) ** 2) - ((yy - 345) / 650) ** 2)).astype(np.uint8)
    img = cv2.add(img, np.repeat(spot[:, :, None], 3, axis=2))
    cv2.rectangle(
        img, (REGION[0] + 4, REGION[1] + 4), (REGION[2] + 4, REGION[3] + 4), (10, 10, 10), 7
    )
    cv2.rectangle(img, REGION[:2], REGION[2:], (216, 219, 222), 5)
    cv2.putText(
        img, "TARGET", (868, 165), cv2.FONT_HERSHEY_SIMPLEX, 0.56, (173, 183, 190), 1, cv2.LINE_AA
    )
    cv2.rectangle(img, (10, 8), (501, 52), (11, 13, 16), -1)
    cv2.putText(
        img,
        "SYNTHETIC / NOT GENUINE CAMERA FOOTAGE",
        (20, 37),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.56,
        (215, 218, 221),
        1,
        cv2.LINE_AA,
    )
    return img


BACKGROUND = make_background()


def blue_block(img: np.ndarray, center: tuple[int, int]) -> None:
    x, y = center
    cv2.ellipse(img, (x + 8, y + 10), (59, 49), 0, 0, 360, (15, 18, 22), -1)
    top = np.array(
        [[x - 49, y - 43], [x + 43, y - 43], [x + 48, y + 37], [x - 47, y + 37]], dtype=np.int32
    )
    side = np.array(
        [[x + 43, y - 43], [x + 57, y - 31], [x + 61, y + 48], [x + 48, y + 37]], dtype=np.int32
    )
    face = np.array(
        [[x - 47, y + 37], [x + 48, y + 37], [x + 61, y + 48], [x - 36, y + 49]], dtype=np.int32
    )
    cv2.fillConvexPoly(img, side, (150, 68, 16))
    cv2.fillConvexPoly(img, face, (189, 92, 21))
    cv2.fillConvexPoly(img, top, (233, 143, 29))
    cv2.polylines(img, [top], True, (255, 183, 69), 2, cv2.LINE_AA)


def yellow_cup(img: np.ndarray, center: tuple[int, int]) -> None:
    x, y = center
    cv2.ellipse(img, (x + 10, y + 13), (58, 48), 0, 0, 360, (14, 19, 20), -1)
    cv2.ellipse(img, (x, y), (52, 44), 0, 0, 360, (20, 202, 239), -1)
    cv2.ellipse(img, (x, y), (44, 36), 0, 0, 360, (10, 126, 162), -1)
    cv2.ellipse(img, (x, y + 4), (36, 29), 0, 0, 360, (17, 67, 81), -1)
    cv2.ellipse(img, (x, y), (49, 41), 0, 204, 329, (108, 249, 255), 4, cv2.LINE_AA)


def opaque_card(img: np.ndarray, t: float) -> None:
    enter, leave = ease((t - 2.65) / 0.35), ease((t - 8.0) / 0.35)
    shift = round(-430 * (1 - enter) if t < 3 else -430 * leave if t > 8 else 0)
    corners = np.array([[15, 140], [1035, 140], [1045, 410], [5, 410]], dtype=np.int32)
    corners[:, 1] += shift
    cv2.fillConvexPoly(img, corners + (9, 10), (14, 16, 18))
    cv2.fillConvexPoly(img, corners, (114, 119, 125))
    cv2.polylines(img, [corners], True, (178, 184, 190), 3, cv2.LINE_AA)


def render(case: str, t: float) -> np.ndarray:
    img = BACKGROUND.copy()
    if case == "correct":
        blue = move(BLUE_START, BLUE_END, t, 3, 5)
        cup = move(CUP_START, CUP_END, t, 8, 10)
    elif case == "reverse":
        blue = move(BLUE_START, BLUE_END, t, 8, 10)
        cup = move(CUP_START, CUP_END, t, 3, 5)
    else:
        blue = move(BLUE_START, BLUE_END, t, 3, 7)
        cup = move(CUP_START, CUP_END, t, 10, 12)
    blue_block(img, blue)
    yellow_cup(img, cup)
    if case == "occlusion" and 2.65 <= t <= 8.35:
        opaque_card(img, t)
    return img


def main() -> None:
    DEST.mkdir(parents=True, exist_ok=True)
    manifest = {
        "provenance": "SYNTHETIC_NOT_GENUINE_CAMERA",
        "resolution": [W, H],
        "fps": FPS,
        "seconds": SECONDS,
        "cases": {},
    }
    for case in ("correct", "reverse", "occlusion"):
        video = DEST / f"{case}.mp4"
        command = [
            get_ffmpeg_exe(),
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "bgr24",
            "-s",
            f"{W}x{H}",
            "-r",
            str(FPS),
            "-i",
            "-",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(video),
        ]
        with subprocess.Popen(command, stdin=subprocess.PIPE) as process:
            assert process.stdin is not None
            try:
                for i in range(FPS * SECONDS):
                    process.stdin.write(render(case, i / FPS).tobytes())
            finally:
                process.stdin.close()
            if process.wait() != 0:
                raise RuntimeError(f"ffmpeg failed for {case}")
        digest = hashlib.sha256(video.read_bytes()).hexdigest()
        manifest["cases"][case] = {
            "path": str(video),
            "sha256": digest,
            "bytes": video.stat().st_size,
        }
        print(f"Generated {video} ({video.stat().st_size:,} bytes; SHA-256 {digest})", flush=True)
    (DEST / "manifest.synthetic.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print("Synthetic footage for tests only. Never claim genuine-camera validation.")


if __name__ == "__main__":
    main()
