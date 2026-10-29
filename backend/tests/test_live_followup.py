import pytest

from backend.app.compiler import SemanticCompiler


def test_final_visual_change_retains_exact_predicate_without_transient_event():
    text = (
        "At end, the cup visibly changes color from green to red "
        "(visual criteria: The cup body is red finally and green initially)."
    )
    graph = SemanticCompiler().compile(text)
    assert not graph.events
    assert len(graph.conditions) == 1
    condition = graph.conditions[0]
    assert condition.observability == "SUPPORTED"
    assert condition.scope == "final"
    assert condition.predicate.type == "visually_confirmed_state_change"
    assert condition.predicate.from_state == "green"
    assert condition.predicate.to_state == "red"
    assert condition.source.quote == text
    extra = SemanticCompiler().compile(text.rstrip(".") + " without spilling.")
    assert any(c.observability == "UNSUPPORTED" for c in extra.conditions)


def test_request_schema_constrains_multiplicity_and_exact_source_instruction():
    from backend.app.grounding import grounded_schema

    text = (
        "The cup enters the visible image region target before "
        "the blue block enters the visible image region target."
    )
    schema = grounded_schema(text)
    assert schema["properties"]["events"]["minItems"] == 2
    assert schema["properties"]["events"]["maxItems"] == 2
    assert schema["properties"]["conditions"]["maxItems"] == 0
    assert schema["$defs"]["Event"]["properties"]["instruction"]["enum"] == [text]


def test_wonder_receives_independently_owned_requirement_metadata():
    import json

    from backend.app.meta_semantics import LiveMuseWonderCompiler
    from backend.tests.test_grounding import wire
    from backend.tests.test_meta_semantics import Transport, envelope

    text = "The cup is visible. Verify the cup is sterile."
    transport = Transport(envelope(json.dumps(wire(text))))
    LiveMuseWonderCompiler(transport).compile(text)
    supplied = json.loads(transport.requests[0][1]["messages"][1]["content"])
    assert supplied["requirement_slots"][1] == {
        "section": "conditions",
        "id": "condition1",
        "source_id": "clause2",
        "required": True,
        "observability": "UNSUPPORTED",
        "scope": "during",
    }


def test_spark_final_state_change_requires_initial_and_every_final_frame(tmp_path):
    import json

    from backend.app.evaluator import evaluate
    from backend.app.meta_semantics import MuseSparkObserver
    from backend.app.perception import LocalCVTracker, inspect_video
    from backend.tests.test_meta_semantics import Transport, envelope
    from backend.tests.test_perception import initialization, video

    source = tmp_path / "synthetic.mp4"
    video(source)
    text = (
        "At end, the cup visibly changes color from red to green "
        "(visual criteria: The cup body is green finally and red initially)."
    )
    graph = SemanticCompiler().compile(text)
    metadata = inspect_video(source)
    tracks = LocalCVTracker(initialization(graph, metadata["frame_reference"])).track(source, graph)
    condition = graph.conditions[0]
    indices = [0, *range(138, 144)]
    claim = {
        "event_id": condition.id,
        "predicate": condition.predicate.model_dump(),
        "frame_indices": indices,
        "polarity": "CONFIRMED",
        "confidence": 0.9,
        "description": "Synthetic schema example, not an actual color observation",
    }
    transport = Transport(envelope(json.dumps({"observations": [claim]}), "muse-spark-1.3"))
    observations = MuseSparkObserver(transport).observe(source, graph, tracks)
    assert len(observations) == 1
    assert evaluate(graph, observations, metadata["duration_s"]).verdict.value == "PASS"
    for missing in indices:
        incomplete = {**claim, "frame_indices": [i for i in indices if i != missing]}
        transport.result = envelope(json.dumps({"observations": [incomplete]}), "muse-spark-1.3")
        assert MuseSparkObserver(transport).observe(source, graph, tracks) == []
    conflicting = {**claim, "polarity": "CONTRADICTED"}
    transport.result = envelope(
        json.dumps({"observations": [claim, conflicting]}), "muse-spark-1.3"
    )
    observations = MuseSparkObserver(transport).observe(source, graph, tracks)
    assert evaluate(graph, observations, metadata["duration_s"]).verdict.value == "UNKNOWN"


def test_source_specific_schema_locks_capabilities_and_literal_criteria():
    from backend.app.grounding import grounded_schema

    text = (
        "At end, the cup visibly changes color from green to red "
        "(visual criteria: The cup body is red finally and green initially)."
    )
    schema = grounded_schema(text)
    item = schema["properties"]["conditions"]["items"]["anyOf"][0]["properties"]
    assert item["observability"]["enum"] == ["SUPPORTED"]
    assert item["scope"]["enum"] == ["final"]
    assert item["predicate"]["anyOf"][0]["properties"]["visual_criteria"]["enum"] == [
        "the cup body is red finally and green initially"
    ]
    unknown = grounded_schema("Verify the cup is sterile.")
    item = unknown["properties"]["conditions"]["items"]["anyOf"][0]["properties"]
    assert item["reason"]["type"] == "string"
    assert item["reason"]["minLength"] == 1


@pytest.mark.parametrize(
    "text",
    [
        "Slide the cup into the visible marked region "
        "before moving the blue block into that region.",
        "Move the blue block into the visible marked region, "
        "then slide the cup into the same region.",
        "Place the cup into the visible image region target "
        "after sliding the blue block into that region.",
    ],
)
def test_ordinary_imperatives_preserve_explicit_order_and_region_reference(text):
    graph = SemanticCompiler().compile(text)
    assert len(graph.events) == 2
    assert not graph.conditions
    assert len(graph.regions) == 1
    assert all(e.observability == "SUPPORTED" for e in graph.events)
    assert graph.constraints[0].ordered_pair() == (
        ("event2", "event1") if " after " in text else ("event1", "event2")
    )
    assert all(e.source.quote == text for e in graph.events)
    qualified = SemanticCompiler().compile(text.rstrip(".") + " without spilling.")
    assert qualified.conditions[0].observability == "UNSUPPORTED"


def test_spark_schema_binds_claims_to_supplied_requirements_only():
    from backend.app.meta_semantics import spark_schema

    text = (
        "At end, the cup visibly changes color from green to red "
        "(visual criteria: The cup body is red finally and green initially)."
    )
    condition = SemanticCompiler().compile(text).conditions[0]
    schema = spark_schema([condition])
    claim = schema["properties"]["observations"]["items"]["anyOf"][0]["properties"]
    assert claim["event_id"]["enum"] == ["condition1"]
    assert claim["predicate"]["properties"]["visual_criteria"]["enum"] == [
        condition.predicate.visual_criteria
    ]


def test_unsupported_only_upload_finishes_unknown_without_object_selection(tmp_path):
    import hashlib
    import time

    from fastapi.testclient import TestClient

    from backend.app.config import ROOT, Settings
    from backend.app.main import create_app

    with TestClient(create_app(Settings(data_dir=tmp_path))) as client:
        response = client.post(
            "/api/jobs/upload",
            data={"procedure": "Verify the cup is sterile.", "perception_mode": "local_cv"},
            files={
                "video": ("clip.mp4", (ROOT / "fixtures/correct.mp4").read_bytes(), "video/mp4")
            },
        )
        assert response.status_code == 202
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            job = client.get("/api/jobs/" + response.json()["id"]).json()
            if job["status"] not in {"queued", "processing"}:
                break
            time.sleep(0.02)
        assert job["status"] == "completed"
        assert job["result"]["verdict"] == "UNKNOWN"
        assert not job["sam_used"]
        assert not job["inference_usage"]
        assert (
            job["media_metadata"]["source_sha256"]
            == hashlib.sha256((ROOT / "fixtures/correct.mp4").read_bytes()).hexdigest()
        )
        assert job["media_metadata"]["normalized_sha256"] == job["media_metadata"]["sha256"]
        assert "24 fps" in job["media_metadata"]["transformation"]


@pytest.mark.parametrize(
    "capture",
    ["live-api-v6-correct", "live-api-v2-reverse", "live-api-v2-occlusion", "live-api-v5-color"],
)
def test_actual_captured_meta_responses_replay_without_network_or_credentials(capture, monkeypatch):
    from backend.app.config import ROOT
    from backend.app.meta import MetaClient
    from scripts.replay_live_validation import replay

    monkeypatch.setattr(MetaClient, "_http", lambda *args: pytest.fail("Network forbidden"))
    result = replay(ROOT / "docs/live-validation" / capture)
    assert result["new_network_calls"] == 0
    assert result["result"]["verdict"] == (
        "FAIL" if "reverse" in capture else "UNKNOWN" if "occlusion" in capture else "PASS"
    )


def test_manual_identity_binding_supports_concrete_objects_without_hidden_qualifiers():
    text = (
        "Slide the red bottle into the visible marked region "
        "before moving the yellow ball into that region."
    )
    graph = SemanticCompiler().compile(text)
    assert [o.label for o in graph.objects] == ["red bottle", "yellow ball"]
    assert len(graph.events) == 2
    hidden = SemanticCompiler().compile(text.replace("red bottle", "sterile bottle"))
    assert hidden.conditions[0].observability == "UNSUPPORTED"
