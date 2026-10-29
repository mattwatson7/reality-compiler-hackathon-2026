"""Import an explicitly labeled offline review of actual captured generated-input evidence.

Creates a fresh internal run, never changes old runs or resets/reserves the ledger.
No Meta transport dispatch occurs. Revised instructions use the local compiler.
"""

import argparse
import copy
import hashlib
import json
import shutil
import time
import uuid
from pathlib import Path

from backend.app.config import ROOT, Settings
from backend.app.reevaluation import evidence_fingerprint
from backend.app.service import JobService
from scripts.replay_milestone5 import replay


def import_capture(service: JobService) -> str:
    replay()  # Check receipt digests and all deterministic results before import.
    capture = json.loads((ROOT / "docs/milestone-5/generated-comparison.json").read_text())
    job = copy.deepcopy(capture["job"])
    assets = ROOT / "docs/live-validation/live-api-v6-correct"
    for name, key in (("video.mp4", "normalized_sha256"), ("source.mp4", "source_sha256")):
        with (assets / name).open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != job["media_metadata"][key]:
                raise ValueError("Captured generated media hash mismatch")
    identifier, directory = service.allocate(job["procedure"], "meta_sam")
    try:
        shutil.copyfile(assets / "video.mp4", directory / "video.mp4")
        shutil.copyfile(assets / "source.mp4", directory / "source.original")
        service.save_frames(directory / "video.mp4", set(job["saved_frame_indices"]))
        for key in ("id", "created_at", "expires_at", "evidence_seal"):
            job.pop(key, None)
        job.update(
            status="completed",
            execution_mode="offline_capture_review",
            footage_origin="generated",
            media_url=f"/api/jobs/{identifier}/media",
            preview_url=f"/api/jobs/{identifier}/frames/0",
            message=(
                "Offline review of actual captured Meta evidence on generated footage; "
                "no new inference."
            ),
        )
        service.store.update_job(identifier, **job)
        stored = service.store.get_job(identifier)
        assert stored is not None
        for previous in capture["evaluations"][1:]:
            snapshot = copy.deepcopy(previous)
            snapshot.update(
                id=uuid.uuid4().hex,
                job_id=identifier,
                created_at=time.time(),
                evidence_fingerprint=evidence_fingerprint(stored),
            )
            service.store.append_evaluation(identifier, snapshot)
        return identifier
    except BaseException:
        service.store.update_job(identifier, status="failed", message="Capture import failed")
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    args = parser.parse_args()
    # Explicit offline settings, independent of root .env paid flags.
    service = review_service(args.data_dir.resolve())
    try:
        identifier = import_capture(service)
        print(
            json.dumps(
                {
                    "id": identifier,
                    "path": f"/?run={identifier}",
                    "mode": "offline_capture_review",
                    "new_model_calls": 0,
                }
            )
        )
    finally:
        service.pool.shutdown(wait=True)


def review_service(data_dir: Path) -> JobService:
    # An import may run alongside the server. It must not recover/fail that
    # server's active jobs or inherit any paid configuration.
    return JobService(Settings(data_dir=data_dir), recover_jobs=False)


if __name__ == "__main__":
    main()
