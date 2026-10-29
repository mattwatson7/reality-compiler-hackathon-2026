"""Offline preflight and import of future controlled camera application runs.

This module never dispatches a compiler, tracker, model or network request.
The freeze digest must be retained independently before any inference starts.
"""

import argparse
import hashlib
import json
import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, Self

from pydantic import Field, model_validator

from backend.app.evaluator import evaluate
from backend.app.media import probe_video
from backend.app.schemas import Evaluation, Observation, StrictModel, TaskGraph


class GroundTruth(StrictModel):
    start_s: float = Field(ge=0, allow_inf_nan=False)
    end_s: float = Field(ge=0, allow_inf_nan=False)
    description: str = Field(min_length=15)

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if self.end_s < self.start_s:
            raise ValueError("Ground truth interval is reversed")
        return self


class CameraCase(StrictModel):
    id: Literal["correct", "reverse", "occlusion"]
    file: str = Field(min_length=1)
    source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    captured_at: datetime
    camera_operator: str = Field(min_length=2)
    rights_basis: str = Field(min_length=20)
    redistribution: Literal["private_only", "permission_documented"]
    genuine_original_continuous_camera: Literal[True]
    inspected_before_inference: Literal[True]
    expected_verdict: Literal["PASS", "FAIL", "UNKNOWN"]
    expected_reason: str = Field(min_length=20)
    ground_truth: list[GroundTruth] = Field(min_length=1)

    @model_validator(mode="after")
    def timezone(self) -> Self:
        if self.captured_at.tzinfo is None:
            raise ValueError("Capture timestamp needs a timezone")
        return self


class CameraManifest(StrictModel):
    version: Literal["1.0"]
    procedure: str = Field(min_length=10, max_length=10000)
    declared_by: str = Field(min_length=2)
    cases: list[CameraCase] = Field(min_length=3, max_length=3)

    @model_validator(mode="after")
    def cases_unique(self) -> Self:
        if {case.id for case in self.cases} != {"correct", "reverse", "occlusion"}:
            raise ValueError("Exactly three distinct controlled scenarios are required")
        if len({case.source_sha256 for case in self.cases}) != 3:
            raise ValueError("Each scenario needs a distinct original")
        return self


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def write_new(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2, allow_nan=False) + "\n")


def preflight(manifest: CameraManifest, base: Path) -> dict[str, Any]:
    """Validate original bytes and bounded media without performing inference."""
    root = Path(__file__).resolve().parents[1]
    excluded = {
        digest(path)
        for directory in (root / "fixtures", root / "recordings" / "generated")
        for path in directory.rglob("*.mp4")
    }
    inventory = root / "docs" / "milestone-5" / "recording-inventory.json"
    if inventory.exists():
        excluded.update(item["sha256"] for item in json.loads(inventory.read_text()))
    records = []
    for case in manifest.cases:
        source = (base / case.file).resolve(strict=True)
        actual = digest(source)
        if actual != case.source_sha256 or actual in excluded:
            raise ValueError("Source hash mismatch or known fixture/prior research footage")
        if source.stat().st_size > 100 * 1024 * 1024:
            raise ValueError("Source exceeds 100 MB")
        duration = probe_video(source, 20)
        if duration < 10 or any(item.end_s > duration for item in case.ground_truth):
            raise ValueError("Require 10–20 seconds and ground truth within the original clip")
        if case.captured_at > datetime.now(UTC):
            raise ValueError("Capture timestamp is in the future")
        records.append({"id": case.id, "source_sha256": actual, "duration_s": duration})
    return {"status": "preflight_only", "real_world_validation": "pending", "cases": records}


def freeze(manifest_path: Path, output: Path) -> str:
    manifest = CameraManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    checked = preflight(manifest, manifest_path.parent)
    payload = {
        "frozen_at": datetime.now(UTC).isoformat(),
        "manifest": manifest.model_dump(mode="json"),
        "preflight": checked,
    }
    seal = hashlib.sha256(canonical(payload)).hexdigest()
    write_new(output, {"sha256": seal, "payload": payload})
    return seal


def load_frozen(path: Path, expected_seal: str) -> tuple[CameraManifest, datetime]:
    frozen = json.loads(path.read_text(encoding="utf-8"))
    actual = hashlib.sha256(canonical(frozen["payload"])).hexdigest()
    if actual != expected_seal or frozen["sha256"] != actual:
        raise ValueError("Frozen expectations changed or independent seal mismatch")
    timestamp = datetime.fromisoformat(frozen["payload"]["frozen_at"])
    if timestamp.tzinfo is None:
        raise ValueError("Freeze timestamp needs a timezone")
    manifest = CameraManifest.model_validate_json(json.dumps(frozen["payload"]["manifest"]))
    return manifest, timestamp


def import_result(
    case: CameraCase,
    procedure: str,
    frozen_at: datetime,
    job: dict[str, Any],
    normalized: Path,
) -> dict[str, Any]:
    """Check an exported completed /api/jobs/{id} response, never expected labels."""
    if job.get("status") != "completed" or job.get("mode") not in {"local_cv", "meta_sam"}:
        raise ValueError("Require a completed normal application camera job")
    created = job.get("created_at")
    if not isinstance(created, (float, int)) or not math.isfinite(created):
        raise ValueError("Missing application creation timestamp")
    if created <= frozen_at.timestamp():
        raise ValueError("Application job must start after expectation freeze")
    metadata = job.get("media_metadata") or {}
    media_hash = digest(normalized)
    if (
        metadata.get("source_sha256") != case.source_sha256
        or metadata.get("normalized_sha256") != media_hash
        or job.get("frame_reference") != f"{media_hash}:0"
    ):
        raise ValueError("Application source/normalized media identity mismatch")
    graph = TaskGraph.model_validate(job["graph"])
    if graph.procedure != procedure or job.get("procedure") != procedure:
        raise ValueError("Application instruction differs from frozen instruction")
    observations = [Observation.model_validate(item) for item in job["observations"]]
    for item in observations:
        if (
            item.evidence.source not in {"local_cv", "meta_sam", "muse_spark"}
            or item.evidence.frame_reference != job["frame_reference"]
            or not item.provenance
            or not item.frame_indices
            or not set(item.frame_indices) <= set(job.get("saved_frame_indices", []))
        ):
            raise ValueError("Observation lacks normal pipeline provenance or saved frames")
    result = Evaluation.model_validate_json(json.dumps(job["result"]))
    replay = evaluate(graph, observations, job["duration_s"])
    if result != replay:
        raise ValueError("Imported verdict differs from deterministic evidence evaluation")
    provenance = job.get("provenance") or {}
    if (
        provenance.get("compiler") != graph.compilation_source
        or provenance.get("tracker") not in {"meta.sam-3.1", "local_cv.fixed_hsv.v1"}
        or not str(provenance.get("observer", "")).startswith("mask_hysteresis.v1")
        or not job.get("real_pixel_processing")
    ):
        raise ValueError("Application provider provenance is missing or inconsistent")
    return {
        "id": case.id,
        "job_id": job["id"],
        "source_sha256": case.source_sha256,
        "normalized_sha256": media_hash,
        "expected_verdict": case.expected_verdict,
        "actual_verdict": result.verdict.value,
        "matches_predeclared_expectation": result.verdict.value == case.expected_verdict,
        "result": result.model_dump(mode="json"),
        "provenance": provenance,
        "status": "import_validated_acceptance_pending",
        "real_world_validation": "pending_live_and_browser_human_review",
        "limitation": "Exports are untrusted; structural validation cannot attest live execution, "
        "camera authenticity, rights, masks, identity continuity or browser inspection.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", type=Path)
    mode.add_argument("--freeze", type=Path)
    mode.add_argument("--import-result", type=Path, help="Saved normal application job JSON")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--frozen", type=Path)
    parser.add_argument("--seal")
    parser.add_argument("--case", choices=["correct", "reverse", "occlusion"])
    parser.add_argument("--normalized", type=Path)
    args = parser.parse_args()
    try:
        if args.freeze:
            if args.output is None:
                raise ValueError("--output is required")
            report: Any = {"frozen_sha256": freeze(args.freeze, args.output)}
        elif args.preflight:
            manifest = CameraManifest.model_validate_json(
                args.preflight.read_text(encoding="utf-8")
            )
            report = preflight(manifest, args.preflight.parent)
        else:
            if not all([args.frozen, args.seal, args.case, args.normalized, args.output]):
                raise ValueError("Import needs --frozen --seal --case --normalized --output")
            manifest, timestamp = load_frozen(args.frozen, args.seal)
            case = next(case for case in manifest.cases if case.id == args.case)
            report = import_result(
                case,
                manifest.procedure,
                timestamp,
                json.loads(args.import_result.read_text(encoding="utf-8")),
                args.normalized,
            )
            write_new(args.output, report)
        print(json.dumps(report, indent=2))
        return 0
    except (ValueError, OSError, KeyError, StopIteration, TypeError) as exc:
        print(json.dumps({"status": "rejected", "error": str(exc), "validation": "pending"}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
