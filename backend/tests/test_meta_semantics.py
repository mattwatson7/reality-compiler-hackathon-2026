import json
from pathlib import Path

import pytest

from backend.app.compiler import SemanticCompiler
from backend.tests.test_milestone3_contract import PROCEDURE


class Transport:
    def __init__(self, result):
        self.result = result
        self.requests = []

    def dispatch(self, path, body, **kwargs):
        self.requests.append((path, body, kwargs))
        return self.result


def test_recorded_live_wonder_invalid_spans_are_rejected_without_retry_or_settlement():
    from backend.app.config import ROOT
    from backend.app.meta import MetaContractError
    from backend.app.meta_semantics import LiveMuseWonderCompiler
    from scripts.meta_smoke import PROCEDURE as SMOKE_PROCEDURE

    # Sanitized actual live response, not a synthetic successful provider example.
    raw = json.loads(Path(ROOT / "docs/meta-smoke-wonder-response.json").read_text())
    transport = Transport(raw)
    acknowledged = []
    transport.acknowledge = acknowledged.append
    with pytest.raises(MetaContractError, match=r"events\[0\].source: source_reference"):
        LiveMuseWonderCompiler(transport).compile(SMOKE_PROCEDURE)
    assert len(transport.requests) == 1
    assert not acknowledged


def envelope(content, model="muse-wonder-1.0"):
    return {
        "id": "synthetic",
        "object": "chat.completion",
        "created": 0,
        "model": model,
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": content},
            }
        ],
    }


def test_wonder_adapter_validates_graph_and_requests_context_cost_bound():
    from backend.app.meta_semantics import LiveMuseWonderCompiler

    graph = SemanticCompiler().compile(PROCEDURE).model_copy(update={"compilation_source": "muse"})
    from backend.tests.test_grounding import wire

    transport = Transport(envelope(json.dumps(wire(PROCEDURE))))
    result = LiveMuseWonderCompiler(transport).compile(PROCEDURE)
    assert result == graph
    path, body, options = transport.requests[0]
    assert path == "/v1/chat/completions"
    assert body["max_completion_tokens"] == 4096
    assert body["reasoning_effort"] == "minimal"
    assert "Transient actions belong only in events" in body["messages"][0]["content"]
    source_input = json.loads(body["messages"][1]["content"])
    assert source_input["sources"] == [{"source_id": "clause1", "quote": PROCEDURE}]
    assert set(
        body["response_format"]["json_schema"]["schema"]["$defs"]["SourceSpan"]["properties"]
    ) == {"source_id", "quote"}
    assert options["upper_bound_microusd"] == 4 * 1048576 + 20 * 4096


def test_wonder_rejects_omitted_clause_without_retry():
    from backend.app.meta import MetaContractError
    from backend.app.meta_semantics import LiveMuseWonderCompiler

    text = "The cup is visible. The battery is charged."
    from backend.tests.test_grounding import wire

    graph = wire(text)
    graph["conditions"] = []
    transport = Transport(envelope(json.dumps(graph)))
    with pytest.raises(MetaContractError, match="conditions"):
        LiveMuseWonderCompiler(transport).compile(text)
    assert len(transport.requests) == 1


def test_wonder_cannot_downgrade_mandatory_hidden_requirement_to_optional():
    from backend.app.meta import MetaContractError
    from backend.app.meta_semantics import LiveMuseWonderCompiler

    text = "The cup is visible. The battery is charged."
    from backend.tests.test_grounding import wire

    graph = wire(text)
    graph["conditions"][0]["required"] = False
    transport = Transport(envelope(json.dumps(graph)))
    with pytest.raises(MetaContractError, match="required"):
        LiveMuseWonderCompiler(transport).compile(text)


def test_spark_has_no_reason_to_call_for_geometric_procedure(tmp_path):
    from backend.app.meta_semantics import MuseSparkObserver

    transport = Transport({})
    assert (
        MuseSparkObserver(transport).observe(
            tmp_path / "absent.mp4", SemanticCompiler().compile(PROCEDURE), []
        )
        == []
    )
    assert not transport.requests


def test_chat_refusal_and_model_mismatch_never_yield_evidence():
    from backend.app.meta import MetaContractError
    from backend.app.meta_semantics import chat_content

    for result in [envelope("{}", "wrong"), envelope(None)]:
        with pytest.raises(MetaContractError):
            chat_content(result, "muse-wonder-1.0")


def test_spark_final_claims_require_actual_final_frames_and_unbroken_identity(tmp_path):
    from backend.app.meta_semantics import MuseSparkObserver
    from backend.app.perception import LocalCVTracker, inspect_video
    from backend.tests.test_perception import initialization, video

    source = tmp_path / "synthetic.mp4"
    video(source)
    graph = SemanticCompiler().compile(PROCEDURE + " At end, the cup is visible.")
    metadata = inspect_video(source)
    tracks = LocalCVTracker(initialization(graph, metadata["frame_reference"])).track(source, graph)
    condition = graph.conditions[0]
    claim = {
        "event_id": condition.id,
        "predicate": condition.predicate.model_dump(),
        "frame_indices": list(range(138, 144)),
        "polarity": "CONFIRMED",
        "confidence": 0.9,
        "description": "Synthetic model contract: cup visible in final frames",
    }
    transport = Transport(envelope(json.dumps({"observations": [claim]}), "muse-spark-1.3"))
    observations = MuseSparkObserver(transport).observe(source, graph, tracks)
    assert observations[0].end_s == metadata["duration_s"]
    assert observations[0].evidence.source == "muse_spark"
    assert observations[0].frame_indices[-1] == 143
    invalid = {**claim, "polarity": "CONTRADICTED", "frame_indices": [138]}
    transport.result = envelope(json.dumps({"observations": [claim, invalid]}), "muse-spark-1.3")
    assert MuseSparkObserver(transport).observe(source, graph, tracks) == []
    cup = next(t for t in tracks if t.object_id == condition.predicate.object_id)
    cup.samples[-1].status = "missing"
    assert MuseSparkObserver(transport).observe(source, graph, tracks) == []
