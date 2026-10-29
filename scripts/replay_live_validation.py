"""Offline replay of sanitized actual Meta responses, never a new live request.

Usage: uv run python -m scripts.replay_live_validation live-api-v6-correct
Captured videos are generated inputs; replay cannot establish camera validation.
No key, transport HTTP client, paid flags, or ledger are used.
"""

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from backend.app.config import ROOT
from backend.app.evaluator import evaluate
from backend.app.meta_semantics import LiveMuseWonderCompiler, MuseSparkObserver
from backend.app.perception import Initialization, LocalRegionObserver, inspect_video
from backend.app.sam import SAMTrackerProvider


class RecordedResponses:
    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self.responses = responses
        self.used: list[str] = []

    def dispatch(
        self, path: str, body: dict[str, Any], *, model: str, upper_bound_microusd: int
    ) -> dict[str, Any]:
        if not self.responses:
            raise ValueError("Replay has no response for an additional request")
        raw = self.responses.pop(0)
        if raw.get("model") != model or body.get("model") != model:
            raise ValueError("Recorded model/request mismatch")
        self.used.append(model)
        return raw


def replay(directory: Path) -> dict[str, Any]:
    report = json.loads((directory / "report.json").read_text())
    if report.get("synthetic") is not True or report.get("status") != "completed":
        raise ValueError("Only completed, explicitly synthetic-input captures can be replayed")
    responses = []
    for entry in report["responses"]:
        name = entry["file"]
        if Path(name).name != name:
            raise ValueError("Response filename must remain inside the evidence directory")
        data = (directory / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != entry["sha256"]:
            raise ValueError("Captured response digest mismatch")
        responses.append(json.loads(data))
    transport = RecordedResponses(responses)
    job = report["job"]
    video = directory / "video.mp4"
    metadata = inspect_video(video)
    if metadata["sha256"] != report["normalized_video_sha256"]:
        raise ValueError("Captured normalized video digest mismatch")
    graph = LiveMuseWonderCompiler(transport).compile(job["procedure"])
    initialization = Initialization.model_validate_json(json.dumps(job["initialization"]))
    tracks = SAMTrackerProvider(initialization, transport).track(video, graph)
    observations = LocalRegionObserver(initialization).observe(video, graph, tracks)
    if transport.responses:
        observations.extend(MuseSparkObserver(transport).observe(video, graph, tracks))
    if transport.responses:
        raise ValueError("Captured responses were not all used")
    result = evaluate(graph, observations, metadata["duration_s"])
    if result.model_dump(mode="json") != job["result"]:
        raise ValueError("Current deterministic evaluation differs from captured evaluation")
    return {
        "mode": "offline replay of actual captured inference",
        "new_network_calls": 0,
        "synthetic_input": True,
        "genuine_recording_validation": "unverified",
        "models_replayed": transport.used,
        "result": result.model_dump(mode="json"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "capture",
        choices=[
            "live-api-v6-correct",
            "live-api-v2-reverse",
            "live-api-v2-missing",
            "live-api-v2-repeated",
            "live-api-v2-occlusion",
            "live-api-v2-ambiguous",
            "live-api-v2-incomplete",
            "live-api-v4-unsupported",
            "live-api-v5-color",
        ],
    )
    args = parser.parse_args()
    print(json.dumps(replay(ROOT / "docs/live-validation" / args.capture), indent=2))


if __name__ == "__main__":
    main()
