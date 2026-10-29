import time

import pytest
from fastapi.testclient import TestClient

from backend.app.config import ROOT, Settings
from backend.app.main import create_app
from backend.tests.test_api import await_job
from backend.tests.test_milestone3_contract import PROCEDURE


def pending(client, mode="local_cv", video_bytes=None):
    response = client.post(
        "/api/jobs/upload",
        data={"procedure": PROCEDURE, "perception_mode": mode},
        files={
            "video": (
                "clip.mp4",
                video_bytes or (ROOT / "fixtures/correct.mp4").read_bytes(),
                "video/mp4",
            )
        },
    )
    assert response.status_code == 202
    job_id = response.json()["id"]
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in {"awaiting_initialization", "failed"}:
            assert job["status"] == "awaiting_initialization", job
            return job
        time.sleep(0.02)
    raise AssertionError("No first-frame selection state")


def selection(job):
    return {
        "frame_reference": job["frame_reference"],
        "objects": {
            o["id"]: {"x": 0.05 + i * 0.25, "y": 0.1, "width": 0.1, "height": 0.1}
            for i, o in enumerate(job["graph"]["objects"])
        },
        "regions": {
            r["id"]: {"x": 0.5, "y": 0.5, "width": 0.4, "height": 0.4}
            for r in job["graph"]["regions"]
        },
    }


def test_local_upload_awaits_selection_then_processes_and_expires(tmp_path):
    with TestClient(create_app(Settings(data_dir=tmp_path))) as client:
        job = pending(client)
        svc = client.app.state.service
        assert svc.slots.acquire(False)  # Pending input does not occupy a worker slot.
        svc.slots.release()
        assert job["graph"]["compilation_source"] == "local_rules"
        assert job["media_metadata"]["normalized_sha256"]
        assert client.get(job["preview_url"]).headers["content-type"] == "image/jpeg"
        body = selection(job)
        stale = {**body, "frame_reference": "stale"}
        url = f"/api/jobs/{job['id']}/initialize"
        assert client.post(url, json=stale).status_code == 422
        assert client.post(url, json={**body, "event_time": 1}).status_code == 422
        assert client.post(url, json=body).status_code == 202
        assert client.post(url, json=body).status_code == 409
        finished = await_job(client, job["id"])
        assert finished["status"] == "completed", finished
        assert finished["result"]["verdict"] == "UNKNOWN"  # Wrong initialization on fixture pixels.
        assert finished["sam_used"] is False
        assert finished["observations"] is not None
        assert finished["provenance"]["compiler"] == "local_rules"
        assert client.get(f"/api/jobs/{job['id']}/frames/999999").status_code == 404
        svc.cleanup(job["expires_at"] + 1)
        assert client.get(job["preview_url"]).status_code == 410
        assert client.post(url, json=body).status_code == 410
        assert client.get(f"/api/jobs/{job['id']}").json()["result"] is not None


def test_local_mode_rejects_live_and_invalid_boxes(tmp_path):
    with TestClient(create_app(Settings(data_dir=tmp_path))) as client:
        response = client.post(
            "/api/jobs/upload",
            data={"procedure": PROCEDURE, "perception_mode": "sam_live"},
            files={"video": ("clip.mp4", b"invalid")},
        )
        assert response.status_code == 422
        job = pending(client)
        body = selection(job)
        first = next(iter(body["objects"]))
        body["objects"][first]["x"] = 0.99
        assert client.post(f"/api/jobs/{job['id']}/initialize", json=body).status_code == 422


def test_source_frame_attribution_is_bound_and_expires(tmp_path):
    with TestClient(create_app(Settings(data_dir=tmp_path))) as client:
        job = pending(client)
        timing = job["media_metadata"]["source_timing"]
        assert timing["normalized_sha256"] == job["media_metadata"]["normalized_sha256"]
        url = f"/api/jobs/{job['id']}/source-frames/0"
        assert client.get(url).headers["content-type"] == "image/png"
        assert client.get(f"/api/jobs/{job['id']}/source-frames/999999").status_code == 404
        source = tmp_path / "media" / job["id"] / "source.original"
        source.write_bytes(source.read_bytes() + b"tampered")
        assert client.get(url).status_code == 409
        client.app.state.service.cleanup(job["expires_at"] + 1)
        assert client.get(url).status_code == 410


def test_legacy_runs_do_not_invent_source_frame_mapping(tmp_path):
    with TestClient(create_app(Settings(data_dir=tmp_path))) as client:
        job = pending(client)
        metadata = job["media_metadata"]
        del metadata["source_timing"]
        client.app.state.service.store.update_job(job["id"], media_metadata=metadata)
        assert client.get(f"/api/jobs/{job['id']}/source-frames/0").status_code == 409


def test_source_frame_uses_same_video_stream_as_normalization(tmp_path):
    import subprocess

    import cv2
    import numpy as np

    from backend.app.media import ffmpeg_binary

    source = tmp_path / "two-streams.mp4"
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
            "color=red:size=160x120:rate=30:duration=1",
            "-f",
            "lavfi",
            "-i",
            "color=blue:size=320x240:rate=30:duration=1",
            "-map",
            "0:v",
            "-map",
            "1:v",
            "-disposition:v:0",
            "0",
            "-disposition:v:1",
            "default",
            "-c:v",
            "libx264",
            "-threads",
            "2",
            str(source),
        ],
        check=True,
        capture_output=True,
    )
    with TestClient(create_app(Settings(data_dir=tmp_path / "runs"))) as client:
        job = pending(client, video_bytes=source.read_bytes())
        response = client.get(f"/api/jobs/{job['id']}/source-frames/0")
        assert response.status_code == 200
        frame = cv2.imdecode(np.frombuffer(response.content, dtype=np.uint8), cv2.IMREAD_COLOR)
        assert frame.shape[:2] == (120, 160)
        assert frame[50, 50, 2] > 200 and frame[50, 50, 0] < 30


def test_source_frame_rejects_tampered_completed_timing_map(tmp_path):
    import json

    with TestClient(create_app(Settings(data_dir=tmp_path))) as client:
        job = pending(client)
        store = client.app.state.service.store
        store.update_job(job["id"], status="completed")
        job = store.get_job(job["id"])
        job["media_metadata"]["source_timing"]["frames"][0]["source_index"] = 10
        with store.connect() as db:
            db.execute("UPDATE jobs SET body=? WHERE id=?", (json.dumps(job), job["id"]))
        assert client.get(f"/api/jobs/{job['id']}/source-frames/0").status_code == 409


@pytest.mark.parametrize(
    "reverse,occluded,expected",
    [(False, False, "PASS"), (True, False, "FAIL"), (False, True, "UNKNOWN")],
)
def test_synthetic_pixel_api_pipeline_without_fixture_events(tmp_path, reverse, occluded, expected):
    """Algorithm integration only: these are generated clips, never real-world validation."""
    from backend.tests.test_perception import initialization, video

    source = tmp_path / "generated.mp4"
    video(source, reverse=reverse, occluded=occluded)
    with TestClient(create_app(Settings(data_dir=tmp_path / "runs"))) as client:
        svc = client.app.state.service
        original = svc.compiler
        calls = []

        class CountingCompiler:
            def compile(self, text):
                calls.append(text)
                return original.compile(text)

        svc.compiler = CountingCompiler()
        response = client.post(
            "/api/jobs/upload",
            data={"procedure": PROCEDURE, "perception_mode": "local_cv"},
            files={"video": ("generated.mp4", source.read_bytes(), "video/mp4")},
        )
        job_id = response.json()["id"]
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            job = client.get(f"/api/jobs/{job_id}").json()
            if job["status"] == "awaiting_initialization":
                break
            assert job["status"] != "failed", job
            time.sleep(0.02)
        else:
            pytest.fail("No initialization frame")
        from backend.app.schemas import TaskGraph

        init = initialization(TaskGraph.model_validate(job["graph"]), job["frame_reference"])
        assert (
            client.post(
                f"/api/jobs/{job_id}/initialize", json=init.model_dump(mode="json")
            ).status_code
            == 202
        )
        completed = await_job(client, job_id)
        assert completed["status"] == "completed", completed
        assert calls == [PROCEDURE]
        assert completed["result"]["verdict"] == expected, completed["tracks"]
        assert completed["real_pixel_processing"] is True
        if expected != "UNKNOWN":
            assert completed["result"]["evidence"]
            for evidence in completed["result"]["evidence"]:
                assert evidence["source"] == "local_cv"
                assert evidence["frame_reference"] == job["frame_reference"]
                for index in evidence["frame_indices"]:
                    assert client.get(f"/api/jobs/{job_id}/frames/{index}").status_code == 200
