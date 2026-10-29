"""Provider-neutral contracts. No fields here represent a vendor API response."""

from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Identifier = Annotated[str, StringConstraints(pattern=r"^[a-zA-Z][a-zA-Z0-9_-]{0,63}$")]
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
Seconds = Annotated[float, Field(ge=0, allow_inf_nan=False)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class PhysicalObject(StrictModel):
    id: Identifier
    label: Text


class Step(StrictModel):
    id: Identifier
    instruction: Text
    object_ids: list[Identifier] = Field(default_factory=list, max_length=30)


class OrderingConstraint(StrictModel):
    id: Identifier
    before: Identifier
    after: Identifier


class TaskGraph(StrictModel):
    version: Literal["1.0"] = "1.0"
    procedure: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10000)
    ]
    objects: list[PhysicalObject] = Field(max_length=30)
    steps: list[Step] = Field(min_length=1, max_length=30)
    constraints: list[OrderingConstraint] = Field(max_length=100)

    @model_validator(mode="after")
    def validate_graph(self) -> Self:
        for collection in (self.objects, self.steps, self.constraints):
            ids = [item.id for item in collection]
            if len(ids) != len(set(ids)):
                raise ValueError("IDs must be unique within each collection")
        objects = {item.id for item in self.objects}
        steps = {item.id for item in self.steps}
        for step in self.steps:
            if not set(step.object_ids) <= objects:
                raise ValueError("Step references an unknown object")
            if len(step.object_ids) != len(set(step.object_ids)):
                raise ValueError("Duplicate object reference")
        edges: dict[str, list[str]] = {step: [] for step in steps}
        pairs: set[tuple[str, str]] = set()
        for constraint in self.constraints:
            if constraint.before not in steps or constraint.after not in steps:
                raise ValueError("Constraint references an unknown step")
            pair = (constraint.before, constraint.after)
            if pair in pairs:
                raise ValueError("Duplicate ordering constraint")
            pairs.add(pair)
            edges[constraint.before].append(constraint.after)
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(step: str) -> None:
            if step in visiting:
                raise ValueError("Ordering constraints must form an acyclic graph")
            if step in visited:
                return
            visiting.add(step)
            for target in edges[step]:
                visit(target)
            visiting.remove(step)
            visited.add(step)

        for step_id in steps:
            visit(step_id)
        return self


class Interval(StrictModel):
    start_s: Seconds
    end_s: Seconds

    @model_validator(mode="after")
    def valid_interval(self) -> Self:
        if self.end_s < self.start_s:
            raise ValueError("Interval end precedes start")
        return self


class Evidence(Interval):
    id: Identifier
    description: Text
    source: Literal["fixture", "model"]


class Observation(Interval):
    step_id: Identifier
    confidence: float = Field(ge=0, le=1, allow_inf_nan=False)
    evidence: Evidence


class TrackSample(StrictModel):
    time_s: Seconds
    # Normalized x, y, width, height; useful for future overlays.
    box: tuple[float, float, float, float]

    @model_validator(mode="after")
    def valid_box(self) -> Self:
        x, y, w, h = self.box
        if not (
            0 <= x <= 1 and 0 <= y <= 1 and 0 < w <= 1 and 0 < h <= 1 and x + w <= 1 and y + h <= 1
        ):
            raise ValueError("Box must be within normalized frame bounds")
        return self


class ObjectTrack(StrictModel):
    object_id: Identifier
    source: Literal["fixture", "model"]
    samples: list[TrackSample]


class Verdict(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


class CheckResult(StrictModel):
    id: Identifier
    verdict: Verdict
    reason: str
    evidence_ids: list[Identifier]


class Evaluation(StrictModel):
    verdict: Verdict
    reason: str
    steps: list[CheckResult]
    constraints: list[CheckResult]
    evidence: list[Evidence]

    @model_validator(mode="after")
    def decisive_results_have_evidence(self) -> Self:
        ids = {item.id for item in self.evidence}
        checks = self.steps + self.constraints
        if any(not set(check.evidence_ids) <= ids for check in checks):
            raise ValueError("Unknown evidence reference")
        if any(check.verdict != Verdict.UNKNOWN and not check.evidence_ids for check in checks):
            raise ValueError("PASS/FAIL requires evidence")
        if self.verdict != Verdict.UNKNOWN and not self.evidence:
            raise ValueError("Decisive evaluation requires evidence")
        return self
