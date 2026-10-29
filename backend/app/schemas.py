"""Versioned, provider-neutral semantic contracts, not vendor response fields."""

from typing import Annotated, Literal, Self

from pydantic import Field, StringConstraints, model_validator

from backend.app.legacy import Evidence as LegacyEvidence
from backend.app.legacy import (
    Identifier,
    Interval,
    Text,
)
from backend.app.legacy import (
    ObjectTrack as ObjectTrack,
)
from backend.app.legacy import (
    OrderingConstraint as OrderingConstraint,
)
from backend.app.legacy import (
    Step as Step,
)
from backend.app.legacy import (
    StrictModel as StrictModel,
)
from backend.app.legacy import (
    TrackSample as TrackSample,
)
from backend.app.legacy import (
    Verdict as Verdict,
)


class SourceSpan(StrictModel):
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    quote: Text


class Evidence(LegacyEvidence):
    source: Literal["fixture", "model", "local_cv", "meta_sam", "muse_spark"]  # type: ignore[assignment]
    model_id: str | None = None
    frame_indices: list[int] = Field(default_factory=list, max_length=721)
    frame_reference: str | None = None


class PhysicalObject(StrictModel):
    id: Identifier
    label: Text
    description: Text
    grounding_prompt: Text | None = None


class Observability(StrictModel):
    observability: Literal["SUPPORTED", "AMBIGUOUS", "UNSUPPORTED"] = "SUPPORTED"
    reason: Text | None = None

    @model_validator(mode="after")
    def reason_required(self) -> Self:
        if self.observability != "SUPPORTED" and self.reason is None:
            raise ValueError("Ambiguous/unsupported requirements need an explicit reason")
        return self


class Region(Observability):
    id: Identifier
    description: Text
    grounding_prompt: Text
    coordinate_semantics: Literal["visible_image_region"] = "visible_image_region"


class ObjectVisible(StrictModel):
    type: Literal["object_visible"]
    object_id: Identifier


class RegionTransition(StrictModel):
    type: Literal["object_entered_region", "object_exited_region"]
    object_id: Identifier
    region_id: Identifier


class StateChange(StrictModel):
    type: Literal["visually_confirmed_state_change"]
    object_id: Identifier
    state_dimension: Text
    from_state: Text
    to_state: Text
    visual_criteria: Text

    @model_validator(mode="after")
    def changed(self) -> Self:
        if self.from_state == self.to_state:
            raise ValueError("State change requires distinct visible states")
        return self


Predicate = Annotated[ObjectVisible | RegionTransition | StateChange, Field(discriminator="type")]


class Event(Observability):
    id: Identifier
    instruction: Text
    source: SourceSpan
    predicate: Predicate | None
    required: bool = True

    @model_validator(mode="after")
    def supported_has_predicate(self) -> Self:
        if self.observability == "SUPPORTED" and self.predicate is None:
            raise ValueError("Supported requirements need a typed predicate")
        return self


class Condition(Event):
    scope: Literal["during", "final"] = "during"

    @model_validator(mode="after")
    def final_is_state(self) -> Self:
        if self.scope == "final" and isinstance(self.predicate, RegionTransition):
            raise ValueError("A transient region crossing cannot establish a final state")
        return self


class TemporalConstraint(StrictModel):
    id: Identifier
    operator: Literal["BEFORE", "AFTER"]
    first: Identifier
    second: Identifier
    source: SourceSpan

    def ordered_pair(self) -> tuple[str, str]:
        return (self.first, self.second) if self.operator == "BEFORE" else (self.second, self.first)


class TaskGraph(StrictModel):
    version: Literal["2.0"]
    procedure: Annotated[str, StringConstraints(min_length=1, max_length=10000)]
    compilation_source: Literal["fixture", "local_rules", "muse", "legacy"]
    objects: list[PhysicalObject] = Field(max_length=30)
    regions: list[Region] = Field(default_factory=list, max_length=30)
    events: list[Event] = Field(default_factory=list, max_length=60)
    constraints: list[TemporalConstraint] = Field(default_factory=list, max_length=100)
    conditions: list[Condition] = Field(default_factory=list, max_length=60)

    @model_validator(mode="after")
    def semantic_graph(self) -> Self:
        ids = (
            [item.id for item in self.objects]
            + [item.id for item in self.regions]
            + [item.id for item in self.events]
            + [item.id for item in self.constraints]
            + [item.id for item in self.conditions]
        )
        if len(ids) != len(set(ids)):
            raise ValueError("IDs must be globally unique")
        requirements = [*self.events, *self.conditions]
        if not any(item.required for item in requirements):
            raise ValueError("At least one required requirement is necessary")
        objects = {obj.id for obj in self.objects}
        regions = {region.id for region in self.regions}
        for requirement in requirements:
            p = requirement.predicate
            if p is not None:
                if p.object_id not in objects:
                    raise ValueError("Predicate references an unknown object")
                if isinstance(p, RegionTransition) and p.region_id not in regions:
                    raise ValueError("Predicate references an unknown region")
        for span in [item.source for item in requirements] + [
            item.source for item in self.constraints
        ]:
            if (
                span.end > len(self.procedure)
                or span.end <= span.start
                or self.procedure[span.start : span.end] != span.quote
            ):
                raise ValueError("Source span must match the original procedure exactly")
        edges: dict[str, list[str]] = {event.id: [] for event in self.events}
        pairs: set[tuple[str, str]] = set()
        for constraint in self.constraints:
            before, after = constraint.ordered_pair()
            if before not in edges or after not in edges:
                raise ValueError("Constraint references an unknown event")
            if (before, after) in pairs:
                raise ValueError("Duplicate normalized temporal constraint")
            pairs.add((before, after))
            edges[before].append(after)
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(event_id: str) -> None:
            if event_id in visiting:
                raise ValueError("Temporal dependencies must be acyclic")
            if event_id in visited:
                return
            visiting.add(event_id)
            for child in edges[event_id]:
                visit(child)
            visiting.remove(event_id)
            visited.add(event_id)

        for event_id in edges:
            visit(event_id)
        return self


class Observation(Interval):
    occurrence_id: Identifier
    event_id: Identifier
    predicate: Predicate
    polarity: Literal["CONFIRMED", "CONTRADICTED"] = "CONFIRMED"
    confidence: float = Field(ge=0, le=1, allow_inf_nan=False)
    evidence: Evidence
    frame_indices: list[int] = Field(default_factory=list, max_length=721)
    quality_components: dict[str, float] = Field(default_factory=dict)
    provenance: str | None = None
    usable: bool = True
    model_id: str | None = None


class CheckResult(StrictModel):
    id: Identifier
    verdict: Verdict
    reason: str
    evidence_ids: list[Identifier]
    required: bool = True


class Evaluation(StrictModel):
    verdict: Verdict
    reason: str
    steps: list[CheckResult]
    constraints: list[CheckResult]
    conditions: list[CheckResult] = Field(default_factory=list)
    evidence: list[Evidence]

    @model_validator(mode="after")
    def evidence_integrity(self) -> Self:
        ids = [item.id for item in self.evidence]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate evidence IDs")
        checks = self.steps + self.constraints + self.conditions
        for check in checks:
            if not set(check.evidence_ids) <= set(ids):
                raise ValueError("Unknown evidence reference")
            if check.verdict != Verdict.UNKNOWN and not check.evidence_ids:
                raise ValueError("PASS/FAIL requires evidence")
        required = [item.verdict for item in checks if item.required]
        expected = (
            Verdict.FAIL
            if Verdict.FAIL in required
            else Verdict.UNKNOWN
            if not required or Verdict.UNKNOWN in required
            else Verdict.PASS
        )
        if self.verdict != expected:
            raise ValueError("Overall verdict disagrees with required checks")
        return self
