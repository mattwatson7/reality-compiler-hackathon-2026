"""Re-evaluate captured M5 observations offline; never sends a model request.

This verifies recorded deterministic results and evidence compatibility. It is
not new perception, not camera acceptance and not a replay of live HTTP itself.
"""

import hashlib
import json
from typing import Any

from backend.app.config import ROOT
from backend.app.evaluator import evaluate
from backend.app.reevaluation import reuse_observations
from backend.app.schemas import Observation, TaskGraph


def replay() -> dict[str, Any]:
    directory = ROOT / "docs/milestone-5"
    index = json.loads((directory / "capture-index.json").read_text(encoding="utf-8"))
    for entry in index["responses"]:
        path = directory / entry["file"]
        if path.resolve().parent != (directory / "responses").resolve():
            raise ValueError("Invalid captured response path")
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
            raise ValueError("Captured response hash mismatch")
    results = []
    for capture in json.loads((directory / "live-results.json").read_text(encoding="utf-8")):
        job = capture["job"]
        graph = TaskGraph.model_validate(job["graph"])
        observations = [Observation.model_validate(o) for o in job["observations"]]
        actual = evaluate(graph, observations, job["duration_s"]).model_dump(mode="json")
        if actual != job["result"]:
            raise ValueError("Captured real-camera deterministic result differs")
        results.append(
            {"case": capture["case"]["name"], "mode": job["mode"], "verdict": actual["verdict"]}
        )
    comparisons = {}
    for name in ("generated", "real-peg"):
        capture = json.loads((directory / f"{name}-comparison.json").read_text(encoding="utf-8"))
        job = capture["job"]
        original = TaskGraph.model_validate(job["graph"])
        observations = [Observation.model_validate(o) for o in job["observations"]]
        verdicts = []
        for snapshot in capture["evaluations"]:
            graph = TaskGraph.model_validate(snapshot["graph"])
            reused, reasons = reuse_observations(original, graph, observations)
            if reasons:
                raise ValueError("Captured comparison unexpectedly incompatible")
            actual = evaluate(graph, reused, job["duration_s"]).model_dump(mode="json")
            if actual != snapshot["result"]:
                raise ValueError("Captured comparison differs from deterministic replay")
            verdicts.append(actual["verdict"])
        comparisons[name] = verdicts
    return {
        "mode": "offline deterministic replay of captured observations",
        "new_network_calls": 0,
        "recorded_results": results,
        "comparisons": comparisons,
        "response_hashes_verified": len(index["responses"]),
    }


if __name__ == "__main__":
    print(json.dumps(replay(), indent=2))
