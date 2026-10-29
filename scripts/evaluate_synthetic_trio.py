"""Exercise generated trio through real upload/initialization APIs, never camera acceptance.

Run after ``uv run python -m scripts.generate_synthetic_trio``. Reports and isolated
job data go under ignored output/; the existing application database is read-only.
No event times or desired verdicts are supplied to the application.
"""

import hashlib
import json
import sqlite3
import subprocess
import time
from collections import Counter
from fractions import Fraction
from typing import Any
from unittest.mock import patch

import cv2
from fastapi.testclient import TestClient
from imageio_ffmpeg import get_ffmpeg_exe

from backend.app.config import ROOT, Settings
from backend.app.main import create_app

OUT = ROOT / "output/synthetic-trio" / str(time.time_ns())
PROCEDURE = (
    "Move the blue block into the visible marked region before moving the cup into that region."
)


def ledger() -> list[tuple[Any, ...]] | None:
    path = ROOT / "data/runs.sqlite"
    if not path.exists():
        return None
    with sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True) as db:
        return db.execute("SELECT * FROM costs ORDER BY id").fetchall()


def wait(client: TestClient, job_id: str, statuses: set[str]) -> dict[str, Any]:
    deadline = time.monotonic() + 150
    while time.monotonic() < deadline:
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in statuses | {"failed"}:
            assert job["status"] != "failed", job
            return dict(job)
        time.sleep(0.05)
    raise TimeoutError(job_id)


def box(x: int, y: int, w: int, h: int) -> dict[str, float]:
    return dict(x=x / 1280, y=y / 720, width=w / 1280, height=h / 720)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=False)
    before = ledger()
    original = Settings.from_env()
    assert not original.meta_paid_enabled and not original.meta_smoke_approved
    report: dict[str, Any] = {
        "provenance": "SYNTHETIC_NOT_GENUINE_CAMERA",
        "real_world_validation": "unverified",
        "procedure": PROCEDURE,
        "cases": {},
    }
    settings = Settings(
        data_dir=OUT / f"api-{time.time_ns()}", provider_mode="local_cv", media_ttl_s=86400
    )
    with (
        patch(
            "backend.app.meta.MetaClient._http",
            side_effect=RuntimeError("Meta network forbidden in synthetic evaluation"),
        ) as network,
        TestClient(create_app(settings)) as client,
    ):
        for case in ("correct", "reverse", "occlusion"):
            source = ROOT / f"recordings/synthetic/{case}.mp4"
            cap = cv2.VideoCapture(str(source))
            metadata: dict[str, Any] = dict(
                width=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                height=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                fps=cap.get(cv2.CAP_PROP_FPS),
                codec=int(cap.get(cv2.CAP_PROP_FOURCC)),
            )
            count = 0
            while cap.read()[0]:
                count += 1
            cap.release()
            metadata.update(
                decoded_frames=count,
                duration_s=count / metadata["fps"],
                sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
            )
            metadata["fourcc"] = "".join(
                chr((metadata["codec"] >> (8 * i)) & 255) for i in range(4)
            )
            assert (metadata["width"], metadata["height"], metadata["fps"], count) == (
                1280,
                720,
                30,
                450,
            ) and metadata["fourcc"] in {"avc1", "h264"}, metadata
            decode = subprocess.run(
                [get_ffmpeg_exe(), "-v", "error", "-xerror", "-i", str(source), "-f", "null", "-"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            assert decode.returncode == 0 and not decode.stderr, decode.stderr
            metadata["ffmpeg_full_decode"] = "passed"
            response = client.post(
                "/api/jobs/upload",
                data={
                    "procedure": PROCEDURE,
                    "perception_mode": "local_cv",
                    "footage_origin": "generated",
                },
                files={"video": (source.name, source.read_bytes(), "video/mp4")},
            )
            assert response.status_code == 202, response.text
            job_id = response.json()["id"]
            job = wait(client, job_id, {"awaiting_initialization"})
            init = {
                "frame_reference": job["frame_reference"],
                "objects": {
                    o["id"]: box(175, 203, 122, 108)
                    if "block" in o["label"]
                    else box(172, 455, 122, 105)
                    for o in job["graph"]["objects"]
                },
                "regions": {r["id"]: box(704, 180, 448, 360) for r in job["graph"]["regions"]},
            }
            response = client.post(f"/api/jobs/{job_id}/initialize", json=init)
            assert response.status_code == 202, response.text
            job = wait(client, job_id, {"completed"})
            assert job["mode"] == "local_cv" and job["footage_origin"] == "generated"
            assert job["real_pixel_processing"] and not job["sam_used"]
            assert not job["inference_usage"]
            assert job["media_metadata"]["fps"] == 24
            assert job["media_metadata"]["frame_count"] == 360
            timing = job["media_metadata"]["source_timing"]
            assert timing["source_sha256"] == metadata["sha256"]
            assert len(timing["frames"]) == 360 and len(timing["source_frames"]) == 450
            for index, mapping in enumerate(timing["frames"]):
                assert mapping["normalized_index"] == index
                assert mapping["normalized_time_s"] == index / 24
                original_frame = timing["source_frames"][mapping["source_index"]]
                assert original_frame["pts"] == mapping["source_pts"]
                assert mapping["source_time_s"] == float(
                    mapping["source_pts"] * Fraction(timing["source_time_base"])
                )
            for track in job["tracks"]:
                assert [s["frame_index"] for s in track["samples"]] == [*range(0, 360, 2), 359]
                assert all(
                    abs(s["time_s"] - s["frame_index"] / 24) < 1e-6 for s in track["samples"]
                )
            evidence = {e["id"]: e for e in job["result"]["evidence"]}
            for check in [*job["result"]["steps"], *job["result"]["constraints"]]:
                if check["verdict"] in {"PASS", "FAIL"}:
                    assert check["evidence_ids"]
                    assert all(eid in evidence for eid in check["evidence_ids"])
            for item in evidence.values():
                assert 0 <= item["start_s"] <= item["end_s"] <= job["duration_s"]
                for index in item["frame_indices"]:
                    assert index in job["saved_frame_indices"]
                    assert client.get(f"/api/jobs/{job_id}/frames/{index}").status_code == 200
            (OUT / f"{case}.job.json").write_text(json.dumps(job, indent=2), encoding="utf-8")
            summary = {
                "source": metadata,
                "job_id": job_id,
                "graph": job["graph"],
                "normalized": job["media_metadata"],
                "initialization": init,
                "provenance": job["provenance"],
                "result": job["result"],
                "observations": job["observations"],
                "tracks": [
                    {
                        "object_id": t["object_id"],
                        "statuses": dict(Counter(s["status"] for s in t["samples"])),
                        "first": t["samples"][0],
                        "last": t["samples"][-1],
                        "minimum_reliable_quality": min(
                            (s["confidence"] for s in t["samples"] if s["status"] == "reliable"),
                            default=None,
                        ),
                        "diagnostics": t["diagnostics"],
                        "invalid_intervals": t["invalid_intervals"],
                    }
                    for t in job["tracks"]
                ],
            }
            report["cases"][case] = summary
            print(case, job["result"]["verdict"], flush=True)
        report["costs"] = client.get("/api/costs").json()
        assert report["costs"]["committed_microusd"] == 0
        assert network.call_count == 0
        report["meta_network_calls"] = network.call_count
    report["existing_ledger_unchanged"] = before == ledger()
    assert report["existing_ledger_unchanged"]
    (OUT / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Report: {OUT / 'report.json'}")


if __name__ == "__main__":
    main()
