import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import Field

from backend.app.schemas import ObjectTrack, Observation, StrictModel, TaskGraph


class Fixture(StrictModel):
    id: Literal["correct", "incorrect"]
    title: str
    description: str
    video: Literal["correct.mp4", "incorrect.mp4"]
    video_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    graph: TaskGraph
    observations: list[Observation]
    tracks: list[ObjectTrack]


def load_fixture(directory: Path, fixture_id: str) -> Fixture:
    if fixture_id not in {"correct", "incorrect"}:
        raise KeyError(fixture_id)
    fixture = Fixture.model_validate_json((directory / f"{fixture_id}.json").read_text("utf-8"))
    if fixture.id != fixture_id or fixture.video != f"{fixture_id}.mp4":
        raise ValueError("Mismatched fixture video identity")
    if hashlib.sha256((directory / fixture.video).read_bytes()).hexdigest() != fixture.video_sha256:
        raise ValueError("Declared events require the exact bundled fixture video")
    return fixture


def fixture_summaries(directory: Path) -> list[dict[str, str]]:
    return [
        {
            "id": fixture.id,
            "title": fixture.title,
            "description": fixture.description,
            "procedure": fixture.graph.procedure,
        }
        for fixture in [load_fixture(directory, name) for name in ("correct", "incorrect")]
    ]


def export_taskgraph_schema(destination: Path) -> None:
    destination.write_text(json.dumps(TaskGraph.model_json_schema(), indent=2) + "\n", "utf-8")
