"""Behavioral contract for semantic TaskGraph v2, independent of AI services."""

from copy import deepcopy

import pytest
from pydantic import ValidationError

from backend.app.evaluator import evaluate
from backend.app.schemas import Observation, TaskGraph


def graph_data():
    text = "Battery enters case before controller."
    source = {"start": 0, "end": len(text), "quote": text}
    return {
        "version": "2.0",
        "procedure": text,
        "compilation_source": "fixture",
        "objects": [{"id": x, "label": x, "description": x} for x in ("battery", "controller")],
        "regions": [
            {
                "id": "case",
                "description": "Visible case opening",
                "grounding_prompt": "case opening",
            }
        ],
        "events": [
            {
                "id": x,
                "instruction": text,
                "source": source,
                "predicate": {
                    "type": "object_entered_region",
                    "object_id": obj,
                    "region_id": "case",
                },
            }
            for x, obj in (("e1", "battery"), ("e2", "controller"))
        ],
        "constraints": [
            {"id": "c1", "operator": "BEFORE", "first": "e1", "second": "e2", "source": source}
        ],
        "conditions": [],
    }


def obs(event="e1", obj="battery", start=1, end=2, **changes):
    data = {
        "occurrence_id": f"occ-{event}",
        "event_id": event,
        "predicate": {"type": "object_entered_region", "object_id": obj, "region_id": "case"},
        "polarity": "CONFIRMED",
        "confidence": 1.0,
        "start_s": start,
        "end_s": end,
        "evidence": {
            "id": f"proof-{event}",
            "start_s": start,
            "end_s": end,
            "description": "Declared synthetic predicate",
            "source": "fixture",
        },
    }
    data.update(changes)
    return Observation.model_validate(data)


@pytest.mark.parametrize(
    "a,b,status",
    [
        ((1, 2), (3, 4), "PASS"),
        ((3, 4), (1, 2), "FAIL"),
        ((1, 3), (2, 4), "UNKNOWN"),
        ((1, 2), (2, 3), "UNKNOWN"),
    ],
)
def test_predicate_ordering(a, b, status):
    graph = TaskGraph.model_validate(graph_data())
    result = evaluate(graph, [obs(start=a[0], end=a[1]), obs("e2", "controller", *b)], 6)
    assert result.verdict == status
    assert result.constraints[0].verdict == status
    assert all(
        set(c.evidence_ids) <= {e.id for e in result.evidence}
        for c in result.steps + result.constraints
    )


def test_id_and_confidence_alone_cannot_prove_predicate():
    graph = TaskGraph.model_validate(graph_data())
    assert (
        evaluate(graph, [obs(obj="controller"), obs("e2", "controller", 3, 4)], 6).verdict
        == "UNKNOWN"
    )
    assert evaluate(graph, [obs()], 6).verdict == "UNKNOWN"


def test_after_is_normalized_for_evaluation():
    data = graph_data()
    data["constraints"][0].update(operator="AFTER", first="e2", second="e1")
    assert (
        evaluate(TaskGraph.model_validate(data), [obs(), obs("e2", "controller", 3, 4)], 6).verdict
        == "PASS"
    )


@pytest.mark.parametrize(
    "mutate",
    [
        lambda g: g["events"][0]["predicate"].update(object_id="invented"),
        lambda g: g["events"][0]["predicate"].update(region_id="invented"),
        lambda g: g["events"][0]["predicate"].update(type="hidden_containment"),
        lambda g: g["events"].append(deepcopy(g["events"][0])),
        lambda g: g["constraints"][0].update(operator="DURING"),
        lambda g: g["constraints"][0].update(second="missing"),
        lambda g: g["constraints"].append({**g["constraints"][0], "id": "c2", "operator": "AFTER"}),
        lambda g: g["events"][0]["source"].update(quote="fabricated"),
    ],
)
def test_reject_invalid_semantic_graphs(mutate):
    data = graph_data()
    mutate(data)
    with pytest.raises(ValidationError):
        TaskGraph.model_validate(data)


def test_conflicting_and_repeated_observations_do_not_silently_pass():
    graph = TaskGraph.model_validate(graph_data())
    first = obs()
    other = obs("e2", "controller", 3, 4)
    repeated = obs(
        occurrence_id="another", evidence={**first.evidence.model_dump(), "id": "another-proof"}
    )
    contradictory = repeated.model_copy(update={"polarity": "CONTRADICTED"})
    assert evaluate(graph, [first, repeated, other], 6).verdict == "UNKNOWN"
    assert evaluate(graph, [first, contradictory, other], 6).verdict == "UNKNOWN"
    assert (
        evaluate(graph, [first.model_copy(update={"polarity": "CONTRADICTED"}), other], 6).verdict
        == "FAIL"
    )


def test_unsupported_required_condition_prevents_pass():
    data = graph_data()
    data["conditions"] = [
        {
            "id": "hidden",
            "instruction": "Battery is charged",
            "source": data["events"][0]["source"],
            "observability": "UNSUPPORTED",
            "reason": "Charge is not visible",
            "predicate": None,
            "scope": "during",
        }
    ]
    result = evaluate(TaskGraph.model_validate(data), [obs(), obs("e2", "controller", 3, 4)], 6)
    assert result.verdict == "UNKNOWN"
    assert result.conditions[0].verdict == "UNKNOWN"


def test_optional_absent_event_does_not_become_mandatory_via_edge():
    data = graph_data()
    data["events"][1]["required"] = False
    result = evaluate(TaskGraph.model_validate(data), [obs()], 6)
    assert result.verdict == "PASS"
    assert result.constraints[0].required is False


def test_present_but_repeated_optional_event_cannot_bypass_declared_order():
    data = graph_data()
    data["events"][0]["required"] = False
    # Optional e1 must precede required e2, but both observed e1 occurrences follow it.
    optional = obs(start=3, end=3.5)
    repeated = obs(
        start=4,
        end=4.5,
        occurrence_id="second-occ",
        evidence={
            "id": "second-proof",
            "start_s": 4,
            "end_s": 4.5,
            "description": "Repeated optional entry",
            "source": "fixture",
        },
    )
    result = evaluate(
        TaskGraph.model_validate(data), [optional, repeated, obs("e2", "controller", 1, 1.5)], 6
    )
    assert result.verdict == "UNKNOWN"
    assert result.constraints[0].required is True


def test_final_state_requires_evidence_at_end_of_video():
    data = graph_data()
    data["conditions"] = [
        {
            "id": "visible-final",
            "instruction": data["procedure"],
            "source": data["events"][0]["source"],
            "predicate": {"type": "object_visible", "object_id": "battery"},
            "scope": "final",
        }
    ]
    graph = TaskGraph.model_validate(data)
    final = obs(
        "visible-final",
        predicate={"type": "object_visible", "object_id": "battery"},
        start=4,
        end=5,
    )
    events = [obs(), obs("e2", "controller", 3, 4)]
    assert evaluate(graph, [*events, final], 6).verdict == "UNKNOWN"
    final.end_s = final.evidence.end_s = 6
    assert evaluate(graph, [*events, final], 6).verdict == "PASS"


def test_observable_final_state_change_requires_persistence_to_clip_end():
    data = graph_data()
    predicate = {
        "type": "visually_confirmed_state_change",
        "object_id": "battery",
        "state_dimension": "orientation",
        "from_state": "horizontal",
        "to_state": "vertical",
        "visual_criteria": "Long visible axis rotates upright",
    }
    data["conditions"] = [
        {
            "id": "upright",
            "instruction": data["procedure"],
            "source": data["events"][0]["source"],
            "predicate": predicate,
            "scope": "final",
        }
    ]
    graph = TaskGraph.model_validate(data)
    events = [obs(), obs("e2", "controller", 3, 4)]
    final = obs("upright", predicate=predicate, start=4, end=5)
    assert evaluate(graph, [*events, final], 6).verdict == "UNKNOWN"
    final.end_s = final.evidence.end_s = 6
    assert evaluate(graph, [*events, final], 6).verdict == "PASS"


@pytest.mark.parametrize(
    "changes",
    [
        {
            "predicate": {
                "type": "object_exited_region",
                "object_id": "battery",
                "region_id": "case",
            }
        },
        {"predicate": {"type": "object_visible", "object_id": "battery"}},
        {
            "predicate": {
                "type": "object_entered_region",
                "object_id": "battery",
                "region_id": "elsewhere",
            }
        },
        {"confidence": 0.79},
        {"end_s": 7},
        {
            "evidence": {
                "id": "proof",
                "start_s": 1.1,
                "end_s": 2,
                "description": "Does not cover event",
                "source": "fixture",
            }
        },
    ],
)
def test_no_other_predicate_or_invalid_evidence_can_prove_an_event(changes):
    result = evaluate(
        TaskGraph.model_validate(graph_data()), [obs(**changes), obs("e2", "controller", 3, 4)], 6
    )
    assert result.verdict == "UNKNOWN"


def test_ambiguous_region_cannot_be_overridden_by_confident_observation():
    data = graph_data()
    data["regions"][0].update(observability="AMBIGUOUS", reason="Region not visually grounded")
    assert (
        evaluate(TaskGraph.model_validate(data), [obs(), obs("e2", "controller", 3, 4)], 6).verdict
        == "UNKNOWN"
    )


def test_schema_rejects_unsupported_without_reason_and_optional_only_graph():
    data = graph_data()
    data["events"][0].update(observability="UNSUPPORTED")
    with pytest.raises(ValidationError):
        TaskGraph.model_validate(data)
    data = graph_data()
    for event in data["events"]:
        event["required"] = False
    with pytest.raises(ValidationError):
        TaskGraph.model_validate(data)
