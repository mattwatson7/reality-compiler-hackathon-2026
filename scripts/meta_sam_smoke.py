"""Independent, default-off SAM-only smoke. Default invocation is offline preflight.

No Wonder, Spark, retries or persistent flag changes. Approval must bind to the
reviewed plan digest in code after a separate explicit human authorization.
"""

import argparse
import hashlib
import json
import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from backend.app.compiler import SemanticCompiler
from backend.app.config import ROOT, Settings
from backend.app.meta import MetaClient, MetaContractError, MetaDisabled
from backend.app.meta import load_key as server_key
from backend.app.perception import Initialization, inspect_video, validate_selection
from backend.app.sam import SAMTrackerProvider
from backend.app.schemas import TaskGraph
from backend.app.store import Store

AUTHORIZATION_ID = "meta-sam-only-m41-2026-10-28"
LIMIT = 14_400
# The human-authorized 2026-10-28 attempt is consumed in the lifetime database.
# Retired after successful live execution; never reuse that approval.
APPROVED_PLAN_SHA256: str | None = None
PLAN_PATH = ROOT / "docs/sam-smoke-plan.json"
GRAPH_PATH = ROOT / "docs/sam-smoke-taskgraph.json"
SELECTION_PATH = ROOT / "docs/sam-smoke-selections.json"
VIDEO_RELATIVE = Path("meta-smoke-2026-10-27-one-wonder-one-sam/video.mp4")
PROCEDURE = (
    "Move the blue block into the visible marked region before moving the cup into that region."
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reviewed_graph() -> TaskGraph:
    graph = TaskGraph.model_validate_json(GRAPH_PATH.read_text(encoding="utf-8"))
    if graph != SemanticCompiler().compile(PROCEDURE):
        raise MetaDisabled("Reviewed local TaskGraph changed; new review required")
    return graph


def preflight(data_dir: Path) -> tuple[TaskGraph, Initialization, dict[str, Any]]:
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    if (
        plan["authorization_id"] != AUTHORIZATION_ID
        or plan["maximum_reservation_microusd"] != LIMIT
        or plan["graph_sha256"] != digest(GRAPH_PATH)
        or plan["selections_sha256"] != digest(SELECTION_PATH)
    ):
        raise MetaDisabled("Reviewed plan digest or bound changed")
    video = data_dir / VIDEO_RELATIVE
    metadata = inspect_video(video)
    if (
        metadata != plan["media"]
        or metadata["sha256"] != plan["video_sha256"]
        or (metadata["frame_count"], metadata["width"], metadata["height"]) != (72, 320, 180)
        or max(50, metadata["frame_count"]) * 200 != LIMIT
    ):
        raise MetaDisabled("Reviewed media changed; no request authorized")
    graph = reviewed_graph()
    initialization = Initialization.model_validate_json(SELECTION_PATH.read_text(encoding="utf-8"))
    validate_selection(initialization, graph, metadata["frame_reference"])
    return graph, initialization, plan


def claim_authorization(store: Store) -> None:
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute(
            "CREATE TABLE IF NOT EXISTS smoke_authorizations "
            "(id TEXT PRIMARY KEY, body TEXT NOT NULL)"
        )
        db.execute(
            "INSERT INTO smoke_authorizations VALUES (?,?)",
            (
                AUTHORIZATION_ID,
                json.dumps({"status": "consumed", "plan_sha256": digest(PLAN_PATH)}),
            ),
        )


class SAMOnlyClient(MetaClient):
    """Consume one attempt before transport; acknowledge only after harness validation."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.attempts = 0
        self.validated_response: dict[str, Any] | None = None
        self.reported_usage: dict[str, int] = {}
        self.estimated_charge_microusd: int | None = None

    def dispatch(
        self, path: str, body: dict[str, Any], *, model: str, upper_bound_microusd: int
    ) -> dict[str, Any]:
        if (
            self.attempts != 0
            or model != "sam-3.1"
            or path != "/v1/responses"
            or type(upper_bound_microusd) is not int
            or upper_bound_microusd != LIMIT
            or self._validate_video_request(body) != LIMIT
        ):
            raise MetaDisabled("Request outside independent one-SAM authorization")
        self.attempts += 1
        raw = super().dispatch(path, body, model=model, upper_bound_microusd=LIMIT)
        usage = raw.get("usage")
        if isinstance(usage, dict) and type(usage.get("video_frames_processed")) is int:
            self.reported_usage = {"video_frames_processed": usage["video_frames_processed"]}
        self.estimated_charge_microusd = self._actual_cost(model, raw, LIMIT)
        return raw

    def acknowledge(self, response: dict[str, Any]) -> None:
        self.validated_response = response  # Adapter success, deferred until strict track review.

    def settle_validated(self) -> None:
        if self.validated_response is None:
            raise MetaContractError("No validated SAM response; reservation retained")
        super().acknowledge(self.validated_response)


def run_once(
    client: SAMOnlyClient, video: Path, graph: TaskGraph, initialization: Initialization
) -> list[dict[str, Any]]:
    tracks = SAMTrackerProvider(initialization, client).track(video, graph)
    if len(tracks) != 2 or any(
        t.invalid_intervals
        or len(t.samples) != 72
        or any(
            s.status != "reliable" or s.frame_index != i or abs(s.time_s - i / 24) > 1e-6
            for i, s in enumerate(t.samples)
        )
        for t in tracks
    ):
        raise MetaContractError("SAM identity/frame/mask validation failed; reservation retained")
    client.settle_validated()
    return [t.model_dump(mode="json") for t in tracks]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute-authorized-once", action="store_true")
    args = parser.parse_args()
    if args.execute_authorized_once and APPROVED_PLAN_SHA256 != digest(PLAN_PATH):
        raise MetaDisabled("Separate human SAM-only authorization is pending")
    settings = Settings.from_env()
    if settings.meta_paid_enabled or settings.meta_smoke_approved or settings.spark_visual_enabled:
        raise MetaDisabled("Persistent paid and Spark flags must remain disabled")
    graph, initialization, plan = preflight(settings.data_dir)
    if not args.execute_authorized_once:
        print(
            json.dumps({"offline_preflight": "validated", "plan_sha256": digest(PLAN_PATH), **plan})
        )
        return 0
    if os.getenv("CI") or os.getenv("PYTEST_CURRENT_TEST"):
        raise MetaDisabled("Paid smoke cannot execute in automated tests or CI")
    # This runner must use the existing lifetime ledger, never initialize a fresh
    # budget in another DATA_DIR. Preserve the old consumed claim and exposure.
    if settings.data_dir != ROOT / "data" or not (settings.data_dir / "runs.sqlite").is_file():
        raise MetaDisabled("Existing lifetime ledger required")
    store = Store(settings.data_dir / "runs.sqlite")
    if store.ledger()["remaining_microusd"] < LIMIT:
        raise MetaDisabled("Insufficient lifetime budget")
    try:
        claim_authorization(store)
    except sqlite3.IntegrityError:
        raise MetaDisabled("SAM-only authorization already consumed; no retry permitted") from None
    directory = settings.data_dir / AUTHORIZATION_ID
    directory.mkdir(exist_ok=False)
    client = SAMOnlyClient(key=server_key(), store=store)
    report: dict[str, Any] = {
        "authorization_id": AUTHORIZATION_ID,
        "plan_sha256": digest(PLAN_PATH),
        "started_at": datetime.now(UTC).isoformat(),
        "status": "stopped",
        "maximum_reservation_microusd": LIMIT,
        "synthetic": True,
        "real_world_validation": "unverified",
        "evaluation_status": "not_run",
        "wonder_requests": 0,
        "spark_requests": 0,
        "automatic_retries": 0,
        "ledger_before": store.ledger(),
        "plan": plan,
    }
    try:
        # Pin the exact submitted bytes in the internally named evidence directory.
        video = directory / "video.mp4"
        video.write_bytes((settings.data_dir / VIDEO_RELATIVE).read_bytes())
        if digest(video) != plan["video_sha256"]:
            raise MetaDisabled("Media changed after preflight")
        if not client.discover().supports("sam-3.1"):
            raise MetaDisabled("SAM entitlement unavailable")
        client.paid_enabled = client.smoke_approved = True
        report["tracks"] = run_once(client, video, graph, initialization)
        report["status"] = "validated_segmentation"
        return 0
    except Exception as exc:
        report["error_type"] = type(exc).__name__
        report["error"] = "SAM smoke stopped; no retry; uncertain exposure retained"
        return 1
    finally:
        client.paid_enabled = client.smoke_approved = False
        report.update(
            finished_at=datetime.now(UTC).isoformat(),
            paid_enabled=False,
            smoke_approved=False,
            attempts=client.attempts,
            reported_usage=client.reported_usage,
            usage=client.usage,
            ledger_after=store.ledger(),
            estimated_charge_microusd=client.estimated_charge_microusd,
            billing_note="Response usage at published rates, not a billing invoice; "
            "uncertain or failed adapter results retain the reservation.",
        )
        # No raw responses, arbitrary remote strings, headers or credentials.
        encoded = json.dumps(report, indent=2)
        key = client._key.get_secret_value()
        if key:
            encoded = encoded.replace(key, "[REDACTED]")
        (directory / "evidence.json").write_text(encoded + "\n", encoding="utf-8")
        print(json.dumps({k: report[k] for k in ("status", "attempts", "usage", "ledger_after")}))


if __name__ == "__main__":
    raise SystemExit(main())
