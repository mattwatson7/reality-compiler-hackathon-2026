"""Explicit legacy migration; arbitrary instruction text cannot become evidence."""

import hashlib
from typing import Any

from backend.app.config import ROOT
from backend.app.legacy import Observation as LegacyObservation
from backend.app.legacy import TaskGraph as LegacyTaskGraph
from backend.app.schemas import TaskGraph

PROCEDURE = (
    "1. Move the blue block onto the mat.\n2. Place the cup on the mat.\n3. Raise the green card."
)
LABELS = ["Move blue block onto mat", "Place cup on mat", "Raise green card"]


def legacy_demo_graph() -> LegacyTaskGraph:
    return LegacyTaskGraph.model_validate(
        {
            "procedure": PROCEDURE,
            "objects": [{"id": name, "label": name} for name in ("block", "cup", "card")],
            "steps": [
                {"id": f"s{i + 1}", "instruction": label, "object_ids": [name]}
                for i, (label, name) in enumerate(
                    zip(LABELS, ("block", "cup", "card"), strict=True)
                )
            ],
            "constraints": [
                {"id": "c1", "before": "s1", "after": "s2"},
                {"id": "c2", "before": "s2", "after": "s3"},
            ],
        }
    )


def migrate_legacy_graph(graph: LegacyTaskGraph) -> TaskGraph:
    # Source spans preserve the original text, even when old labels were paraphrased.
    quote = graph.procedure[:2000]
    source = {"start": 0, "end": len(quote), "quote": quote}
    return TaskGraph.model_validate(
        {
            "version": "2.0",
            "procedure": graph.procedure,
            "compilation_source": "legacy",
            "objects": [{**obj.model_dump(), "description": obj.label} for obj in graph.objects],
            "events": [
                {
                    "id": step.id,
                    "instruction": step.instruction,
                    "source": source,
                    "predicate": None,
                    "observability": "UNSUPPORTED",
                    "reason": "Legacy instruction has no reviewed observable predicate.",
                }
                for step in graph.steps
            ],
            "constraints": [
                {
                    "id": edge.id,
                    "operator": "BEFORE",
                    "first": edge.before,
                    "second": edge.after,
                    "source": source,
                }
                for edge in graph.constraints
            ],
        }
    )


def migrate_fixture(raw: dict[str, Any], video_sha256: str | None = None) -> dict[str, Any]:
    """Only the reviewed bundled animation has a semantic declaration mapping."""
    legacy = LegacyTaskGraph.model_validate(raw["graph"])
    if legacy != legacy_demo_graph() or raw["video"] not in {"correct.mp4", "incorrect.mp4"}:
        raise ValueError("Only the exact reviewed legacy fixture graph can be migrated")
    lines = PROCEDURE.splitlines()
    predicates: list[dict[str, str]] = [
        {"type": "object_entered_region", "object_id": "block", "region_id": "mat"},
        {"type": "object_entered_region", "object_id": "cup", "region_id": "mat"},
        {
            "type": "visually_confirmed_state_change",
            "object_id": "card",
            "state_dimension": "vertical_position",
            "from_state": "lowered",
            "to_state": "raised",
            "visual_criteria": (
                "Green card moves visibly from y=400 to y=160 in the synthetic frame."
            ),
        },
    ]
    events = []
    for i, line in enumerate(lines):
        start = PROCEDURE.index(line)
        events.append(
            {
                "id": f"s{i + 1}",
                "instruction": line,
                "source": {"start": start, "end": start + len(line), "quote": line},
                "predicate": predicates[i],
            }
        )
    graph = TaskGraph.model_validate(
        {
            "version": "2.0",
            "procedure": PROCEDURE,
            "compilation_source": "fixture",
            "objects": [
                {"id": name, "label": name, "description": f"Synthetic {name}"}
                for name in ("block", "cup", "card")
            ],
            "regions": [
                {
                    "id": "mat",
                    "description": "Visible mat rectangle, not containment",
                    "grounding_prompt": (
                        "Outlined MAT rectangle x=325..700, y=260..450 in 960x540 frame"
                    ),
                }
            ],
            "events": events,
            "constraints": [
                {
                    "id": edge.id,
                    "operator": "BEFORE",
                    "first": edge.before,
                    "second": edge.after,
                    "source": {"start": 0, "end": len(PROCEDURE), "quote": PROCEDURE},
                }
                for edge in legacy.constraints
            ],
        }
    )
    observations = []
    for item in raw["observations"]:
        old = LegacyObservation.model_validate(item)
        index = ["s1", "s2", "s3"].index(old.step_id)
        observations.append(
            {key: value for key, value in old.model_dump(mode="json").items() if key != "step_id"}
            | {
                "event_id": old.step_id,
                "occurrence_id": f"occ-{old.step_id}",
                "predicate": predicates[index],
                "polarity": "CONFIRMED",
            }
        )
    digest = (
        video_sha256 or hashlib.sha256((ROOT / "fixtures" / raw["video"]).read_bytes()).hexdigest()
    )
    return {
        **raw,
        "graph": graph.model_dump(mode="json"),
        "observations": observations,
        "video_sha256": digest,
    }
