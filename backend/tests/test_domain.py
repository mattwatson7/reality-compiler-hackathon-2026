from copy import deepcopy

import pytest
from pydantic import ValidationError

from backend.app.evaluator import evaluate
from backend.app.legacy import TaskGraph as LegacyTaskGraph
from backend.app.schemas import Evidence, Observation, TaskGraph


def graph_data():
    return {
        "version": "1.0",
        "procedure": "Pick up the block. Place the block.",
        "steps": [
            {"id": "s1", "instruction": "Pick up the block", "object_ids": ["block"]},
            {"id": "s2", "instruction": "Place the block", "object_ids": ["block"]},
        ],
        "objects": [{"id": "block", "label": "block"}],
        "constraints": [{"id": "c1", "before": "s1", "after": "s2"}],
    }


def observation(step, start, end, confidence=1.0):
    return Observation(
        event_id=step,
        occurrence_id=f"occ-{step}",
        predicate={"type": "object_visible", "object_id": "block"},
        start_s=start,
        end_s=end,
        confidence=confidence,
        evidence=Evidence(
            id=f"e-{step}",
            start_s=start,
            end_s=end,
            description=f"Synthetic {step}",
            source="fixture",
        ),
    )


def semantic_graph(data=None):
    old = graph_data() if data is None else data
    source = {"start": 0, "end": len(old["procedure"]), "quote": old["procedure"]}
    return TaskGraph.model_validate(
        {
            "version": "2.0",
            "procedure": old["procedure"],
            "compilation_source": "fixture",
            "objects": [
                {"id": "block", "label": "block", "description": "Visible synthetic block"}
            ],
            "events": [
                {
                    "id": step["id"],
                    "instruction": step["instruction"],
                    "source": source,
                    "predicate": {"type": "object_visible", "object_id": "block"},
                }
                for step in old["steps"]
            ],
            "constraints": [
                {
                    "id": c["id"],
                    "operator": "BEFORE",
                    "first": c["before"],
                    "second": c["after"],
                    "source": source,
                }
                for c in old["constraints"]
            ],
        }
    )


@pytest.mark.parametrize(
    "first,second,status",
    [
        ((1, 2), (3, 4), "PASS"),
        ((3, 4), (1, 2), "FAIL"),
        ((1, 3), (2, 4), "UNKNOWN"),
        ((1, 2), (2, 3), "UNKNOWN"),
    ],
)
def test_interval_ordering(first, second, status):
    result = evaluate(
        semantic_graph(),
        [
            observation("s1", *first),
            observation("s2", *second),
        ],
        duration_s=6,
    )
    assert result.verdict == status
    assert result.constraints[0].verdict == status
    if status != "UNKNOWN":
        assert len(result.constraints[0].evidence_ids) == 2
        assert result.evidence


@pytest.mark.parametrize(
    "observations",
    [
        [],
        [observation("s1", 1, 2)],
        [observation("s1", 1, 2, 0.3), observation("s2", 3, 4)],
        [observation("s1", 1, 2), observation("s1", 2, 3), observation("s2", 4, 5)],
        [observation("s1", 1, 2), observation("s2", 6, 7)],
    ],
)
def test_insufficient_evidence_is_unknown(observations):
    result = evaluate(semantic_graph(), observations, duration_s=6)
    assert result.verdict == "UNKNOWN"


def test_unobserved_unconstrained_step_prevents_pass():
    data = graph_data()
    data["constraints"] = []
    assert evaluate(semantic_graph(data), [], duration_s=6).verdict == "UNKNOWN"


@pytest.mark.parametrize(
    "mutate",
    [
        lambda g: g.update(extra=True),
        lambda g: g["steps"].append(deepcopy(g["steps"][0])),
        lambda g: g["constraints"][0].update(after="missing"),
        lambda g: g["constraints"][0].update(after="s1"),
        lambda g: g["constraints"].append({"id": "c2", "before": "s2", "after": "s1"}),
        lambda g: g["steps"][0].update(object_ids=["missing"]),
        lambda g: g.update(steps=[]),
        lambda g: g.update(version="2.0"),
    ],
)
def test_graph_rejects_invalid_structure(mutate):
    data = graph_data()
    mutate(data)
    with pytest.raises(ValidationError):
        LegacyTaskGraph.model_validate(data)


def test_observation_rejects_reversed_or_negative_times():
    with pytest.raises(ValidationError):
        observation("s1", 3, 2)
    with pytest.raises(ValidationError):
        observation("s1", -1, 2)
