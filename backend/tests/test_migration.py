import hashlib
import json

import pytest

from backend.app.config import ROOT
from backend.app.fixtures import load_fixture
from backend.app.legacy import TaskGraph as LegacyTaskGraph
from backend.app.migration import migrate_fixture, migrate_legacy_graph


def test_generic_v1_never_invents_predicate_semantics():
    graph = LegacyTaskGraph(
        procedure="Lift cup.",
        objects=[],
        steps=[{"id": "s1", "instruction": "Lift cup."}],
        constraints=[],
    )
    migrated = migrate_legacy_graph(graph)
    assert migrated.version == "2.0"
    assert migrated.compilation_source == "legacy"
    assert migrated.events[0].observability == "UNSUPPORTED"
    assert migrated.events[0].predicate is None


def test_reviewed_v1_fixture_migration_preserves_timestamps():
    raw = json.loads((ROOT / "fixtures/v1/correct.json").read_text("utf-8"))
    migrated = migrate_fixture(raw)
    assert migrated["graph"]["version"] == "2.0"
    assert migrated["observations"][0]["start_s"] == raw["observations"][0]["start_s"]
    assert migrated["observations"][0]["predicate"]["object_id"] == "block"
    raw["graph"]["steps"][0]["instruction"] = "Verify hidden battery charge"
    with pytest.raises(ValueError):
        migrate_fixture(raw)


def test_fixture_declarations_only_apply_to_exact_video(tmp_path):
    raw = json.loads((ROOT / "fixtures/correct.json").read_text("utf-8"))
    assert (
        raw["video_sha256"]
        == hashlib.sha256((ROOT / "fixtures/correct.mp4").read_bytes()).hexdigest()
    )
    (tmp_path / "correct.json").write_text(json.dumps(raw), "utf-8")
    (tmp_path / "correct.mp4").write_bytes(b"a different video")
    with pytest.raises(ValueError, match="fixture video"):
        load_fixture(tmp_path, "correct")
