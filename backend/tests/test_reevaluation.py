"""Evidence reuse must preserve uncertainty and never depend on compiled ID order."""

import copy
import hashlib

import pytest

from backend.app.compiler import SemanticCompiler
from backend.app.evaluator import evaluate
from backend.app.perception import LocalCVTracker, LocalRegionObserver, inspect_video
from backend.tests.test_perception import initialization, video

FORWARD = (
    "Move the blue block into the visible marked region before moving the cup into that region."
)
REVERSE = (
    "Move the cup into the visible marked region before moving the blue block into that region."
)


def capture(tmp_path):
    path = tmp_path / "clip.mp4"
    video(path)
    graph = SemanticCompiler().compile(FORWARD)
    meta = inspect_video(path)
    init = initialization(graph, meta["frame_reference"])
    tracks = LocalCVTracker(init).track(path, graph)
    observations = LocalRegionObserver(init).observe(path, graph, tracks)
    return graph, observations, meta


def test_reversed_procedure_reuses_exact_evidence_with_different_ids(tmp_path):
    from backend.app.reevaluation import reuse_observations

    original, observations, meta = capture(tmp_path)
    revised = SemanticCompiler().compile(REVERSE)
    before = copy.deepcopy(observations)
    reused, reasons = reuse_observations(original, revised, observations)
    assert not reasons
    assert evaluate(original, observations, meta["duration_s"]).verdict == "PASS"
    assert evaluate(revised, reused, meta["duration_s"]).verdict == "FAIL"
    assert {o.evidence.id for o in reused} == {o.evidence.id for o in observations}
    assert observations == before


@pytest.mark.parametrize(
    "procedure",
    [
        FORWARD.replace("blue block", "red block"),
        FORWARD.replace("marked region", "image region different"),
        "At end, the blue block is visible.",
    ],
)
def test_changed_grounding_or_new_perception_is_incompatible(tmp_path, procedure):
    from backend.app.reevaluation import reuse_observations

    original, observations, _ = capture(tmp_path)
    reused, reasons = reuse_observations(
        original, SemanticCompiler().compile(procedure), observations
    )
    assert reasons
    assert not reused


def test_unsupported_revision_is_unknown_without_new_perception(tmp_path):
    from backend.app.reevaluation import reuse_observations

    original, observations, meta = capture(tmp_path)
    revised = SemanticCompiler().compile(FORWARD + "\nEnsure the block is sterile.")
    reused, reasons = reuse_observations(original, revised, observations)
    assert not reasons
    assert evaluate(revised, reused, meta["duration_s"]).verdict == "UNKNOWN"


def test_repeated_and_unusable_evidence_is_not_filtered_to_manufacture_verdict(tmp_path):
    from backend.app.reevaluation import reuse_observations

    original, observations, meta = capture(tmp_path)
    duplicate = observations[0].model_copy(deep=True)
    duplicate.occurrence_id += "_repeat"
    duplicate.evidence.id += "_repeat"
    duplicate.usable = False
    reused, reasons = reuse_observations(
        original, SemanticCompiler().compile(REVERSE), [*observations, duplicate]
    )
    assert not reasons
    assert len(reused) == len(observations) + 1
    assert (
        evaluate(SemanticCompiler().compile(REVERSE), reused, meta["duration_s"]).verdict
        == "UNKNOWN"
    )


def test_api_reuses_completed_pixels_persists_and_preserves_original(tmp_path):
    from fastapi.testclient import TestClient

    from backend.app.config import Settings
    from backend.app.main import create_app
    from backend.tests.test_api import await_job
    from backend.tests.test_local_api import pending

    settings = Settings(data_dir=tmp_path / "runs")
    with TestClient(create_app(settings)) as client:
        job = pending(client)
        svc = client.app.state.service
        path = svc.media_dir / job["id"] / "video.mp4"
        # Test-only generated pixels; never real-camera acceptance evidence.
        video(path)
        meta = inspect_video(path)
        graph = SemanticCompiler().compile(FORWARD)
        svc.store.update_job(
            job["id"],
            graph=graph.model_dump(mode="json"),
            procedure=FORWARD,
            duration_s=meta["duration_s"],
            frame_reference=meta["frame_reference"],
            media_metadata={**meta, "normalized_sha256": meta["sha256"]},
        )
        init = initialization(graph, meta["frame_reference"])
        assert (
            client.post(f"/api/jobs/{job['id']}/initialize", json=init.model_dump()).status_code
            == 202
        )
        original = await_job(client, job["id"])
        assert original["result"]["verdict"] == "PASS"

        class NeverPerceive:
            def __call__(self, *_):
                raise AssertionError("Re-evaluation must not dispatch perception")

        svc.visual_tracker = NeverPerceive()
        svc.visual_observer = NeverPerceive()
        url = f"/api/jobs/{job['id']}/evaluations"
        response = client.post(url, json={"procedure": REVERSE})
        assert response.status_code == 201, response.text
        revised = response.json()
        assert revised["reuse_status"] == "reused"
        assert revised["result"]["verdict"] == "FAIL"
        assert revised["inference_usage"] == []
        assert client.get(f"/api/jobs/{job['id']}").json() == original
        changed = client.post(url, json={"procedure": FORWARD.replace("blue", "red")}).json()
        assert changed["reuse_status"] == "needs_perception"
        assert changed["result"]["verdict"] == "UNKNOWN"
        assert client.post(url, json={"procedure": "   "}).status_code == 422
        assert client.post(url, json={"procedure": REVERSE, "observations": []}).status_code == 422
        history = client.get(url).json()
        assert [entry["result"]["verdict"] for entry in history] == ["PASS", "FAIL", "UNKNOWN"]
        path.write_bytes(b"tampered")
        assert client.post(url, json={"procedure": REVERSE}).status_code == 422
        assert len(client.get(url).json()) == 3
    with TestClient(create_app(settings)) as client:
        assert client.get(url).json() == history
        svc = client.app.state.service
        svc.cleanup(original["expires_at"] + 1)
        assert client.post(url, json={"procedure": REVERSE}).status_code == 410
        assert client.get(url).json() == history


def test_local_final_visibility_requires_unbroken_identity_and_end_coverage(tmp_path):
    path = tmp_path / "clip.mp4"
    video(path)
    graph = SemanticCompiler().compile("At end, the blue block is visible.")
    meta = inspect_video(path)
    init = initialization(graph, meta["frame_reference"])
    tracks = LocalCVTracker(init).track(path, graph)
    observations = LocalRegionObserver(init).observe(path, graph, tracks)
    assert evaluate(graph, observations, meta["duration_s"]).verdict == "PASS"
    tracks[0].samples = tracks[0].samples[:-1]
    observations = LocalRegionObserver(init).observe(path, graph, tracks)
    assert evaluate(graph, observations, meta["duration_s"]).verdict == "UNKNOWN"


def test_relabelled_conflicting_observation_still_blocks_reuse(tmp_path):
    from backend.app.reevaluation import reuse_observations

    original, observations, meta = capture(tmp_path)
    conflict = observations[0].model_copy(deep=True)
    conflict.event_id = "unmatched_conflict"
    conflict.occurrence_id = "conflicting_occurrence"
    conflict.evidence.id = "conflicting_evidence"
    conflict.polarity = "CONTRADICTED"
    revised = SemanticCompiler().compile(REVERSE)
    reused, reasons = reuse_observations(original, revised, [*observations, conflict])
    assert not reasons
    assert evaluate(revised, reused, meta["duration_s"]).verdict == "UNKNOWN"


@pytest.mark.parametrize("field", ["evidence", "occurrence"])
def test_collision_with_observation_outside_revised_requirements_stays_unknown(tmp_path, field):
    from backend.app.reevaluation import reuse_observations

    original, observations, meta = capture(tmp_path)
    if field == "evidence":
        observations[1].evidence.id = observations[0].evidence.id
    else:
        observations[1].occurrence_id = observations[0].occurrence_id
    revised = SemanticCompiler().compile("Move the blue block into the visible marked region.")
    reused, reasons = reuse_observations(original, revised, observations)
    assert not reasons
    assert evaluate(revised, reused, meta["duration_s"]).verdict == "UNKNOWN"


@pytest.mark.parametrize(
    "failure", ["seal", "frame_reference", "expiry_during_compile", "mask_missing", "mask_tampered"]
)
def test_service_integrity_and_expiry_guards(tmp_path, failure):
    from backend.app.config import Settings
    from backend.app.service import JobService

    graph, observations, meta = capture(tmp_path)
    svc = JobService(Settings(data_dir=tmp_path / "runs"))
    try:
        job_id, directory = svc.allocate(FORWARD, "local_cv")
        (directory / "video.mp4").write_bytes((tmp_path / "clip.mp4").read_bytes())
        if failure == "frame_reference":
            observations[0].evidence.frame_reference = "different_source:0"
        if failure.startswith("mask_"):
            svc.store.update_job(
                job_id,
                perception_artifacts={"sam_masks_sha256": hashlib.sha256(b"original").hexdigest()},
            )
            if failure == "mask_tampered":
                (directory / "sam-masks.txt").write_bytes(b"changed")
        svc.store.update_job(
            job_id,
            status="completed",
            graph=graph.model_dump(mode="json"),
            duration_s=meta["duration_s"],
            frame_reference=meta["frame_reference"],
            media_metadata={**meta, "normalized_sha256": meta["sha256"]},
            observations=[o.model_dump(mode="json") for o in observations],
        )
        if failure == "seal":
            svc.store.update_job(job_id, provenance={"tracker": "changed"})
        if failure == "expiry_during_compile":
            original_compiler = svc.compiler

            class ExpiringCompiler:
                def compile(self, procedure):
                    svc.store.update_job(job_id, expires_at=0)
                    return original_compiler.compile(procedure)

            svc.compiler = ExpiringCompiler()
        with pytest.raises(
            TimeoutError if failure == "expiry_during_compile" else (ValueError, OSError)
        ):
            svc.reevaluate(job_id, REVERSE)
        assert svc.store.evaluations(job_id) == []
    finally:
        svc.pool.shutdown(wait=True)
