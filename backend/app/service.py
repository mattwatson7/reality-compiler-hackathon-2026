import hashlib
import json
import logging
import shutil
import threading
import time
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import cv2

from backend.app.config import Settings
from backend.app.evaluator import evaluate
from backend.app.fixtures import load_fixture
from backend.app.media import InvalidMedia, normalize_video, probe_video
from backend.app.meta import MetaClient, MetaContractError, MetaDisabled, ModelCatalog, load_key
from backend.app.meta_semantics import LiveMuseWonderCompiler, MuseSparkObserver
from backend.app.perception import (
    Initialization,
    LocalCVTracker,
    LocalRegionObserver,
    inspect_video,
    validate_selection,
)
from backend.app.providers import (
    CompilerProvider,
    EventProvider,
    FixtureEventObserver,
    FixtureTracker,
    MockCompiler,
    MockEventObserver,
    MockTracker,
    TrackingProvider,
    VisualEventProvider,
    VisualTrackingProvider,
)
from backend.app.reevaluation import evidence_fingerprint, reuse_observations
from backend.app.sam import SAMTrackerProvider
from backend.app.schemas import Observation, TaskGraph
from backend.app.store import Store

logger = logging.getLogger(__name__)


class JobService:
    def __init__(
        self,
        settings: Settings,
        compiler: CompilerProvider | None = None,
        tracker: TrackingProvider | None = None,
        observer: EventProvider | None = None,
        visual_tracker: Callable[[Initialization], VisualTrackingProvider] = LocalCVTracker,
        visual_observer: Callable[[Initialization], VisualEventProvider] = LocalRegionObserver,
        recover_jobs: bool = True,
    ) -> None:
        self.settings = settings
        self.store = Store(settings.data_dir / "runs.sqlite")
        self.media_dir = settings.data_dir / "media"
        self.media_dir.mkdir(parents=True, exist_ok=True)
        self.compiler = compiler or MockCompiler()
        self.meta = MetaClient(
            key=load_key(),
            store=self.store,
            paid_enabled=settings.meta_paid_enabled,
            smoke_approved=settings.meta_smoke_approved,
        )
        if settings.meta_paid_enabled and settings.meta_smoke_approved:
            try:
                self.meta.discover()
            except (MetaContractError, MetaDisabled):
                pass  # Fail closed; health supplies a safe disabled reason.
        self.tracker = tracker or MockTracker()
        self.observer = observer or MockEventObserver()
        self.visual_tracker = visual_tracker
        self.visual_observer = visual_observer
        self.pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="verification")
        self.slots = threading.BoundedSemaphore(4)
        if recover_jobs:
            self.store.recover_interrupted()

    def compile(
        self, procedure: str, client: MetaClient | None = None, *, force_local: bool = False
    ) -> TaskGraph:
        # A future paid provider must own each reservation at its dispatch boundary.
        # The local compiler performs no network call and incurs no cost.
        provider = (
            LiveMuseWonderCompiler(client or self.meta.fork())
            if self.settings.compiler_mode == "muse_wonder" and not force_local
            else self.compiler
        )
        graph = provider.compile(procedure)
        return TaskGraph.model_validate_json(graph.model_dump_json())

    def meta_capabilities(self) -> dict[str, Any]:
        catalog = self.meta.catalog
        if not catalog.authenticated:
            path = self.settings.data_dir / "meta-discovery.json"
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                if raw.get("authenticated") is True:
                    catalog = ModelCatalog(tuple(raw["models"]), True)
            except (OSError, ValueError, KeyError, TypeError):
                pass
        enabled = self.meta.paid_enabled and self.meta.smoke_approved
        return {
            "credential_configured": bool(load_key().get_secret_value()),
            "catalog_authenticated": catalog.authenticated,
            "models": list(catalog.ids),
            "paid_inference_enabled": enabled,
            "sam_selectable": enabled and self.meta.catalog.supports("sam-3.1"),
            "wonder_selectable": enabled and self.meta.catalog.supports("muse-wonder-1.0"),
            "spark_selectable": enabled and self.meta.catalog.supports("muse-spark-1.3"),
            "reason": "Paid inference requires explicit approval and both server enable flags"
            if not enabled
            else (
                "Fresh account catalog verified; paid dispatch is enabled"
                if self.meta.catalog.authenticated
                else "Fresh authenticated discovery required for each server start"
            ),
        }

    def allocate(self, procedure: str, mode: str) -> tuple[str, Path]:
        job_id = uuid.uuid4().hex
        directory = self.media_dir / job_id
        now = time.time()
        self.store.create_job(
            job_id,
            {
                "id": job_id,
                "status": "queued",
                "progress": 0,
                "message": "Queued for local mock verification",
                "mode": mode,
                "procedure": procedure,
                "created_at": now,
                "expires_at": now + self.settings.media_ttl_s,
                "graph": None,
                "result": None,
                "tracks": [],
                "duration_s": None,
                "media_url": None,
                "error": None,
                "preview_url": None,
                "frame_reference": None,
                "media_metadata": None,
                "initialization": None,
                "observations": [],
                "sam_used": False,
                "real_pixel_processing": False,
                "provenance": {},
                "saved_frame_indices": [],
                "inference_usage": [],
            },
        )
        # Metadata must exist before a directory becomes visible to the orphan sweep.
        directory.mkdir()
        return job_id, directory

    def submit(self, job_id: str, fixture_id: str | None = None) -> None:
        future = self.pool.submit(self.process, job_id, fixture_id)
        future.add_done_callback(lambda _: self.slots.release())

    def process(self, job_id: str, fixture_id: str | None) -> None:
        directory = self.media_dir / job_id
        source, video = directory / "source.upload", directory / "video.mp4"
        client = self.meta.fork()
        try:
            self.store.update_job(
                job_id, status="processing", progress=10, message="Preparing video"
            )
            job = self.store.get_job(job_id)
            assert job is not None
            if job["mode"] in {"local_cv", "meta_sam"} and job.get("initialization"):
                client.usage = list(job.get("inference_usage", []))
                self.process_local(job_id, job, video, client)
                return
            if fixture_id:
                fixture = load_fixture(self.settings.fixture_dir, fixture_id)
                shutil.copyfile(self.settings.fixture_dir / fixture.video, video)
                duration = probe_video(video, self.settings.max_duration_s)
                graph = fixture.graph
                tracker: TrackingProvider = FixtureTracker(fixture.tracks)
                observer: EventProvider = FixtureEventObserver(fixture.observations)
            else:
                local_cv = job["mode"] in {"local_cv", "meta_sam"}
                source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
                duration = normalize_video(
                    source,
                    video,
                    min(30, self.settings.max_duration_s)
                    if local_cv
                    else self.settings.max_duration_s,
                    local_cv=local_cv,
                )
                # Keep the exact upload for audit until the same media expiry.
                source.replace(directory / "source.original")
                source_timing = json.loads(video.with_suffix(".timing.json").read_text())
                capture = cv2.VideoCapture(str(video))
                try:
                    dimensions = {
                        "width": int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
                        "height": int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                    }
                finally:
                    capture.release()
                self.store.update_job(
                    job_id,
                    media_metadata={
                        **dimensions,
                        "fps": 24,
                        "source_sha256": source_hash,
                        "normalized_sha256": source_timing["normalized_sha256"],
                        "source_timing": source_timing,
                    },
                )
                graph = self.compile(
                    job["procedure"], client, force_local=job["mode"] != "meta_sam"
                )
                if local_cv:
                    metadata = inspect_video(video)
                    self.save_frames(video, {0})
                    if not graph.objects:
                        # Unsupported-only prose has nothing to initialize or
                        # track. Preserve its requirements and finish honestly
                        # without charging for a doomed SAM request.
                        result = evaluate(graph, [], metadata["duration_s"])
                        self.store.update_job(
                            job_id,
                            status="completed",
                            progress=100,
                            message="No observable objects; inspect unsupported requirements",
                            graph=graph.model_dump(mode="json"),
                            result=result.model_dump(mode="json"),
                            duration_s=metadata["duration_s"],
                            frame_reference=metadata["frame_reference"],
                            media_url=f"/api/jobs/{job_id}/media",
                            preview_url=f"/api/jobs/{job_id}/frames/0",
                            saved_frame_indices=[0],
                            media_metadata={
                                **metadata,
                                "source_timing": source_timing,
                                "source_sha256": source_hash,
                                "normalized_sha256": metadata["sha256"],
                                "transformation": (
                                    "ffmpeg autorotation, fit 1280x720, 24 fps, no audio"
                                ),
                            },
                            inference_usage=client.usage,
                            provenance={
                                "compiler": graph.compilation_source,
                                "tracker": "not_dispatched_no_objects",
                                "observer": "not_dispatched_no_objects",
                            },
                        )
                        return
                    self.store.update_job(
                        job_id,
                        status="awaiting_initialization",
                        progress=35,
                        message="Select both objects and the visible marked region on frame zero",
                        graph=graph.model_dump(mode="json"),
                        duration_s=metadata["duration_s"],
                        media_url=f"/api/jobs/{job_id}/media",
                        preview_url=f"/api/jobs/{job_id}/frames/0",
                        frame_reference=metadata["frame_reference"],
                        saved_frame_indices=[0],
                        inference_usage=client.usage,
                        media_metadata={
                            **metadata,
                            "source_timing": source_timing,
                            "source_sha256": source_hash,
                            "normalized_sha256": metadata["sha256"],
                            "transformation": "ffmpeg autorotation, fit 1280x720, 24 fps, no audio",
                        },
                        provenance={
                            "compiler": graph.compilation_source,
                            "tracker": "local_cv_fixed_hsv_v1",
                            "observer": "region_hysteresis_v1",
                        },
                    )
                    return
                tracker, observer = self.tracker, self.observer
            self.store.update_job(
                job_id,
                progress=40,
                message=(
                    f"Semantic TaskGraph compiled ({graph.compilation_source}); perception mocked"
                ),
                graph=graph.model_dump(mode="json"),
                duration_s=duration,
            )
            reservation = self.store.reserve_cost(
                "fixture-tracker" if fixture_id else "mock-tracker", 0
            )
            tracks = tracker.track(video, graph)
            self.store.settle_cost(reservation, 0)
            self.store.update_job(job_id, progress=65, message="Collecting mock event evidence")
            reservation = self.store.reserve_cost(
                "fixture-events" if fixture_id else "mock-events", 0
            )
            observations = observer.observe(video, graph, tracks)
            self.store.settle_cost(reservation, 0)
            self.store.update_job(job_id, progress=85, message="Evaluating temporal constraints")
            result = evaluate(graph, observations, duration)
            self.store.update_job(
                job_id,
                status="completed",
                progress=100,
                message="Fixture verification complete"
                if fixture_id
                else "Mock run complete — no live inference; evidence unavailable",
                result=result.model_dump(mode="json"),
                tracks=[track.model_dump(mode="json") for track in tracks],
                observations=[item.model_dump(mode="json") for item in observations],
                provenance={
                    "compiler": graph.compilation_source,
                    "tracker": "fixture" if fixture_id else "mock",
                    "observer": "fixture" if fixture_id else "mock",
                },
                media_url=f"/api/jobs/{job_id}/media",
            )
        except Exception as exc:
            logger.exception("Local verification failed for job %s", job_id)
            message = (
                str(exc)
                if isinstance(exc, (InvalidMedia, ValueError, MetaContractError, MetaDisabled))
                else ("Local processing failed. Check server logs and submit again.")
            )
            self.store.update_job(
                job_id,
                status="failed",
                error=message,
                message="Verification failed",
                inference_usage=client.usage,
            )
            video.unlink(missing_ok=True)
        finally:
            # Phase one stores compiler usage before exposing initialization. Phase
            # two owns the combined record; a late phase-one finally must not erase it.
            current = self.store.get_job(job_id)
            if current is not None and len(client.usage) >= len(current.get("inference_usage", [])):
                self.store.update_job(job_id, inference_usage=client.usage)
            source.unlink(missing_ok=True)
            self.cleanup()

    def initialize(self, job_id: str, initialization: Initialization) -> None:
        job = self.get_job(job_id)
        if job is None:
            raise KeyError(job_id)
        if job["status"] == "expired":
            raise TimeoutError("Media expired; upload again")
        if job["status"] != "awaiting_initialization":
            raise RuntimeError("Initialization is accepted only once while awaiting selection")
        graph = TaskGraph.model_validate(job["graph"])
        validate_selection(initialization, graph, job["frame_reference"])
        if not self.slots.acquire(blocking=False):
            raise BlockingIOError("Local job queue is full; try again shortly")
        try:
            if not self.store.claim_initialization(job_id, initialization.model_dump(mode="json")):
                raise RuntimeError("Initialization already submitted or expired")
            self.submit(job_id)
        except BaseException:
            self.slots.release()
            raise

    def process_local(
        self, job_id: str, job: dict[str, Any], video: Path, client: MetaClient | None = None
    ) -> None:
        graph = TaskGraph.model_validate(job["graph"])
        initialization = Initialization.model_validate(job["initialization"])
        validate_selection(initialization, graph, job["frame_reference"])
        self.store.update_job(job_id, progress=45, message="Tracking actual decoded frames")
        client = client or self.meta.fork()
        artifacts: dict[str, str] = {}
        if job["mode"] == "meta_sam":
            sam_tracker = SAMTrackerProvider(initialization, client)
            tracks = sam_tracker.track(video, graph)
            if sam_tracker.segmentation_text is not None:
                encoded = sam_tracker.segmentation_text.encode("utf-8")
                (video.parent / "sam-masks.txt").write_bytes(encoded)
                artifacts["sam_masks_sha256"] = hashlib.sha256(encoded).hexdigest()
        else:
            tracks = self.visual_tracker(initialization).track(video, graph)
        self.store.update_job(
            job_id, progress=70, message="Detecting conservative region transitions"
        )
        observations = self.visual_observer(initialization).observe(video, graph, tracks)
        spark_enabled = self.settings.spark_visual_enabled and job["mode"] == "meta_sam"
        if spark_enabled:
            observations.extend(MuseSparkObserver(client).observe(video, graph, tracks))
        indices = {0}
        for item in observations:
            indices.update(item.frame_indices)
        self.save_frames(video, indices)
        result = evaluate(graph, observations, job["duration_s"])
        self.store.update_job(
            job_id,
            status="completed",
            progress=100,
            message=(
                "Meta SAM tracking complete. Inspect actual masks, evidence and cost."
                if job["mode"] == "meta_sam"
                else "Local OpenCV complete. Inspect tracking quality and evidence. SAM not used."
            ),
            result=result.model_dump(mode="json"),
            tracks=[item.model_dump(mode="json") for item in tracks],
            observations=[item.model_dump(mode="json") for item in observations],
            real_pixel_processing=True,
            sam_used=job["mode"] == "meta_sam",
            provenance={
                "compiler": graph.compilation_source,
                "tracker": "meta.sam-3.1" if job["mode"] == "meta_sam" else "local_cv.fixed_hsv.v1",
                "observer": "mask_hysteresis.v1" + (";muse-spark-1.3" if spark_enabled else ""),
            },
            inference_usage=client.usage,
            saved_frame_indices=sorted(indices),
            perception_artifacts=artifacts,
        )

    @staticmethod
    def save_frames(video: Path, indices: set[int]) -> None:
        if not indices or min(indices) < 0 or max(indices) >= 720:
            raise ValueError("Invalid supporting frame index")
        capture = cv2.VideoCapture(str(video))
        started = time.monotonic()
        try:
            for index in range(max(indices) + 1):
                if time.monotonic() - started > 45:
                    raise InvalidMedia("Saving supporting frames exceeded wall-time bound")
                ok, frame = capture.read()
                if not ok:
                    raise InvalidMedia("Supporting frame could not be decoded")
                if index in indices and not cv2.imwrite(
                    str(video.parent / f"frame-{index}.jpg"), frame
                ):
                    raise InvalidMedia("Could not save supporting frame")
        finally:
            capture.release()

    def cleanup(self, now: float | None = None) -> None:
        timestamp = time.time() if now is None else now
        for job_id in self.store.expired_jobs(timestamp):
            # IDs are generated internally; never derive deletion paths from user filenames.
            directory = self.media_dir / job_id
            if directory.parent.resolve() != self.media_dir.resolve():
                raise ValueError("Invalid stored media path")
            # Expired status is committed before deletion to prevent serving stale media.
            self.store.update_job(
                job_id,
                status="expired",
                media_url=None,
                message="Media expired; metadata retained for audit",
            )
            shutil.rmtree(directory, ignore_errors=True)
        # Retry deletion of expired media, including files held open on Windows.
        for directory in self.media_dir.iterdir():
            job = self.store.get_job(directory.name)
            if directory.is_dir() and (job is None or job["status"] == "expired"):
                shutil.rmtree(directory, ignore_errors=True)

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        self.cleanup()
        return self.store.get_job(job_id)

    def evaluation_history(self, job_id: str) -> list[dict[str, Any]]:
        job = self.get_job(job_id)
        if job is None:
            raise KeyError(job_id)
        original = []
        if job.get("result") is not None:
            original = [
                {
                    "id": job_id,
                    "job_id": job_id,
                    "created_at": job["created_at"],
                    "procedure": job["procedure"],
                    "graph": job["graph"],
                    "result": job["result"],
                    "reuse_status": "original",
                    "reuse_reasons": [],
                    "evidence_fingerprint": evidence_fingerprint(job),
                    "provenance": job.get("provenance", {}),
                    "inference_usage": job.get("inference_usage", []),
                }
            ]
        return original + self.store.evaluations(job_id)

    def reevaluate(self, job_id: str, procedure: str) -> dict[str, Any]:
        job = self.get_job(job_id)
        if job is None:
            raise KeyError(job_id)
        if job["status"] == "expired":
            raise TimeoutError("Media expired; history remains available")
        if job["status"] != "completed":
            raise RuntimeError("Finish the original analysis before re-evaluating")
        if job.get("evidence_seal") and evidence_fingerprint(job) != job["evidence_seal"]:
            raise ValueError("Stored perception integrity mismatch; reuse rejected")
        if len(self.store.evaluations(job_id)) >= 50:
            raise ValueError("Evaluation history limit reached (50 per recording)")
        if not self.slots.acquire(blocking=False):
            raise BlockingIOError("Local job queue is full; try again shortly")
        client = self.meta.fork()
        try:
            original = TaskGraph.model_validate(job["graph"])
            graph = self.compile(
                procedure,
                client,
                force_local=job["mode"] != "meta_sam"
                or job.get("execution_mode") == "offline_capture_review",
            )
            observations = [Observation.model_validate(item) for item in job["observations"]]
            reused, reasons = reuse_observations(original, graph, observations)
            metadata = job.get("media_metadata") or {}
            path = self.media_dir / job_id / "video.mp4"
            if metadata.get("normalized_sha256"):
                with path.open("rb") as stream:
                    digest = hashlib.file_digest(stream, "sha256").hexdigest()
                if digest != metadata["normalized_sha256"]:
                    raise ValueError("Immutable normalized media digest mismatch")
                if job["frame_reference"] != f"{digest}:0":
                    raise ValueError("Immutable frame-zero reference mismatch")
                if any(o.evidence.frame_reference != job["frame_reference"] for o in reused):
                    raise ValueError("Observation evidence belongs to a different time base")
                mask_digest = (job.get("perception_artifacts") or {}).get("sam_masks_sha256")
                if mask_digest:
                    with (path.parent / "sam-masks.txt").open("rb") as stream:
                        if hashlib.file_digest(stream, "sha256").hexdigest() != mask_digest:
                            raise ValueError("Stored SAM mask digest mismatch")
            elif job["mode"] != "fixture":
                reasons.append("Source identity unavailable; new analysis required.")
            result = evaluate(graph, [] if reasons else reused, job["duration_s"])
            record = {
                "id": uuid.uuid4().hex,
                "job_id": job_id,
                "created_at": time.time(),
                "procedure": procedure,
                "graph": graph.model_dump(mode="json"),
                "result": result.model_dump(mode="json"),
                "reuse_status": "needs_perception" if reasons else "reused",
                "reuse_reasons": reasons,
                "evidence_fingerprint": evidence_fingerprint(job),
                "provenance": {**job["provenance"], "compiler": graph.compilation_source},
                "inference_usage": client.usage,
            }
            self.store.append_evaluation(job_id, record)
            return record
        finally:
            self.slots.release()
