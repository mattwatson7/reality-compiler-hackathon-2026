"""Harness validation tests; generated clips never establish real-world success."""

import json
from pathlib import Path


def test_empty_manifest_is_explicitly_unverified(tmp_path):
    from scripts.evaluate_recordings import evaluate_manifest

    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"procedure": "The cup is visible.", "recordings": []}))
    report, code = evaluate_manifest(manifest, tmp_path / "report")
    assert code != 0
    assert report["status"] == "unverified"
    assert report["evaluated_recordings"] == 0


def test_bundled_synthetic_fixture_cannot_be_attested_as_genuine(tmp_path):
    import pytest

    from scripts.evaluate_recordings import prepare_recording

    fixture = Path(__file__).resolve().parents[2] / "fixtures" / "correct.mp4"
    with pytest.raises(ValueError, match="synthetic fixture"):
        prepare_recording(fixture, tmp_path / "prepared")


def test_generated_test_clip_prepare_produces_hash_bound_first_frame(tmp_path):
    from backend.tests.test_perception import video
    from scripts.evaluate_recordings import prepare_recording

    source = tmp_path / "synthetic-algorithm-test.mp4"
    video(source)
    prepared = prepare_recording(source, tmp_path / "prepared")
    assert prepared["real_world_validation"] == "unverified"
    assert prepared["source_sha256"] != prepared["normalized_sha256"]
    assert Path(prepared["normalized_file"]).is_file()
    assert (tmp_path / "prepared" / "frame-0.jpg").is_file()
    assert prepared["frame_reference"] == prepared["normalized_sha256"] + ":0"


def test_non_genuine_provenance_is_rejected_without_running_perception(tmp_path):
    from scripts.evaluate_recordings import evaluate_manifest

    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "procedure": "The cup is visible.",
                "recordings": [
                    {
                        "id": "synthetic",
                        "file": "generated.mp4",
                        "source_sha256": "0" * 64,
                        "normalized_sha256": "1" * 64,
                        "expected_verdict": "PASS",
                        "provenance": {
                            "kind": "synthetic_test",
                            "captured_at": "2026-10-27T10:00:00+07:00",
                            "description": "Generated algorithm test, not genuine footage",
                        },
                        "initialization": {"objects": {}, "regions": {}},
                    }
                ],
            }
        )
    )
    report, code = evaluate_manifest(manifest, tmp_path / "report")
    assert code != 0
    assert report["status"] == "unverified"
    assert report["evaluated_recordings"] == 0


def test_harness_evaluates_pixels_and_fails_mismatch_without_claiming_real_success(tmp_path):
    """A deliberately spoofed attestation tests plumbing, NOT genuine footage validation."""
    from backend.tests.test_perception import graph, initialization, video
    from scripts.evaluate_recordings import evaluate_manifest, prepare_recording

    source = tmp_path / "SYNTHETIC-unit-test.mp4"
    video(source)
    prepared = prepare_recording(source, tmp_path / "prepared")
    init = initialization(graph(), prepared["frame_reference"])
    record = {
        "id": "SYNTHETIC-unit-test",
        "file": str(source),
        "source_sha256": prepared["source_sha256"],
        "normalized_file": prepared["normalized_file"],
        "normalized_sha256": prepared["normalized_sha256"],
        "expected_verdict": "PASS",
        "provenance": {
            "kind": "genuine_recording",
            "captured_at": "2026-10-27T19:00:00+07:00",
            "description": "SPOOFED UNIT TEST attestation for generated pixels; not real footage",
        },
        "initialization": init.model_dump(mode="json", exclude={"frame_reference"}),
    }
    manifest = tmp_path / "test-only-manifest.json"
    for expected, status, code in [("PASS", "unverified", 2), ("FAIL", "failed", 1)]:
        record["expected_verdict"] = expected
        manifest.write_text(json.dumps({"procedure": graph().procedure, "recordings": [record]}))
        report, actual_code = evaluate_manifest(manifest, tmp_path / f"report-{expected}")
        assert actual_code == code
        assert report["status"] == status
        assert report["real_world_validation"] == "unverified"
        assert report["evaluated_recordings"] == 1
        result = report["records"][0]
        assert result["observed_verdict"] == "PASS"
        assert result["evaluation"]["evidence"]
        evidence_dir = Path(result["evidence_directory"])
        assert (evidence_dir / "frame-0.jpg").exists()
