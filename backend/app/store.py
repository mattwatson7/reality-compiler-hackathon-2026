"""SQLite metadata and cost reservations. All money is integer micro-USD."""

import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any

CAP_MICROUSD = 100_000_000


class BudgetExceeded(RuntimeError):
    pass


class Store:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS evaluations (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    id TEXT UNIQUE NOT NULL, job_id TEXT NOT NULL, body TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS costs (
                    id TEXT PRIMARY KEY, provider TEXT NOT NULL,
                    reserved INTEGER NOT NULL CHECK(reserved >= 0),
                    actual INTEGER CHECK(actual >= 0 AND actual <= reserved),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
            """)

    def connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path, timeout=30)

    def create_job(self, job_id: str, body: dict[str, Any]) -> None:
        with self.connect() as db:
            db.execute("INSERT INTO jobs VALUES (?, ?)", (job_id, json.dumps(body)))

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self.connect() as db:
            row = db.execute("SELECT body FROM jobs WHERE id=?", (job_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def evaluations(self, job_id: str) -> list[dict[str, Any]]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT body FROM evaluations WHERE job_id=? ORDER BY sequence", (job_id,)
            ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def append_evaluation(self, job_id: str, body: dict[str, Any]) -> None:
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT body FROM jobs WHERE id=?", (job_id,)).fetchone()
            if row is None:
                raise KeyError(job_id)
            job = json.loads(row[0])
            import time

            if job["status"] != "completed" or job["expires_at"] <= time.time():
                raise TimeoutError("Completed, unexpired media is required")
            from backend.app.reevaluation import evidence_fingerprint

            if evidence_fingerprint(job) != body["evidence_fingerprint"]:
                raise ValueError("Perception changed during compilation; reuse rejected")
            count = db.execute(
                "SELECT COUNT(*) FROM evaluations WHERE job_id=?", (job_id,)
            ).fetchone()[0]
            if count >= 50:
                raise ValueError("Evaluation history limit reached (50 per recording)")
            db.execute(
                "INSERT INTO evaluations(id,job_id,body) VALUES (?,?,?)",
                (body["id"], job_id, json.dumps(body)),
            )

    def update_job(self, job_id: str, **updates: Any) -> None:
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT body FROM jobs WHERE id=?", (job_id,)).fetchone()
            if row is None:
                raise KeyError(job_id)
            body = json.loads(row[0])
            if body["status"] == "expired" and updates.get("status") != "expired":
                return
            body.update(updates)
            if updates.get("status") == "completed":
                from backend.app.reevaluation import evidence_fingerprint

                body["evidence_seal"] = evidence_fingerprint(body)
            db.execute("UPDATE jobs SET body=? WHERE id=?", (json.dumps(body), job_id))

    def recover_interrupted(self) -> None:
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            for job_id, encoded in db.execute("SELECT id, body FROM jobs").fetchall():
                body = json.loads(encoded)
                if body["status"] in {"queued", "processing"}:
                    body.update(status="failed", message="Server restarted; submit the run again.")
                    db.execute("UPDATE jobs SET body=? WHERE id=?", (json.dumps(body), job_id))

    def claim_initialization(self, job_id: str, initialization: dict[str, Any]) -> bool:
        """Atomically reject duplicate submissions across concurrent request threads."""
        import time

        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT body FROM jobs WHERE id=?", (job_id,)).fetchone()
            if row is None:
                return False
            body = json.loads(row[0])
            if body["status"] != "awaiting_initialization" or body["expires_at"] <= time.time():
                return False
            body.update(
                status="queued",
                initialization=initialization,
                message="Queued for local OpenCV tracking",
            )
            db.execute("UPDATE jobs SET body=? WHERE id=?", (json.dumps(body), job_id))
            return True

    def expired_jobs(self, now: float) -> list[str]:
        with self.connect() as db:
            rows = db.execute("SELECT id, body FROM jobs").fetchall()
        return [
            job_id
            for job_id, raw in rows
            if (body := json.loads(raw))["expires_at"] <= now and body["status"] != "expired"
        ]

    def reserve_cost(self, provider: str, upper_bound_microusd: int) -> str:
        if type(upper_bound_microusd) is not int or upper_bound_microusd < 0:
            raise ValueError("Reservation must be nonnegative integer micro-USD")
        reservation_id = uuid.uuid4().hex
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            total = db.execute("SELECT COALESCE(SUM(COALESCE(actual, reserved)),0) FROM costs")
            if total.fetchone()[0] + upper_bound_microusd > CAP_MICROUSD:
                raise BudgetExceeded("$100 internal API budget exhausted; dispatch blocked")
            db.execute(
                "INSERT INTO costs(id,provider,reserved) VALUES (?,?,?)",
                (reservation_id, provider, upper_bound_microusd),
            )
        return reservation_id

    def settle_cost(self, reservation_id: str, actual_microusd: int) -> None:
        if type(actual_microusd) is not int or actual_microusd < 0:
            raise ValueError("Actual cost must be nonnegative integer micro-USD")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT reserved,actual FROM costs WHERE id=?", (reservation_id,)
            ).fetchone()
            if row is None or row[1] is not None or actual_microusd > row[0]:
                raise ValueError("Invalid, settled, or exceeded reservation")
            db.execute("UPDATE costs SET actual=? WHERE id=?", (actual_microusd, reservation_id))

    def ledger(self) -> dict[str, int]:
        with self.connect() as db:
            total, count = db.execute(
                "SELECT COALESCE(SUM(COALESCE(actual,reserved)),0), COUNT(*) FROM costs"
            ).fetchone()
        return {
            "cap_microusd": CAP_MICROUSD,
            "committed_microusd": total,
            "remaining_microusd": CAP_MICROUSD - total,
            "reservations": count,
        }
