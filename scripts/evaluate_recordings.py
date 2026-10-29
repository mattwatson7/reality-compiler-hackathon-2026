"""Prepare and evaluate attested camera recordings with the application pipeline.

Run as ``python -m scripts.evaluate_recordings`` from the repository root.
Provenance is a human attestation, not an automated authenticity detector.
"""

import argparse
import hashlib
import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, Literal, Self

from pydantic import Field, StringConstraints, model_validator

from backend.app.compiler import SemanticCompiler
from backend.app.config import ROOT, Settings
from backend.app.evaluator import evaluate
from backend.app.media import normalize_video
from backend.app.meta import MetaClient, MetaDisabled, load_key
from backend.app.perception import (
    Box,
    Initialization,
    LocalCVTracker,
    LocalRegionObserver,
    inspect_video,
    validate_selection,
)
from backend.app.sam import SAMTrackerProvider
from backend.app.schemas import StrictModel
from backend.app.service import JobService
from backend.app.store import Store

Checksum = Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{64}$")]


class Provenance(StrictModel):
    kind: Literal["genuine_recording"]
    captured_at: str = Field(min_length=10, max_length=100)
    description: str = Field(min_length=10, max_length=2000)

    @model_validator(mode="after")
    def timestamp(self) -> Self:
        if datetime.fromisoformat(self.captured_at).tzinfo is None:
            raise ValueError("Capture date must include its timezone")
        return self


class Selections(StrictModel):
    objects: dict[str, Box] = Field(max_length=30)
    regions: dict[str, Box] = Field(max_length=30)


class Recording(StrictModel):
    id: str = Field(min_length=1, max_length=100)
    file: str = Field(min_length=1, max_length=1000)
    source_sha256: Checksum
    normalized_file: str | None = Field(default=None, max_length=1000)
    normalized_sha256: Checksum
    expected_verdict: Literal["PASS", "FAIL", "UNKNOWN"]
    provenance: Provenance
    initialization: Selections


class Manifest(StrictModel):
    procedure: str = Field(min_length=1, max_length=10000)
    recordings: list[Recording] = Field(max_length=30)


def checksum(path: Path) -> str:
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def reject_fixture(path: Path) -> None:
    digest = checksum(path)
    bundled = {checksum(video) for video in (ROOT / "fixtures").glob("*.mp4")}
    if digest in bundled:
        raise ValueError("Bundled synthetic fixture cannot count as a genuine recording")


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def prepare_recording(source: Path, output: Path) -> dict[str, Any]:
    source = source.resolve(strict=True)
    reject_fixture(source)
    if source.stat().st_size > 100 * 1024 * 1024:
        raise ValueError("Recording exceeds 100 MB upload bound")
    # A new directory avoids silently replacing reviewed frames or annotations.
    output.mkdir(parents=True, exist_ok=False)
    normalized = output / "video.mp4"
    try:
        normalize_video(source, normalized, 30, local_cv=True)
        metadata = inspect_video(normalized)
        JobService.save_frames(normalized, {0})
        prepared = {
            "source_file": str(source),
            "source_sha256": checksum(source),
            "normalized_file": str(normalized.resolve()),
            "normalized_sha256": metadata["sha256"],
            **metadata,
            "normalization": "ffmpeg 24fps, aspect-preserving <=1280x720, audio removed",
            "real_world_validation": "unverified",
            "annotation": "Draw normalized boxes on frame-0.jpg; never supply event times",
        }
        write_json(output / "prepare.json", prepared)
        return prepared
    except Exception:
        # Retain the directory as an explicit failed preparation; remove partial media.
        normalized.unlink(missing_ok=True)
        raise


def resolve_file(base: Path, name: str) -> Path:
    candidate = Path(name)
    return (
        (base / candidate).resolve(strict=True)
        if not candidate.is_absolute()
        else candidate.resolve(strict=True)
    )


def evaluate_manifest(
    manifest_path: Path, output: Path, provider: str = "local_cv"
) -> tuple[dict[str, Any], int]:
    output.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "status": "unverified",
        "evaluated_recordings": 0,
        "records": [],
        "real_world_validation": "unverified",
        "sam_used": False,
        "paid_calls": 0,
        "authenticity": "Human-attested provenance; not independently authenticated",
        "required_coverage": ["PASS", "FAIL", "UNKNOWN"],
    }
    client: MetaClient | None = None
    try:
        if provider == "meta_sam":
            settings = Settings.from_env()
            if not (settings.meta_paid_enabled and settings.meta_smoke_approved):
                raise MetaDisabled(
                    "Harness paid SAM requires explicit approval and both enable flags"
                )
            client = MetaClient(
                key=load_key(),
                store=Store(settings.data_dir / "runs.sqlite"),
                paid_enabled=True,
                smoke_approved=True,
            )
            client.discover()
        elif provider != "local_cv":
            raise ValueError("Unknown recording provider")
        manifest = Manifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
        if len({r.id for r in manifest.recordings}) != len(manifest.recordings):
            raise ValueError("Recording IDs must be unique")
        graph = SemanticCompiler().compile(manifest.procedure)
        report["graph"] = graph.model_dump(mode="json")
    except Exception as exc:
        report["error"] = str(exc)
        write_json(output / "report.json", report)
        return report, 2
    coverage: set[str] = set()
    failures = False
    for record in manifest.recordings:
        item: dict[str, Any] = {
            "id": record.id,
            "expected_verdict": record.expected_verdict,
            "provenance": record.provenance.model_dump(),
            "status": "error",
        }
        directory = output / uuid.uuid4().hex
        directory.mkdir()
        try:
            source = resolve_file(manifest_path.parent, record.file)
            reject_fixture(source)
            if (
                source.stat().st_size > 100 * 1024 * 1024
                or checksum(source) != record.source_sha256
            ):
                raise ValueError("Source size or SHA-256 does not match the attested recording")
            normalized = directory / "video.mp4"
            if record.normalized_file:
                prepared = resolve_file(manifest_path.parent, record.normalized_file)
                reject_fixture(prepared)
                if checksum(prepared) != record.normalized_sha256:
                    raise ValueError(
                        "Prepared normalized SHA-256 mismatch; re-annotate first frame"
                    )
                preparation = json.loads(
                    (prepared.parent / "prepare.json").read_text(encoding="utf-8")
                )
                if (
                    preparation["source_sha256"] != record.source_sha256
                    or preparation["normalized_sha256"] != record.normalized_sha256
                ):
                    raise ValueError("Prepared media is not bound to the attested source checksum")
                shutil.copyfile(prepared, normalized)
            else:
                normalize_video(source, normalized, 30, local_cv=True)
            metadata = inspect_video(normalized)
            if metadata["sha256"] != record.normalized_sha256:
                raise ValueError("Normalized SHA-256 differs from the frame used for annotation")
            initialization = Initialization(
                frame_reference=metadata["frame_reference"],
                objects=record.initialization.objects,
                regions=record.initialization.regions,
            )
            validate_selection(initialization, graph, metadata["frame_reference"])
            tracks = (
                SAMTrackerProvider(initialization, client).track(normalized, graph)
                if client is not None
                else LocalCVTracker(initialization).track(normalized, graph)
            )
            observations = LocalRegionObserver(initialization).observe(normalized, graph, tracks)
            result = evaluate(graph, observations, metadata["duration_s"])
            indices = {0}
            for observation in observations:
                indices.update(observation.frame_indices)
            JobService.save_frames(normalized, indices)
            item.update(
                {
                    "status": "matched"
                    if result.verdict == record.expected_verdict
                    else "mismatch",
                    "observed_verdict": result.verdict,
                    "source_sha256": record.source_sha256,
                    "metadata": metadata,
                    "initialization": initialization.model_dump(mode="json"),
                    "tracks": [t.model_dump(mode="json") for t in tracks],
                    "observations": [o.model_dump(mode="json") for o in observations],
                    "evaluation": result.model_dump(mode="json"),
                    "evidence_directory": str(directory.resolve()),
                    "saved_frame_indices": sorted(indices),
                    "provider_provenance": {
                        "compiler": graph.compilation_source,
                        "tracker": "meta.sam-3.1"
                        if client is not None
                        else "local_cv.fixed_hsv.v1",
                        "observer": "mask_hysteresis.v1",
                    },
                }
            )
            report["evaluated_recordings"] += 1
            if item["status"] == "matched":
                coverage.add(record.expected_verdict)
            else:
                failures = True
        except Exception as exc:
            item["error"] = str(exc)
            failures = True
        report["records"].append(item)
        write_json(directory / "result.json", item)
    report["matched_coverage"] = sorted(coverage)
    report["provider"] = provider
    report["sam_used"] = client is not None and report["evaluated_recordings"] > 0
    report["paid_calls"] = len(client.usage) if client is not None else 0
    report["inference_usage"] = client.usage if client is not None else []
    complete = coverage == {"PASS", "FAIL", "UNKNOWN"} and not failures
    report["status"] = (
        "validated_attested_recordings" if complete else "failed" if failures else "unverified"
    )
    report["real_world_validation"] = (
        "validated_on_attested_recordings" if complete else "unverified"
    )
    if not manifest.recordings:
        report["reason"] = (
            "No genuine recordings supplied; real-world PASS/FAIL/UNKNOWN remain unverified"
        )
    elif not complete and not failures:
        report["reason"] = (
            "All three expected outcomes require held-out genuine recording evaluation"
        )
    write_json(output / "report.json", report)
    return report, 0 if complete else 1 if failures else 2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare", type=Path, metavar="SOURCE")
    mode.add_argument("--manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--provider", choices=["local_cv", "meta_sam"], default="local_cv")
    args = parser.parse_args()
    if args.prepare:
        try:
            print(json.dumps(prepare_recording(args.prepare, args.output), indent=2))
            return 0
        except Exception as exc:
            print(
                json.dumps(
                    {"status": "error", "error": str(exc), "real_world_validation": "unverified"}
                )
            )
            return 2
    report, code = evaluate_manifest(args.manifest, args.output, args.provider)
    print(
        json.dumps(
            {key: value for key, value in report.items() if key not in {"records", "graph"}},
            indent=2,
        )
    )
    print(f"Full report: {(args.output / 'report.json').resolve()}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
