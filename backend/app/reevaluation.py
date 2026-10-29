"""Pure, conservative semantic compatibility for immutable perception reuse.

IDs are local to each compilation. Definitions, predicate arguments and requirement
scope must match exactly. No observation is discarded for being uncertain or a
repeat. No region can be redefined through this interface.
"""

import hashlib
import json
from collections import Counter
from typing import Any

from backend.app.schemas import Condition, Event, Observation, TaskGraph


def evidence_fingerprint(job: dict[str, Any]) -> str:
    fields = (
        "graph",
        "duration_s",
        "frame_reference",
        "media_metadata",
        "initialization",
        "tracks",
        "observations",
        "provenance",
        "mode",
    )
    payload = {k: job.get(k) for k in fields}
    if "perception_artifacts" in job:
        payload["perception_artifacts"] = job["perception_artifacts"]
    if "execution_mode" in job:
        payload["execution_mode"] = job["execution_mode"]
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


def _definition(item: Any) -> str:
    return json.dumps(item.model_dump(exclude={"id"}), sort_keys=True)


def reuse_observations(
    original: TaskGraph, revised: TaskGraph, observations: list[Observation]
) -> tuple[list[Observation], list[str]]:
    original = TaskGraph.model_validate_json(original.model_dump_json())
    revised = TaskGraph.model_validate_json(revised.model_dump_json())
    reasons: list[str] = []

    def mapping(old: list[Any], new: list[Any], kind: str) -> dict[str, str]:
        result = {}
        for item in new:
            matches = [
                candidate.id for candidate in old if _definition(candidate) == _definition(item)
            ]
            if len(matches) != 1:
                reasons.append(
                    f"Changed or ambiguous {kind} definition: select objects/regions again."
                )
            else:
                result[item.id] = matches[0]
        if len(set(result.values())) != len(result):
            reasons.append(f"Multiple revised {kind}s refer to the same stored identity.")
        return result

    objects = mapping(original.objects, revised.objects, "object")
    regions = mapping(original.regions, revised.regions, "region")
    if reasons:
        return [], reasons

    def key(requirement: Event, remap: bool) -> str:
        predicate = requirement.predicate
        payload = predicate.model_dump() if predicate else None
        if payload is not None and remap:
            payload["object_id"] = objects[payload["object_id"]]
            if "region_id" in payload:
                payload["region_id"] = regions[payload["region_id"]]
        return json.dumps(
            {
                "predicate": payload,
                "scope": requirement.scope if isinstance(requirement, Condition) else "event",
                "observability": requirement.observability,
            },
            sort_keys=True,
        )

    old_requirements = [*original.events, *original.conditions]
    evidence_counts = Counter(item.evidence.id for item in observations)
    occurrence_counts = Counter(item.occurrence_id for item in observations)
    reused = []
    for requirement in [*revised.events, *revised.conditions]:
        if requirement.observability != "SUPPORTED":
            continue  # The evaluator preserves unsupported requirements as UNKNOWN.
        matches = [old for old in old_requirements if key(old, False) == key(requirement, True)]
        if len(matches) != 1:
            reasons.append("New or ambiguous predicate/scope requires additional perception.")
            continue
        previous = matches[0]
        for item in observations:
            # Include contradictory/repeated/malformed-argument claims bound to the
            # old requirement. Never silently turn them into a confirming candidate.
            if item.event_id != previous.id and item.predicate != previous.predicate:
                continue
            clone = item.model_copy(deep=True)
            # Removing an unrelated requirement cannot erase global source-ID
            # collisions that made the original evidence nondecisive.
            clone.usable = (
                clone.usable
                and evidence_counts[item.evidence.id] == 1
                and occurrence_counts[item.occurrence_id] == 1
            )
            clone.event_id = (
                requirement.id
                if item.event_id == previous.id
                else "reuse_context_" + hashlib.sha256(item.event_id.encode()).hexdigest()[:32]
            )
            predicate = clone.predicate.model_dump()
            inverse_objects = {value: name for name, value in objects.items()}
            inverse_regions = {value: name for name, value in regions.items()}
            if predicate["object_id"] not in inverse_objects:
                reasons.append("Observation object arguments do not match the stored grounding.")
                continue
            predicate["object_id"] = inverse_objects[predicate["object_id"]]
            if "region_id" in predicate:
                if predicate["region_id"] not in inverse_regions:
                    reasons.append("Observation region arguments do not match stored grounding.")
                    continue
                predicate["region_id"] = inverse_regions[predicate["region_id"]]
            clone = Observation.model_validate({**clone.model_dump(), "predicate": predicate})
            reused.append(clone)
    return ([], reasons) if reasons else (reused, [])
