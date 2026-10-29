import pytest

from backend.app.compiler import SemanticCompiler
from backend.app.evaluator import evaluate
from backend.app.schemas import TaskGraph
from backend.tests.test_semantics import graph_data, obs

PROCEDURE = (
    "Move the blue block into the visible marked region before moving the cup into that region."
)


def test_approved_sentence_is_exact_local_grammar():
    graph = SemanticCompiler().compile(PROCEDURE)
    assert graph.compilation_source == "local_rules"
    assert len(graph.events) == 2
    assert graph.constraints[0].operator == "BEFORE"
    assert all(event.observability == "SUPPORTED" for event in graph.events)
    extended = SemanticCompiler().compile(PROCEDURE.rstrip(".") + " without spilling.")
    assert any(c.observability == "UNSUPPORTED" for c in extended.conditions)


@pytest.mark.parametrize("error", [-1e-8, 1e-8])
def test_final_timestamps_allow_only_representation_error(error):
    data = graph_data()
    data["conditions"] = [
        {
            "id": "final",
            "instruction": data["procedure"],
            "source": data["events"][0]["source"],
            "predicate": {"type": "object_visible", "object_id": "battery"},
            "scope": "final",
        }
    ]
    graph = TaskGraph.model_validate(data)
    final = obs(
        "final",
        predicate={"type": "object_visible", "object_id": "battery"},
        start=5,
        end=6 + error,
    )
    events = [obs(), obs("e2", "controller", 3, 4)]
    assert evaluate(graph, [*events, final], 6).verdict == "PASS"
    final.end_s = final.evidence.end_s = 6 - 1 / 24
    assert evaluate(graph, [*events, final], 6).verdict == "UNKNOWN"


def test_unusable_raw_candidate_cannot_prove_order():
    graph = TaskGraph.model_validate(graph_data())
    a = obs().model_copy(update={"usable": False})
    assert evaluate(graph, [a, obs("e2", "controller", 3, 4)], 6).verdict == "UNKNOWN"
