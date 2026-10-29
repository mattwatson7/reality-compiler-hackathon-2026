"""Synthetic deterministic tests: these do not establish camera acceptance."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from backend.app.compiler import SemanticCompiler
from backend.app.evaluator import evaluate
from backend.app.schemas import Evidence, Observation
from scripts.controlled_recordings import (
    CameraManifest,
    canonical,
    freeze,
    import_result,
    load_frozen,
    preflight,
)

PROCEDURE = "Move the blue block into the visible image region target."


def declaration(tmp_path: Path) -> CameraManifest:
    cases = []
    for index, name in enumerate(("correct", "reverse", "occlusion")):
        data = f"synthetic test bytes {index}".encode()
        (tmp_path / f"{name}.mp4").write_bytes(data)
        cases.append(
            {
                "id": name,
                "file": f"{name}.mp4",
                "source_sha256": hashlib.sha256(data).hexdigest(),
                "captured_at": datetime(2026, 1, 1, tzinfo=UTC),
                "camera_operator": "Test operator",
                "rights_basis": "Synthetic test fixture; no camera validation claimed",
                "redistribution": "private_only",
                "genuine_original_continuous_camera": True,
                "inspected_before_inference": True,
                "expected_verdict": "PASS",
                "expected_reason": "Synthetic expectation for deterministic validation only",
                "ground_truth": [{"start_s": 3, "end_s": 4, "description": "Test annotation only"}],
            }
        )
    return CameraManifest.model_validate(
        {"version": "1.0", "procedure": PROCEDURE, "declared_by": "Tester", "cases": cases}
    )


def job_export(tmp_path: Path, manifest: CameraManifest) -> tuple[dict, Path]:
    path = tmp_path / "normalized.mp4"
    path.write_bytes(b"synthetic normalized bytes")
    media_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    reference = f"{media_hash}:0"
    graph = SemanticCompiler().compile(PROCEDURE)
    event = graph.events[0]
    observation = Observation(
        occurrence_id="o1",
        event_id=event.id,
        predicate=event.predicate,
        start_s=3,
        end_s=4,
        confidence=1,
        provenance="mask_hysteresis.v1",
        frame_indices=[72, 96],
        evidence=Evidence(
            id="e1",
            start_s=3,
            end_s=4,
            source="local_cv",
            description="Synthetic entry observation",
            frame_reference=reference,
            frame_indices=[72, 96],
        ),
    )
    return {
        "id": "test-job",
        "status": "completed",
        "mode": "local_cv",
        "created_at": datetime(2026, 2, 1, tzinfo=UTC).timestamp(),
        "duration_s": 15,
        "procedure": PROCEDURE,
        "graph": graph.model_dump(mode="json"),
        "result": evaluate(graph, [observation], 15).model_dump(mode="json"),
        "observations": [observation.model_dump(mode="json")],
        "frame_reference": reference,
        "saved_frame_indices": [0, 72, 96],
        "media_metadata": {
            "source_sha256": manifest.cases[0].source_sha256,
            "normalized_sha256": media_hash,
        },
        "real_pixel_processing": True,
        "provenance": {
            "compiler": "local_rules",
            "tracker": "local_cv.fixed_hsv.v1",
            "observer": "mask_hysteresis.v1",
        },
    }, path


def test_preflight_hash_and_duration(tmp_path, monkeypatch):
    manifest = declaration(tmp_path)
    monkeypatch.setattr("scripts.controlled_recordings.probe_video", lambda *_: 15)
    assert preflight(manifest, tmp_path)["status"] == "preflight_only"
    (tmp_path / "correct.mp4").write_bytes(b"changed")
    with pytest.raises(ValueError, match="hash mismatch"):
        preflight(manifest, tmp_path)


def test_freeze_exclusive_and_tamper_rejected(tmp_path, monkeypatch):
    manifest = declaration(tmp_path)
    path = tmp_path / "manifest.json"
    path.write_text(manifest.model_dump_json())
    frozen = tmp_path / "frozen.json"
    monkeypatch.setattr("scripts.controlled_recordings.probe_video", lambda *_: 15)
    seal = freeze(path, frozen)
    assert load_frozen(frozen, seal)[0] == manifest
    with pytest.raises(FileExistsError):
        freeze(path, frozen)
    edited = json.loads(frozen.read_text())
    edited["payload"]["manifest"]["cases"][0]["expected_verdict"] = "FAIL"
    edited["sha256"] = hashlib.sha256(canonical(edited["payload"])).hexdigest()
    frozen.write_text(json.dumps(edited))
    with pytest.raises(ValueError, match="seal mismatch"):
        load_frozen(frozen, seal)


def test_import_uses_actual_evaluator_and_never_claims_acceptance(tmp_path):
    manifest = declaration(tmp_path)
    job, path = job_export(tmp_path, manifest)
    case = manifest.cases[0].model_copy(update={"expected_verdict": "FAIL"})
    result = import_result(case, PROCEDURE, datetime(2026, 1, 2, tzinfo=UTC), job, path)
    assert result["actual_verdict"] == "PASS"
    assert not result["matches_predeclared_expectation"]
    assert result["real_world_validation"] == "pending_live_and_browser_human_review"


@pytest.mark.parametrize(
    "mutation", ["verdict", "media", "frame", "provenance", "freeze", "mock", "evidence", "saved"]
)
def test_import_rejects_invalid_application_export(tmp_path, mutation):
    manifest = declaration(tmp_path)
    job, path = job_export(tmp_path, manifest)
    if mutation == "verdict":
        job["result"]["reason"] = "Altered evaluation"
    elif mutation == "media":
        path.write_bytes(b"changed")
    elif mutation == "frame":
        job["observations"][0]["evidence"]["frame_reference"] = "another-frame"
    elif mutation == "provenance":
        job["provenance"]["tracker"] = "fixture"
    elif mutation == "freeze":
        job["created_at"] = 0
    elif mutation == "evidence":
        job["result"]["steps"][0]["evidence_ids"] = ["missing"]
    elif mutation == "saved":
        job["saved_frame_indices"] = [0]
    else:
        job["mode"] = "mock"
    with pytest.raises(ValueError):
        import_result(manifest.cases[0], PROCEDURE, datetime(2026, 1, 2, tzinfo=UTC), job, path)


def test_duplicate_original_rejected(tmp_path):
    data = declaration(tmp_path).model_dump(mode="json")
    data["cases"][1]["source_sha256"] = data["cases"][0]["source_sha256"]
    with pytest.raises(ValueError, match="distinct original"):
        CameraManifest.model_validate_json(json.dumps(data))


@pytest.mark.parametrize("duration", [9.9, 15])
def test_preflight_rejects_short_clip_or_out_of_bounds_annotation(tmp_path, monkeypatch, duration):
    data = declaration(tmp_path).model_dump(mode="json")
    data["cases"][0]["ground_truth"][0]["end_s"] = 16
    manifest = CameraManifest.model_validate_json(json.dumps(data))
    monkeypatch.setattr("scripts.controlled_recordings.probe_video", lambda *_: duration)
    with pytest.raises(ValueError, match="10–20 seconds"):
        preflight(manifest, tmp_path)


def test_missing_original_does_not_create_freeze(tmp_path):
    manifest = declaration(tmp_path)
    path = tmp_path / "manifest.json"
    path.write_text(manifest.model_dump_json())
    (tmp_path / "correct.mp4").unlink()
    output = tmp_path / "frozen.json"
    with pytest.raises(FileNotFoundError):
        freeze(path, output)
    assert not output.exists()
