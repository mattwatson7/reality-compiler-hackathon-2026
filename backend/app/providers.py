"""Local application protocols, deliberately independent of any Meta SDK."""

from pathlib import Path
from typing import Protocol

from backend.app.compiler import SemanticCompiler
from backend.app.perception import VisualTrack
from backend.app.schemas import (
    ObjectTrack,
    Observation,
    TaskGraph,
)


class CompilerProvider(Protocol):
    def compile(self, procedure: str) -> TaskGraph: ...


class TrackingProvider(Protocol):
    def track(self, video: Path, graph: TaskGraph) -> list[ObjectTrack]: ...


class EventProvider(Protocol):
    def observe(
        self, video: Path, graph: TaskGraph, tracks: list[ObjectTrack]
    ) -> list[Observation]: ...


class VisualTrackingProvider(Protocol):
    def track(self, video: Path, graph: TaskGraph) -> list[VisualTrack]: ...


class VisualEventProvider(Protocol):
    def observe(
        self, video: Path, graph: TaskGraph, tracks: list[VisualTrack]
    ) -> list[Observation]: ...


class MockCompiler(SemanticCompiler):
    """Compatibility name for the local controlled-language compiler."""


class MockTracker:
    def track(self, video: Path, graph: TaskGraph) -> list[ObjectTrack]:
        # Unknown user media cannot inherit fixture detections.
        return []


class MockEventObserver:
    def observe(
        self, video: Path, graph: TaskGraph, tracks: list[ObjectTrack]
    ) -> list[Observation]:
        return []


class FixtureTracker:
    def __init__(self, tracks: list[ObjectTrack]) -> None:
        self.tracks = tracks

    def track(self, video: Path, graph: TaskGraph) -> list[ObjectTrack]:
        return self.tracks


class FixtureEventObserver:
    def __init__(self, observations: list[Observation]) -> None:
        self.observations = observations

    def observe(
        self, video: Path, graph: TaskGraph, tracks: list[ObjectTrack]
    ) -> list[Observation]:
        return self.observations
