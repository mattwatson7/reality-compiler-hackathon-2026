import asyncio
import contextlib
import shutil
import subprocess
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Any, Literal

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import StringConstraints

from backend.app.compiler import validate_procedure
from backend.app.config import ROOT, Settings
from backend.app.fixtures import fixture_summaries, load_fixture
from backend.app.legacy import TaskGraph as LegacyTaskGraph
from backend.app.limits import UploadBodyLimit
from backend.app.media import ffmpeg_binary
from backend.app.meta import MetaContractError, MetaDisabled
from backend.app.perception import Initialization
from backend.app.reevaluation import evidence_fingerprint
from backend.app.schemas import StrictModel, TaskGraph
from backend.app.service import JobService
from backend.app.source_timing import digest


class ProcedureInput(StrictModel):
    procedure: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10000)
    ]


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        service = JobService(config)
        app.state.service = service
        service.cleanup()

        async def sweep() -> None:
            while True:
                await asyncio.sleep(config.cleanup_interval_s)
                await asyncio.to_thread(service.cleanup)

        task = asyncio.create_task(sweep())
        try:
            yield
        finally:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
            await asyncio.to_thread(service.pool.shutdown, wait=True)

    app = FastAPI(title="Reality Compiler", version="0.2.0", lifespan=lifespan)
    # Leave 64 KiB for multipart boundaries and the bounded procedure field.
    app.add_middleware(UploadBodyLimit, max_bytes=config.max_upload_bytes + 65536)

    def service() -> JobService:
        return app.state.service  # type: ignore[no-any-return]

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        meta = service().meta_capabilities()
        return {
            "status": "ok",
            "mode": config.provider_mode,
            "live_inference": meta["paid_inference_enabled"],
            "compiler_source": "muse" if config.compiler_mode == "muse_wonder" else "local_rules",
            "real_muse_compilation": config.compiler_mode == "muse_wonder"
            and meta["wonder_selectable"],
            "real_video_verification": True,
            "sam_used": False,
            "perception_modes": ["fixture", "mock-upload", "local_cv"]
            + (["meta_sam"] if meta["sam_selectable"] else []),
            "local_cv_scope": "Static camera, saturated objects, manual first-frame selection",
            "meta": meta,
        }

    @app.get("/api/taskgraph/schema/v1")
    def legacy_schema() -> dict[str, Any]:
        return LegacyTaskGraph.model_json_schema()

    @app.get("/api/taskgraph/schema")
    def schema() -> dict[str, Any]:
        return TaskGraph.model_json_schema()

    @app.post("/api/compile", response_model=TaskGraph)
    def compile_procedure(body: ProcedureInput) -> TaskGraph:
        try:
            return service().compile(body.procedure)
        except (MetaContractError, MetaDisabled) as exc:
            raise HTTPException(503, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.get("/api/fixtures")
    def fixtures() -> list[dict[str, str]]:
        return fixture_summaries(config.fixture_dir)

    @app.get("/api/costs")
    def costs() -> dict[str, int]:
        return service().store.ledger()

    @app.post("/api/jobs/demo/{fixture_id}", status_code=202)
    def demo(fixture_id: str) -> dict[str, str]:
        try:
            fixture = load_fixture(config.fixture_dir, fixture_id)
        except KeyError as exc:
            raise HTTPException(404, "Unknown fixture") from exc
        svc = service()
        if not svc.slots.acquire(blocking=False):
            raise HTTPException(429, "Local job queue is full; try again shortly")
        job_id, _ = svc.allocate(fixture.graph.procedure, "fixture")
        svc.submit(job_id, fixture_id)
        return {"id": job_id}

    @app.post("/api/jobs/upload", status_code=202)
    async def upload(
        procedure: Annotated[str, Form(min_length=1, max_length=10000)],
        video: Annotated[UploadFile, File()],
        perception_mode: Annotated[str | None, Form()] = None,
        footage_origin: Annotated[
            Literal["unknown", "genuine_camera", "generated"], Form()
        ] = "unknown",
    ) -> dict[str, str]:
        svc = service()
        mode = perception_mode or (
            "mock-upload" if config.provider_mode == "fixture" else config.provider_mode
        )
        if mode not in {"local_cv", "mock-upload", "meta_sam"}:
            await video.close()
            raise HTTPException(422, "Choose local_cv or mock-upload; live SAM is disabled")
        if mode == "meta_sam" and not svc.meta_capabilities()["sam_selectable"]:
            await video.close()
            raise HTTPException(
                503, "Meta SAM is disabled until paid inference is explicitly approved"
            )
        try:
            # Validate before writing media or queueing work.
            validate_procedure(procedure)
        except ValueError as exc:
            await video.close()
            raise HTTPException(422, str(exc)) from exc
        if not svc.slots.acquire(blocking=False):
            await video.close()
            raise HTTPException(429, "Local job queue is full; try again shortly")
        job_id, directory = svc.allocate(procedure, mode)
        svc.store.update_job(job_id, footage_origin=footage_origin)
        submitted = False
        try:
            total = 0
            with (directory / "source.upload").open("wb") as output:
                while chunk := await video.read(1024 * 1024):
                    total += len(chunk)
                    if total > config.max_upload_bytes:
                        raise HTTPException(413, "Video exceeds upload byte limit")
                    output.write(chunk)
            if total == 0:
                raise HTTPException(422, "Video is empty")
            svc.submit(job_id)
            submitted = True
        except BaseException:
            svc.store.update_job(job_id, status="failed", message="Upload rejected")
            shutil.rmtree(directory, ignore_errors=True)
            raise
        finally:
            await video.close()
            if not submitted:
                svc.slots.release()
        return {"id": job_id}

    def get_job(job_id: str) -> dict[str, Any]:
        job = service().get_job(job_id)
        if job is None:
            raise HTTPException(404, "Job not found")
        return job

    @app.get("/api/jobs/{job_id}")
    def job_status(job_id: str) -> dict[str, Any]:
        return get_job(job_id)

    @app.get("/api/jobs/{job_id}/evaluations")
    def evaluation_history(job_id: str) -> list[dict[str, Any]]:
        get_job(job_id)
        return service().evaluation_history(job_id)

    @app.post("/api/jobs/{job_id}/evaluations", status_code=201)
    def reevaluate(job_id: str, body: ProcedureInput) -> dict[str, Any]:
        try:
            validate_procedure(body.procedure)
            return service().reevaluate(job_id, body.procedure)
        except KeyError as exc:
            raise HTTPException(404, "Job not found") from exc
        except TimeoutError as exc:
            raise HTTPException(410, str(exc)) from exc
        except BlockingIOError as exc:
            raise HTTPException(429, str(exc)) from exc
        except (MetaContractError, MetaDisabled) as exc:
            raise HTTPException(503, str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(409, str(exc)) from exc
        except (ValueError, OSError) as exc:
            raise HTTPException(422, "Evidence reuse rejected: " + str(exc)) from exc

    @app.post("/api/jobs/{job_id}/initialize", status_code=202)
    def initialize(job_id: str, body: Initialization) -> dict[str, str]:
        try:
            service().initialize(job_id, body)
        except KeyError as exc:
            raise HTTPException(404, "Job not found") from exc
        except TimeoutError as exc:
            raise HTTPException(410, str(exc)) from exc
        except BlockingIOError as exc:
            raise HTTPException(429, str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(409, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        return {"id": job_id}

    @app.get("/api/jobs/{job_id}/frames/{frame_index}")
    def supporting_frame(job_id: str, frame_index: int) -> FileResponse:
        job = get_job(job_id)
        if job["status"] == "expired":
            raise HTTPException(410, "Media has expired")
        if frame_index not in job.get("saved_frame_indices", []):
            raise HTTPException(404, "Supporting frame unavailable")
        path = config.data_dir / "media" / job["id"] / f"frame-{frame_index}.jpg"
        if not path.is_file():
            raise HTTPException(404, "Supporting frame unavailable")
        return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "no-store"})

    @app.get("/api/jobs/{job_id}/media")
    def media(job_id: str) -> FileResponse:
        job = get_job(job_id)
        if job["status"] == "expired":
            raise HTTPException(410, "Media has expired")
        if not job["media_url"]:
            raise HTTPException(409, "Media is not ready")
        return FileResponse(
            config.data_dir / "media" / job["id"] / "video.mp4",
            media_type="video/mp4",
            headers={"Cache-Control": "no-store"},
        )

    @app.get("/api/jobs/{job_id}/source-frames/{frame_index}")
    def original_frame(job_id: str, frame_index: int) -> FileResponse:
        job = get_job(job_id)
        if job["status"] == "expired":
            raise HTTPException(410, "Media has expired")
        metadata = job.get("media_metadata") or {}
        timing = metadata.get("source_timing")
        if not timing:
            raise HTTPException(409, "Legacy run: exact source frame mapping unavailable")
        if job.get("evidence_seal") and job["evidence_seal"] != evidence_fingerprint(job):
            raise HTTPException(409, "Sealed source timing metadata changed")
        frames = timing["frames"]
        if frame_index < 0 or frame_index >= len(frames):
            raise HTTPException(404, "Source frame unavailable")
        directory = config.data_dir / "media" / job["id"]
        source, video = directory / "source.original", directory / "video.mp4"
        if (
            not source.is_file()
            or not video.is_file()
            or digest(source) != timing["source_sha256"]
            or digest(video) != timing["normalized_sha256"]
            or timing["source_sha256"] != metadata["source_sha256"]
            or timing["normalized_sha256"] != metadata["normalized_sha256"]
        ):
            raise HTTPException(409, "Media identity differs from source timing map")
        path = directory / f"source-frame-{frame_index}.png"
        if not path.is_file():
            try:
                subprocess.run(
                    [
                        ffmpeg_binary(),
                        "-nostdin",
                        "-v",
                        "error",
                        "-y",
                        "-threads",
                        "2",
                        "-protocol_whitelist",
                        "file,pipe",
                        "-i",
                        str(source),
                        "-map",
                        "0:v:0",
                        "-vf",
                        f"select=eq(n\\,{int(frames[frame_index]['source_index'])})",
                        "-frames:v",
                        "1",
                        "-threads",
                        "2",
                        str(path),
                    ],
                    check=True,
                    capture_output=True,
                    timeout=120,
                )
            except (OSError, subprocess.SubprocessError) as exc:
                path.unlink(missing_ok=True)
                raise HTTPException(409, "Source frame could not be decoded") from exc
        return FileResponse(path, media_type="image/png", headers={"Cache-Control": "no-store"})

    # Docker's production build is served from the same origin as the API.
    static_dir = ROOT / "frontend" / "dist"
    if static_dir.is_dir():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")
    return app


app = create_app()
