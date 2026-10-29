import time
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from backend.app.config import ROOT, Settings
from backend.app.main import create_app


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(Settings(data_dir=tmp_path))) as client:
        yield client


def await_job(client, job_id):
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        response = client.get(f"/api/jobs/{job_id}")
        assert response.status_code == 200
        job = response.json()
        if job["status"] in {"completed", "failed", "expired"}:
            return job
        time.sleep(0.02)
    pytest.fail("Job did not finish")


@pytest.mark.parametrize("fixture_id,verdict", [("correct", "PASS"), ("incorrect", "FAIL")])
def test_fixture_workflow_has_evidence_and_seekable_media(client, fixture_id, verdict):
    response = client.post(f"/api/jobs/demo/{fixture_id}")
    assert response.status_code == 202
    job = await_job(client, response.json()["id"])
    assert job["status"] == "completed", job
    assert job["progress"] == 100
    assert job["mode"] == "fixture"
    assert job["result"]["verdict"] == verdict
    assert job["tracks"]
    assert len(job["result"]["evidence"]) == 3
    for check in job["result"]["constraints"]:
        assert check["evidence_ids"]
    response = client.get(job["media_url"], headers={"Range": "bytes=0-99"})
    assert response.status_code == 206
    assert response.headers["content-type"] == "video/mp4"
    assert len(response.content) == 100
    assert response.headers["cache-control"] == "no-store"
    assert client.get("/api/costs").json()["committed_microusd"] == 0


def test_uploaded_fixture_is_unknown_and_source_is_removed(client):
    response = client.post(
        "/api/jobs/upload",
        data={"procedure": "Lift cup. Place cup."},
        files={
            "video": (
                "../../correct.mp4",
                (ROOT / "fixtures/correct.mp4").read_bytes(),
                "video/mp4",
            )
        },
    )
    assert response.status_code == 202
    job = await_job(client, response.json()["id"])
    assert job["status"] == "completed", job
    assert job["mode"] == "mock-upload"
    assert job["result"]["verdict"] == "UNKNOWN"
    assert job["result"]["evidence"] == []
    assert job["tracks"] == []
    assert client.get(job["media_url"]).status_code == 200
    directory = client.app.state.service.media_dir / job["id"]
    # The worker sets completed just before final source cleanup.
    client.app.state.service.pool.submit(lambda: None).result()
    deadline = time.monotonic() + 2
    while (directory / "source.upload").exists() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert not (directory / "source.upload").exists()


def test_invalid_video_fails_without_decisive_result(client):
    response = client.post(
        "/api/jobs/upload",
        data={"procedure": "Lift cup."},
        files={"video": ("clip.mp4", b"not video", "video/mp4")},
    )
    job = await_job(client, response.json()["id"])
    assert job["status"] == "failed"
    assert job["result"] is None
    assert job["media_url"] is None
    assert job["error"]


def test_expiration_removes_video_and_prevents_late_worker_resurrection(client):
    job_id = client.post("/api/jobs/demo/correct").json()["id"]
    job = await_job(client, job_id)
    svc = client.app.state.service
    svc.cleanup(job["expires_at"] + 1)
    assert not (svc.media_dir / job_id).exists()
    assert client.get(f"/api/jobs/{job_id}/media").status_code == 410
    svc.store.update_job(job_id, status="completed", media_url="stale")
    expired = client.get(f"/api/jobs/{job_id}").json()
    assert expired["status"] == "expired"
    assert expired["media_url"] is None
    assert expired["result"]["verdict"] == "PASS"  # audit retained, UI marks unavailable


def test_byte_limit_and_empty_upload_remove_partial_files(tmp_path):
    with TestClient(create_app(replace(Settings(data_dir=tmp_path), max_upload_bytes=3))) as client:
        for content, expected in [(b"", 422), (b"1234", 413)]:
            response = client.post(
                "/api/jobs/upload",
                data={"procedure": "Lift cup."},
                files={"video": ("clip.mp4", content)},
            )
            assert response.status_code == expected
        assert list((tmp_path / "media").iterdir()) == []


def test_input_validation_health_schema_and_queue_limit(client):
    assert client.get("/api/health").json()["live_inference"] is False
    assert client.get("/api/taskgraph/schema").json()["additionalProperties"] is False
    assert len(client.get("/api/fixtures").json()) == 2
    assert client.post("/api/compile", json={"procedure": " "}).status_code == 422
    assert (
        client.post("/api/compile", json={"procedure": "Lift.", "vendor": "x"}).status_code == 422
    )
    compiled = client.post("/api/compile", json={"procedure": "1. Lift cup.\n2. Place cup."}).json()
    assert compiled["version"] == "2.0"
    assert compiled["constraints"] == []  # No invented order for unrecognized prose.
    requirements = compiled["events"] + compiled["conditions"]
    assert len(requirements) == 2
    assert all(item["observability"] == "UNSUPPORTED" for item in requirements)
    assert client.post("/api/jobs/demo/missing").status_code == 404
    assert client.get("/api/jobs/missing").status_code == 404
    assert client.get("/api/jobs/missing/media").status_code == 404
    slots = client.app.state.service.slots
    for _ in range(4):
        assert slots.acquire(False)
    try:
        assert client.post("/api/jobs/demo/correct").status_code == 429
        assert (
            client.post(
                "/api/jobs/upload",
                data={"procedure": "Lift cup."},
                files={"video": ("clip.mp4", b"content")},
            ).status_code
            == 429
        )
    finally:
        for _ in range(4):
            slots.release()


def test_health_distinguishes_compilation_from_perception(client):
    health = client.get("/api/health").json()
    assert health["compiler_source"] == "local_rules"
    assert health["real_muse_compilation"] is False
    assert health["real_video_verification"] is True
    assert health["sam_used"] is False


def test_upload_compiles_once_after_media_validation(client):
    svc = client.app.state.service
    original = svc.compiler

    class CountingCompiler:
        def __init__(self):
            self.calls = 0

        def compile(self, procedure):
            self.calls += 1
            return original.compile(procedure)

    compiler = CountingCompiler()
    svc.compiler = compiler
    for video, expected_calls in [
        (b"invalid", 0),
        ((ROOT / "fixtures/correct.mp4").read_bytes(), 1),
    ]:
        response = client.post(
            "/api/jobs/upload",
            data={"procedure": "Battery is visible."},
            files={"video": ("clip.mp4", video, "video/mp4")},
        )
        job = await_job(client, response.json()["id"])
        assert compiler.calls == expected_calls
        if expected_calls:
            assert job["result"]["verdict"] == "UNKNOWN"
            assert job["graph"]["compilation_source"] == "local_rules"


def test_legacy_schema_still_available(client):
    schema = client.get("/api/taskgraph/schema/v1").json()
    assert schema["properties"]["version"]["const"] == "1.0"
