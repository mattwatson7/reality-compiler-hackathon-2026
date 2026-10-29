import json
import math

import pytest
from pydantic import ValidationError

from backend.app.config import ROOT, Settings
from backend.app.evaluator import evaluate
from backend.app.fixtures import load_fixture
from backend.app.media import InvalidMedia, probe_video
from backend.app.providers import MockCompiler, MockEventObserver, MockTracker
from backend.app.schemas import Evidence, ObjectTrack, Observation, TaskGraph, TrackSample


@pytest.mark.parametrize(
    "procedure,count",
    [
        ("1. Lift cup.\n2. Place cup.", 2),
        ("Lift cup; Place cup", 2),
        ("Lift cup. Then place cup.", 2),
        ("Turn the knob", 1),
    ],
)
def test_fixture_compiler_retains_unknown_instructions_without_inventing_order(procedure, count):
    graph = MockCompiler().compile(procedure)
    assert len(graph.events) + len(graph.conditions) == count
    assert graph.constraints == []
    assert all(item.observability != "SUPPORTED" for item in graph.events + graph.conditions)
    assert MockTracker().track(ROOT, graph) == []
    assert MockEventObserver().observe(ROOT, graph, []) == []


@pytest.mark.parametrize("procedure", ["", "\n", "\n".join(["x"] * 31)])
def test_mock_compiler_rejects_empty_or_excess_steps(procedure):
    with pytest.raises(ValueError):
        MockCompiler().compile(procedure)


def test_exported_schema_and_fixtures_match_current_contract():
    assert json.loads((ROOT / "fixtures/taskgraph.schema.json").read_text("utf-8")) == (
        TaskGraph.model_json_schema()
    )
    for name in ["correct", "incorrect"]:
        fixture = load_fixture(ROOT / "fixtures", name)
        assert probe_video(ROOT / "fixtures" / fixture.video, 300) == pytest.approx(7)
        for track in fixture.tracks:
            assert track.object_id in {obj.id for obj in fixture.graph.objects}
    with pytest.raises(KeyError):
        load_fixture(ROOT / "fixtures", "../../secret")


def test_media_limits_and_unreadable_video(tmp_path):
    with pytest.raises(InvalidMedia):
        probe_video(tmp_path / "missing.mp4", 300)
    with pytest.raises(InvalidMedia):
        probe_video(ROOT / "fixtures/correct.mp4", 1)
    playlist = tmp_path / "fake.mp4"
    playlist.write_text("#EXTM3U\nhttp://example.invalid/video.ts", "utf-8")
    with pytest.raises(InvalidMedia, match="container"):
        probe_video(playlist, 300)


def test_settings_reject_live_mode_and_bad_limits(monkeypatch):
    monkeypatch.setenv("PROVIDER_MODE", "live")
    with pytest.raises(ValueError, match="Only PROVIDER_MODE"):
        Settings.from_env()
    monkeypatch.setenv("PROVIDER_MODE", "fixture")
    monkeypatch.setenv("MEDIA_TTL_SECONDS", "0")
    with pytest.raises(ValueError, match="positive"):
        Settings.from_env()


@pytest.mark.parametrize(
    "box", [(-1, 0, 0.1, 0.1), (0, 0, 0, 1), (0.9, 0, 0.2, 1), (math.nan, 0, 1, 1)]
)
def test_normalized_tracking_boxes_are_validated(box):
    with pytest.raises(ValidationError):
        TrackSample(time_s=0, box=box)


def test_duplicate_and_mismatched_evidence_never_passes():
    fixture = load_fixture(ROOT / "fixtures", "correct")
    graph, observations = fixture.graph, fixture.observations
    observations[0].evidence.id = observations[1].evidence.id
    assert evaluate(graph, observations, 7).verdict == "UNKNOWN"
    fixture = load_fixture(ROOT / "fixtures", "correct")
    fixture.observations[0].evidence.start_s = 1.2
    assert evaluate(fixture.graph, fixture.observations, 7).verdict == "UNKNOWN"
    for duration in [0, -1, math.nan, math.inf]:
        with pytest.raises(ValueError):
            evaluate(graph, [], duration)


def test_all_numeric_fields_reject_nonfinite_or_coerced_values():
    for timestamp in [math.nan, math.inf, "1"]:
        with pytest.raises(ValidationError):
            Evidence(id="e1", start_s=timestamp, end_s=2, source="fixture", description="test")
    with pytest.raises(ValidationError):
        Observation(
            event_id="s1",
            occurrence_id="occ-s1",
            predicate={"type": "object_visible", "object_id": "cup"},
            start_s=1,
            end_s=2,
            confidence=1.1,
            evidence=Evidence(id="e1", start_s=1, end_s=2, source="fixture", description="test"),
        )
    ObjectTrack(
        object_id="cup", source="fixture", samples=[TrackSample(time_s=1, box=(0, 0, 1, 1))]
    )
