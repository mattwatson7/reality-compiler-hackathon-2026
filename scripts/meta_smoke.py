"""One authorization, consumed before dispatch. Never run from CI or retry this run.

2026-10-27 human scope: Wonder then SAM, no Spark, <=4,420,224 micro-USD.
Prices/contracts re-read from official dev.meta.ai docs before this execution.
"""

import argparse
import json
import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from backend.app.config import Settings
from backend.app.evaluator import evaluate
from backend.app.meta import MetaClient, MetaContractError, MetaDisabled
from backend.app.meta import load_key as server_key
from backend.app.meta_semantics import LiveMuseWonderCompiler
from backend.app.perception import Box, Initialization, LocalRegionObserver, inspect_video
from backend.app.sam import SAMTrackerProvider
from backend.app.schemas import TaskGraph
from backend.app.store import Store

AUTHORIZATION_ID = "meta-smoke-2026-10-27-one-wonder-one-sam"
AUTHORIZATION_CONSUMED = True  # Retired after the recorded live attempt; no paid reruns.
LIMIT = 4_420_224
PROCEDURE = (
    "Move the blue block into the visible marked region before moving the cup into that region."
)
PLAN = (("muse-wonder-1.0", 4_276_224), ("sam-3.1", 144_000))


def migrate_authorization(store: Store) -> None:
    """Keep authorization outside expiring playback jobs; preserve the consumed claim."""
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute(
            "CREATE TABLE IF NOT EXISTS smoke_authorizations "
            "(id TEXT PRIMARY KEY, body TEXT NOT NULL)"
        )
        legacy = db.execute("SELECT body FROM jobs WHERE id=?", (AUTHORIZATION_ID,)).fetchone()
        if legacy is not None:
            db.execute(
                "INSERT OR IGNORE INTO smoke_authorizations VALUES (?,?)",
                (AUTHORIZATION_ID, legacy[0]),
            )
            db.execute("DELETE FROM jobs WHERE id=?", (AUTHORIZATION_ID,))


def claim_authorization(store: Store) -> None:
    migrate_authorization(store)
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        committed = db.execute(
            "SELECT COALESCE(SUM(COALESCE(actual,reserved)),0) FROM costs"
        ).fetchone()[0]
        if committed + LIMIT > store.ledger()["cap_microusd"]:
            raise MetaDisabled("Insufficient lifetime budget for the combined conservative bounds")
        # Fixed primary key survives crash/restart. Never delete or reset this claim.
        db.execute(
            "INSERT INTO smoke_authorizations VALUES (?,?)",
            (AUTHORIZATION_ID, json.dumps({"status": "authorization_consumed", "limit": LIMIT})),
        )


class SmokeClient(MetaClient):
    attempts = 0
    first_validated = False

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.responses: list[dict[str, Any]] = []

    def dispatch(
        self, path: str, body: dict[str, Any], *, model: str, upper_bound_microusd: int
    ) -> dict[str, Any]:
        if self.attempts >= len(PLAN):
            raise MetaDisabled("Smoke request allowance exhausted")
        expected, bound = PLAN[self.attempts]
        if (
            model != expected
            or type(upper_bound_microusd) is not int
            or not 0 < upper_bound_microusd <= bound
            or (self.attempts == 1 and not self.first_validated)
        ):
            raise MetaDisabled("Request outside the single smoke authorization")
        self.attempts += 1  # Consume even on timeout, rejection or validation failure.
        return super().dispatch(path, body, model=model, upper_bound_microusd=bound)

    def acknowledge(self, response: dict[str, Any]) -> None:
        pending = self._pending.get(id(response))
        if pending is not None and pending[0] is response and self.attempts == 1:
            self.first_validated = True
        super().acknowledge(response)

    def _http(self, method: str, path: str, body: dict[str, Any] | None) -> dict[str, Any]:
        try:
            response = super()._http(method, path, body)
        except (MetaContractError, MetaDisabled) as exc:
            self.last_transport_error = str(exc)  # Parent diagnostics suppress remote bodies.
            raise
        if method == "POST":
            # Keep only contract evidence; exclude reasoning and arbitrary remote metadata.
            selected = {
                k: response[k]
                for k in ("id", "object", "model", "status", "usage")
                if k in response
            }
            selected["response_fields"] = sorted(response)
            if "choices" in response:
                selected["choices"] = [
                    {
                        "index": c.get("index"),
                        "finish_reason": c.get("finish_reason"),
                        "message": {k: c.get("message", {}).get(k) for k in ("role", "content")},
                    }
                    for c in response["choices"]
                    if isinstance(c, dict)
                ]
            if "output" in response:
                selected["output"] = [
                    v
                    for v in response["output"]
                    if isinstance(v, dict) and v.get("type") == "message"
                ]
            encoded = json.dumps(selected)
            secret = self._key.get_secret_value()
            self.responses.append(json.loads(encoded.replace(secret, "[REDACTED]")))
        return response


def synthetic_clip(path: Path) -> None:
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter.fourcc(*"mp4v"), 24, (320, 180))
    if not writer.isOpened():
        raise ValueError("Synthetic video encoder unavailable")
    try:
        for index in range(72):
            frame = np.full((180, 320, 3), 235, dtype=np.uint8)
            cv2.rectangle(frame, (170, 15), (309, 164), (50, 50, 50), 2)
            # Objects are always visible; only frame-zero geometry initializes identity.
            bx = int(25 + min(1, max(0, (index - 10) / 18)) * 175)
            cx = int(75 + min(1, max(0, (index - 40) / 18)) * 175)
            cv2.rectangle(frame, (bx, 40), (bx + 25, 65), (220, 50, 20), -1)
            cv2.rectangle(frame, (cx, 110), (cx + 20, 139), (30, 160, 40), -1)
            cv2.circle(frame, (cx + 23, 122), 7, (30, 160, 40), 3)
            writer.write(frame)
    finally:
        writer.release()


def selections(graph: TaskGraph, reference: str) -> Initialization:
    objects = {}
    for obj in graph.objects:
        label = (obj.label + " " + obj.description).lower()
        if "block" in label and "cup" not in label:
            objects[obj.id] = Box(x=24 / 320, y=39 / 180, width=28 / 320, height=28 / 180)
        elif "cup" in label and "block" not in label:
            objects[obj.id] = Box(x=74 / 320, y=109 / 180, width=34 / 320, height=33 / 180)
        else:
            raise ValueError("Compiled object cannot bind unambiguously to synthetic frame zero")
    if len(objects) != 2 or len(graph.regions) != 1:
        raise ValueError("Unexpected compiled geometry; second inference blocked")
    return Initialization(
        frame_reference=reference,
        objects=objects,
        regions={
            r.id: Box(x=170 / 320, y=15 / 180, width=140 / 320, height=150 / 180)
            for r in graph.regions
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute-authorized-once", action="store_true")
    args = parser.parse_args()
    if AUTHORIZATION_CONSUMED:
        raise MetaDisabled("This live authorization is consumed; new human authorization required")
    if not args.execute_authorized_once or os.getenv("CI") or os.getenv("PYTEST_CURRENT_TEST"):
        raise MetaDisabled("Explicit one-shot execution outside automated tests required")
    settings = Settings.from_env()
    if settings.meta_paid_enabled or settings.meta_smoke_approved or settings.spark_visual_enabled:
        raise MetaDisabled("Persistent paid/Spark flags must remain disabled")
    store = Store(settings.data_dir / "runs.sqlite")
    directory = settings.data_dir / AUTHORIZATION_ID
    try:
        claim_authorization(store)
    except sqlite3.IntegrityError:
        raise MetaDisabled(
            "Authorization already consumed; new human authorization required"
        ) from None
    directory.mkdir(exist_ok=False)
    client = SmokeClient(key=server_key(), store=store, paid_enabled=False, smoke_approved=False)
    client.responses = []
    report: dict[str, Any] = {
        "started_at": datetime.now(UTC).isoformat(),
        "authorization_id": AUTHORIZATION_ID,
        "combined_reservation_limit_microusd": LIMIT,
        "ledger_before": store.ledger(),
        "synthetic": True,
        "real_world_validation": "unverified",
        "procedure": PROCEDURE,
        "evaluation_status": "unverified",
        "spark_requests": 0,
        "pricing_source": "https://dev.meta.ai/docs/pricing-rate-limits",
        "pricing_checked_date": "2026-10-27",
        "automatic_retries": 0,
    }
    try:
        synthetic_clip(directory / "video.mp4")
        metadata = inspect_video(directory / "video.mp4")
        report["media"] = metadata
        catalog = client.discover()
        if not all(catalog.supports(model) for model, _ in PLAN):
            raise MetaDisabled("Both authorized models must be in the authenticated catalog")
        report["catalog"] = list(catalog.ids)
        client.paid_enabled = client.smoke_approved = True
        graph = LiveMuseWonderCompiler(client).compile(PROCEDURE)
        report["graph"] = graph.model_dump(mode="json")
        initialization = selections(graph, metadata["frame_reference"])
        report["initialization"] = initialization.model_dump(mode="json")
        tracks = SAMTrackerProvider(initialization, client).track(directory / "video.mp4", graph)
        report["tracks"] = [track.model_dump(mode="json") for track in tracks]
        observations = LocalRegionObserver(initialization).observe(
            directory / "video.mp4", graph, tracks
        )
        report["observations"] = [item.model_dump(mode="json") for item in observations]
        report["evaluation"] = evaluate(graph, observations, metadata["duration_s"]).model_dump(
            mode="json"
        )
        report["evaluation_status"] = "evaluated"
        report["status"] = "completed"
        return 0
    except Exception as exc:
        report["status"] = "stopped"
        report["error_type"] = type(exc).__name__
        report["error"] = (
            str(exc)
            if isinstance(exc, (MetaDisabled, MetaContractError))
            else "Local validation failed"
        )
        report["transport_error"] = getattr(client, "last_transport_error", None)
        return 1
    finally:
        client.paid_enabled = client.smoke_approved = False
        report.update(
            finished_at=datetime.now(UTC).isoformat(),
            paid_enabled=False,
            smoke_approved=False,
            attempts=client.attempts,
            usage=client.usage,
            ledger_after=store.ledger(),
            responses=client.responses,
        )
        encoded = json.dumps(report, indent=2)
        key = client._key.get_secret_value()
        if key:
            encoded = encoded.replace(key, "[REDACTED]")
        (directory / "evidence.json").write_text(encoded + "\n", encoding="utf-8")
        with store.connect() as db:
            db.execute(
                "UPDATE smoke_authorizations SET body=? WHERE id=?",
                (
                    json.dumps(
                        {"status": "consumed_finished", "report": str(directory / "evidence.json")}
                    ),
                    AUTHORIZATION_ID,
                ),
            )
        print(
            json.dumps(
                {
                    k: report[k]
                    for k in ("status", "attempts", "usage", "ledger_after", "paid_enabled")
                }
            )
        )


if __name__ == "__main__":
    raise SystemExit(main())
