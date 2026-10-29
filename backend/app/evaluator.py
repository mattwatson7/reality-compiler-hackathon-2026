"""Deterministic exact-predicate evaluation. Absence never proves a failure."""

import math
from collections import Counter

from backend.app.schemas import (
    CheckResult,
    Condition,
    Evaluation,
    Event,
    Observation,
    RegionTransition,
    TaskGraph,
    Verdict,
)


def evaluate(graph: TaskGraph, observations: list[Observation], duration_s: float) -> Evaluation:
    if not math.isfinite(duration_s) or duration_s <= 0:
        raise ValueError("Video duration must be finite and positive")
    # Revalidate at a trust boundary, including objects mutated after construction.
    graph = TaskGraph.model_validate_json(graph.model_dump_json())
    evidence_counts = Counter(item.evidence.id for item in observations)
    occurrence_counts = Counter(item.occurrence_id for item in observations)
    usable: dict[str, Observation] = {}
    evidence = {}
    regions = {item.id: item for item in graph.regions}

    def valid(item: Observation) -> bool:
        values = (
            item.start_s,
            item.end_s,
            item.evidence.start_s,
            item.evidence.end_s,
            item.confidence,
        )
        return (
            item.usable
            and all(math.isfinite(value) for value in values)
            and 0 <= item.start_s <= item.end_s <= duration_s + 1e-6
            and 0 <= item.evidence.start_s <= item.start_s
            and item.end_s <= item.evidence.end_s <= duration_s + 1e-6
            and 0.8 <= item.confidence <= 1
            and evidence_counts[item.evidence.id] == 1
            and occurrence_counts[item.occurrence_id] == 1
        )

    def check(requirement: Event) -> CheckResult:
        result = CheckResult(
            id=requirement.id,
            verdict=Verdict.UNKNOWN,
            evidence_ids=[],
            required=requirement.required,
            reason="Missing, conflicting, repeated, low-confidence or invalid predicate evidence.",
        )
        if requirement.observability != "SUPPORTED":
            result.reason = requirement.reason or "Requirement is not supported."
            return result
        p = requirement.predicate
        if isinstance(p, RegionTransition) and regions[p.region_id].observability != "SUPPORTED":
            result.reason = regions[p.region_id].reason or "Region grounding is ambiguous."
            return result
        candidates = [item for item in observations if item.event_id == requirement.id]
        # Every candidate must agree; never choose an arbitrary occurrence or discard a conflict.
        if len(candidates) != 1:
            return result
        item = candidates[0]
        if not valid(item) or item.predicate != p:
            return result
        # A relabelled contradictory claim about the same predicate also makes it ambiguous.
        if any(
            other is not item
            and other.predicate == item.predicate
            and other.polarity != item.polarity
            and max(other.start_s, item.start_s) <= min(other.end_s, item.end_s)
            for other in observations
        ):
            result.reason = "Conflicting observations of the same predicate."
            return result
        if isinstance(requirement, Condition) and requirement.scope == "final":
            if not math.isclose(item.end_s, duration_s, rel_tol=0, abs_tol=1e-6):
                result.reason = "Final-state evidence does not reach the end of the video."
                return result
        evidence[item.evidence.id] = item.evidence
        result.evidence_ids = [item.evidence.id]
        if item.polarity == "CONTRADICTED":
            result.verdict = Verdict.FAIL
            result.reason = "Positive contradictory evidence for the exact predicate and arguments."
        else:
            result.verdict = Verdict.PASS
            result.reason = "Exact predicate and arguments confirmed by one unambiguous occurrence."
            usable[requirement.id] = item
        return result

    steps = [check(item) for item in graph.events]
    conditions = [check(item) for item in graph.conditions]
    events = {item.id: item for item in graph.events}
    observed_ids = {item.event_id for item in observations}
    checks = []
    for constraint in graph.constraints:
        before_id, after_id = constraint.ordered_pair()
        before, after = usable.get(before_id), usable.get(after_id)
        required = all(
            events[event_id].required or event_id in observed_ids
            for event_id in (before_id, after_id)
        )
        verdict, reason, ids = Verdict.UNKNOWN, "Required predicate evidence unavailable.", []
        if not required:
            reason = "Conditional order with an optional event; missing evidence is nonblocking."
        if before is not None and after is not None:
            ids = [before.evidence.id, after.evidence.id]
            if before.end_s < after.start_s:
                verdict, reason = (
                    Verdict.PASS,
                    "Required order proven by disjoint predicate intervals.",
                )
            elif after.end_s < before.start_s:
                verdict, reason = Verdict.FAIL, "Evidence proves the reverse of the required order."
                # When optional actions occur, their declared order is meaningful.
            else:
                reason = "Intervals overlap or touch; strict ordering is UNKNOWN."
        checks.append(
            CheckResult(
                id=constraint.id,
                verdict=verdict,
                reason=reason,
                evidence_ids=ids,
                required=required,
            )
        )
    required_verdicts = [item.verdict for item in steps + conditions + checks if item.required]
    overall = (
        Verdict.FAIL
        if Verdict.FAIL in required_verdicts
        else Verdict.UNKNOWN
        if Verdict.UNKNOWN in required_verdicts
        else Verdict.PASS
    )
    reasons = {
        Verdict.PASS: "All required predicates and temporal constraints are supported.",
        Verdict.FAIL: "Positive evidence contradicts at least one required requirement.",
        Verdict.UNKNOWN: (
            "Evidence is insufficient for the complete procedure; "
            "unsupported requirements cannot pass."
        ),
    }
    return Evaluation(
        verdict=overall,
        reason=reasons[overall],
        steps=steps,
        constraints=checks,
        conditions=conditions,
        evidence=list(evidence.values()),
    )
