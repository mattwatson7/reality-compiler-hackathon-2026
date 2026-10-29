from fastapi.testclient import TestClient

from backend.app.config import Settings
from backend.app.main import create_app


def test_meta_is_unselectable_without_explicit_paid_approval(tmp_path):
    with TestClient(create_app(Settings(data_dir=tmp_path))) as client:
        health = client.get("/api/health").json()
        assert health["meta"]["paid_inference_enabled"] is False
        assert health["meta"]["sam_selectable"] is False
        assert "key" not in str(health["meta"]).lower()
        response = client.post(
            "/api/jobs/upload",
            data={"procedure": "The cup is visible.", "perception_mode": "meta_sam"},
            files={"video": ("clip.mp4", b"not-decoded")},
        )
        assert response.status_code == 503
        assert client.get("/api/costs").json()["committed_microusd"] == 0


def test_configured_sam_default_cannot_fall_through_to_mock_upload(tmp_path):
    with TestClient(create_app(Settings(data_dir=tmp_path, provider_mode="meta_sam"))) as client:
        response = client.post(
            "/api/jobs/upload",
            data={"procedure": "The cup is visible."},
            files={"video": ("clip.mp4", b"not-decoded")},
        )
        assert response.status_code == 503


def test_synthetic_sam_job_reports_provider_uncertainty_and_cost(tmp_path):
    from pydantic import SecretStr

    from backend.app.meta import MetaClient, ModelCatalog
    from backend.tests.test_api import await_job
    from backend.tests.test_local_api import pending, selection
    from backend.tests.test_sam import envelope

    with TestClient(create_app(Settings(data_dir=tmp_path))) as client:
        svc = client.app.state.service
        response = envelope("")
        response["usage"] = {"video_frames_processed": 168}
        svc.meta = MetaClient(
            key=SecretStr("synthetic-unit-key"),
            store=svc.store,
            paid_enabled=True,
            smoke_approved=True,
            catalog=ModelCatalog(("sam-3.1",), True),
            request=lambda *args: response,
        )
        job = pending(client, "meta_sam")
        assert (
            client.post(f"/api/jobs/{job['id']}/initialize", json=selection(job)).status_code == 202
        )
        done = await_job(client, job["id"])
        assert done["status"] == "completed", done
        assert done["result"]["verdict"] == "UNKNOWN"
        assert done["sam_used"] is True
        assert done["tracks"][0]["source"] == "meta_sam"
        assert done["inference_usage"][0]["model"] == "sam-3.1"
        assert done["inference_usage"][0]["actual_microusd"] is None
        assert done["inference_usage"][0]["reserved_microusd"] == 33600
        assert done["inference_usage"][0]["usage_verified"] is False
        assert done["provenance"]["tracker"] == "meta.sam-3.1"


def test_recording_harness_cannot_silently_enable_sam(tmp_path):
    from scripts.evaluate_recordings import evaluate_manifest

    path = tmp_path / "manifest.json"
    path.write_text('{"procedure":"The cup is visible.","recordings":[]}')
    report, code = evaluate_manifest(path, tmp_path / "output", "meta_sam")
    assert code != 0
    assert report["real_world_validation"] == "unverified"
    assert report["paid_calls"] == 0


def test_live_health_lists_sam_only_after_fresh_entitlement(tmp_path):
    from backend.app.meta import ModelCatalog

    with TestClient(create_app(Settings(data_dir=tmp_path))) as client:
        svc = client.app.state.service
        svc.meta.paid_enabled = svc.meta.smoke_approved = True
        svc.meta.catalog = ModelCatalog(("sam-3.1", "muse-wonder-1.0"), True)
        health = client.get("/api/health").json()
        assert "meta_sam" in health["perception_modes"]
        assert (
            health["meta"]["reason"] == "Fresh account catalog verified; paid dispatch is enabled"
        )
