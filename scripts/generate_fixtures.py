"""Generate synthetic videos and matching declared observations; no inference."""

import hashlib
import json
import subprocess
from pathlib import Path

import cv2
import numpy as np

from backend.app.config import ROOT
from backend.app.fixtures import export_taskgraph_schema
from backend.app.media import ffmpeg_binary
from backend.app.migration import legacy_demo_graph, migrate_fixture

PROCEDURE = (
    "1. Move the blue block onto the mat.\n2. Place the cup on the mat.\n3. Raise the green card."
)
LABELS = ["Move blue block onto mat", "Place cup on mat", "Raise green card"]


def generate(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    graph = legacy_demo_graph()
    for fixture_id, order in [("correct", [0, 1, 2]), ("incorrect", [1, 0, 2])]:
        video = directory / f"{fixture_id}.mp4"
        # Pipe RGB frames into FFmpeg. H.264/yuv420p plays in modern browsers.
        command = [
            ffmpeg_binary(),
            "-y",
            "-v",
            "error",
            "-f",
            "rawvideo",
            "-pixel_format",
            "bgr24",
            "-video_size",
            "960x540",
            "-framerate",
            "24",
            "-i",
            "pipe:0",
            "-an",
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
            str(video),
        ]
        process = subprocess.Popen(command, stdin=subprocess.PIPE)
        assert process.stdin is not None
        for frame_number in range(7 * 24):
            t = frame_number / 24
            frame = np.full((540, 960, 3), (24, 19, 15), dtype=np.uint8)
            cv2.putText(
                frame,
                "REALITY COMPILER / SYNTHETIC FIXTURE",
                (35, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (173, 227, 215),
                2,
            )
            cv2.putText(
                frame,
                f"{t:04.1f}s  /  {fixture_id.upper()} ORDER",
                (35, 78),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (185, 180, 170),
                1,
            )
            cv2.rectangle(frame, (325, 260), (700, 450), (80, 80, 70), 2)
            cv2.putText(frame, "MAT", (335, 440), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (140, 140, 130), 1)
            positions: list[tuple[int, int]] = []
            for action in range(3):
                start = float(1 + 2 * order.index(action))
                progress = max(0.0, min(1.0, (t - start) / 0.8))
                if action == 0:
                    positions.append((int(120 + 280 * progress), 340))
                elif action == 1:
                    positions.append((550, int(160 + 180 * progress)))
                else:
                    positions.append((800, int(400 - 240 * progress)))
            x, y = positions[0]
            cv2.rectangle(frame, (x - 30, y - 30), (x + 30, y + 30), (240, 145, 60), -1)
            x, y = positions[1]
            cv2.rectangle(frame, (x - 25, y - 35), (x + 25, y + 25), (220, 220, 220), -1)
            cv2.ellipse(frame, (x, y - 35), (25, 9), 0, 0, 360, (100, 100, 100), -1)
            x, y = positions[2]
            cv2.rectangle(frame, (x - 30, y - 40), (x + 30, y + 40), (110, 220, 105), -1)
            active = next((order[i] for i in range(3) if 1 + 2 * i <= t <= 1.8 + 2 * i), None)
            caption = LABELS[active] if active is not None else "Observe the sequence"
            cv2.putText(
                frame, caption, (35, 505), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (240, 240, 230), 2
            )
            process.stdin.write(frame.tobytes())
        process.stdin.close()
        if process.wait(timeout=60):
            raise RuntimeError("Fixture video generation failed")
        observations, tracks = [], []
        for action, name in enumerate(("block", "cup", "card")):
            start = float(1 + 2 * order.index(action))
            observations.append(
                {
                    "step_id": f"s{action + 1}",
                    "start_s": start,
                    "end_s": start + 0.8,
                    "confidence": 1.0,
                    "evidence": {
                        "id": f"e{action + 1}",
                        "start_s": start,
                        "end_s": start + 0.8,
                        "source": "fixture",
                        "description": f"Synthetic animation: {LABELS[action]}",
                    },
                }
            )
            start_xy = [(120, 340), (550, 160), (800, 400)][action]
            end_xy = [(400, 340), (550, 340), (800, 160)][action]
            tracks.append(
                {
                    "object_id": name,
                    "source": "fixture",
                    "samples": [
                        {
                            "time_s": time,
                            "box": [(x - 35) / 960, (y - 45) / 540, 70 / 960, 90 / 540],
                        }
                        for time, (x, y) in [(start, start_xy), (start + 0.8, end_xy)]
                    ],
                }
            )
        fixture = {
            "id": fixture_id,
            "title": f"{fixture_id.capitalize()} sequence",
            "description": "Synthetic block, cup and card animation with declared events.",
            "video": video.name,
            "graph": graph.model_dump(mode="json"),
            "observations": observations,
            "tracks": tracks,
        }
        migrated = migrate_fixture(fixture, hashlib.sha256(video.read_bytes()).hexdigest())
        (directory / f"{fixture_id}.json").write_text(
            json.dumps(migrated, indent=2) + "\n", "utf-8"
        )
    export_taskgraph_schema(directory / "taskgraph.schema.json")


if __name__ == "__main__":
    generate(ROOT / "fixtures")
