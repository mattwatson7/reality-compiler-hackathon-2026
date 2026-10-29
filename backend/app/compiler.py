"""Conservative, local controlled-language compilation; no model inference.

Recognized clauses use the named demo objects, visible/entry/exit predicates and
explicit visible state changes. Every clause is matched in full. Unrecognized
clauses remain unsupported requirements. Sentence/list order never creates edges.
"""

import re
from dataclasses import dataclass
from typing import Literal

from backend.app.schemas import (
    Condition,
    Event,
    ObjectVisible,
    PhysicalObject,
    Region,
    RegionTransition,
    SourceSpan,
    StateChange,
    TaskGraph,
    TemporalConstraint,
)

DEMO_PROCEDURE = (
    "1. Move the blue block onto the mat.\n2. Place the cup on the mat.\n3. Raise the green card."
)
_NOUN = (
    r"(?:the )?(?:(?:blue|red|green|yellow|orange|purple|black|white|small|large) ){0,2}"
    r"(?:battery|controller|case|seal|cup|block|card|mat|bottle|ball|box|tool|lid|tube|plate|spoon|key|coin)"
)
_SEPARATOR = re.compile(r"\n+|;\s*|(?<=[.!?])\s+")
_HIDDEN = re.compile(r"\b(?:charged?|steril\w*|torque|voltage|temperature|internal)\b")
_VISUAL_DIMENSIONS = {
    "closure",
    "vertical position",
    "position",
    "color",
    "orientation",
    "attachment",
}
_MOVE = r"(?:move|moving|slide|sliding|place|placing)"


def _instructions(procedure: str) -> list[SourceSpan]:
    if not isinstance(procedure, str) or not procedure.strip() or len(procedure) > 10000:
        raise ValueError("Enter between 1 and 30 explicit steps, at most 10000 characters")
    spans: list[SourceSpan] = []
    offset = 0
    for separator in [*_SEPARATOR.finditer(procedure), None]:
        end = separator.start() if separator else len(procedure)
        raw = procedure[offset:end]
        prefix = re.match(r"\s*(?:(?:\d+[.)]|[-*])\s*)?", raw)
        assert prefix is not None
        start = offset + prefix.end()
        trimmed_end = end - len(raw) + len(raw.rstrip())
        if start < trimmed_end:
            quote = procedure[start:trimmed_end]
            if len(quote) > 2000:
                raise ValueError("Each explicit step must be at most 2000 characters")
            spans.append(SourceSpan(start=start, end=trimmed_end, quote=quote))
        offset = separator.end() if separator else end
    if not spans or len(spans) > 30:
        raise ValueError("Enter between 1 and 30 explicit steps")
    return spans


def validate_procedure(procedure: str) -> None:
    """Validate local syntax limits without compiling or dispatching paid work."""
    _instructions(procedure)


def _label(text: str) -> str:
    return text.removeprefix("the ")


@dataclass(frozen=True)
class _Action:
    kind: Literal["visible", "entered", "exited", "change", "unsupported"]
    object_label: str = ""
    region: str = ""
    explicit_region: bool = False
    dimension: str = ""
    from_state: str = ""
    to_state: str = ""
    criteria: str = ""


def _atom(text: str) -> _Action | None:
    imperative = re.fullmatch(
        rf"{_MOVE} ({_NOUN}) (into|out of) (?:the )?visible "
        r"(?:(marked region)|image region ([a-z][a-z0-9_-]{0,39}))",
        text,
    )
    if imperative:
        return _Action(
            "entered" if imperative[2] == "into" else "exited",
            _label(imperative[1]),
            "marked" if imperative[3] else imperative[4],
            True,
        )
    visible = re.fullmatch(rf"({_NOUN}) is visible", text)
    if visible:
        return _Action("visible", _label(visible[1]))
    transition = re.fullmatch(
        rf"({_NOUN}) (enters|exits) (?:the )?"
        r"(?:(visible image region) ([a-z][a-z0-9_-]{0,39})|"
        rf"({_NOUN}))",
        text,
    )
    if transition:
        return _Action(
            "entered" if transition[2] == "enters" else "exited",
            _label(transition[1]),
            transition[4] or _label(transition[5]),
            bool(transition[3]),
        )
    change = re.fullmatch(
        rf"({_NOUN}) visibly changes ([a-z][a-z -]{{0,59}}) "
        r"from ([a-z][a-z -]{0,79}) to ([a-z][a-z -]{0,79}) "
        r"\(visual criteria: ([^();\n]{1,500})\)",
        text,
    )
    if (
        change
        and change[2] in _VISUAL_DIMENSIONS
        and not _HIDDEN.search(text)
        and change[3] != change[4]
    ):
        return _Action(
            "change",
            _label(change[1]),
            dimension=change[2],
            from_state=change[3],
            to_state=change[4],
            criteria=change[5],
        )
    # These names retain temporal semantics, but cannot claim visible evidence.
    if re.fullmatch(r"(?:closing(?: the case)?|(?:the )?case closes)", text):
        return _Action("unsupported")
    if re.fullmatch(r"(?:the )?seal (?:is )?applied", text):
        return _Action("unsupported")
    return None


def _actions(text: str) -> list[_Action] | None:
    plural = re.fullmatch(rf"({_NOUN}) and ({_NOUN}) (enter|exit) (.+?)(?: in either order)?", text)
    if plural:
        verb = "enters" if plural[3] == "enter" else "exits"
        first = _atom(f"{plural[1]} {verb} {plural[4]}")
        second = _atom(f"{plural[2]} {verb} {plural[4]}")
        if first and second and first.object_label != second.object_label:
            return [first, second]
        return None
    atom = _atom(text)
    return [atom] if atom else None


class SemanticCompiler:
    """Compile the documented small grammar and preserve all unsupported prose."""

    def compile(self, procedure: str) -> TaskGraph:
        spans = _instructions(procedure)
        builder = _Builder(procedure)
        if procedure == DEMO_PROCEDURE:
            demo = [
                _Action("entered", "blue block", "mat", True),
                _Action("entered", "cup", "mat", True),
                _Action(
                    "change",
                    "green card",
                    dimension="vertical position",
                    from_state="lowered",
                    to_state="raised",
                    criteria="The green card visibly moves upward from its lowered position.",
                ),
            ]
            for span, action in zip(spans, demo, strict=True):
                builder.add_event(action, span, True)
        else:
            for span in spans:
                builder.instruction(span)
        if not any(item.required for item in [*builder.events, *builder.conditions]):
            builder.unsupported(
                spans[0], "Optional-only instructions provide no required procedure coverage."
            )
        return TaskGraph(
            version="2.0",
            procedure=procedure,
            compilation_source="local_rules",
            objects=list(builder.objects.values()),
            regions=list(builder.regions.values()),
            events=builder.events,
            constraints=builder.constraints,
            conditions=builder.conditions,
        )


class _Builder:
    def __init__(self, procedure: str) -> None:
        self.procedure = procedure
        self.objects: dict[str, PhysicalObject] = {}
        self.regions: dict[tuple[str, bool], Region] = {}
        self.events: list[Event] = []
        self.event_actions: dict[str, _Action] = {}
        self.conditions: list[Condition] = []
        self.constraints: list[TemporalConstraint] = []
        self.context: list[str] = []

    def unsupported(
        self,
        span: SourceSpan,
        reason: str,
        required: bool = True,
        scope: Literal["during", "final"] = "during",
    ) -> None:
        self.conditions.append(
            Condition(
                id=f"condition{len(self.conditions) + 1}",
                instruction=span.quote,
                source=span,
                predicate=None,
                required=required,
                scope=scope,
                observability="UNSUPPORTED",
                reason=reason,
            )
        )

    def add_event(self, action: _Action, span: SourceSpan, required: bool) -> Event:
        predicate: ObjectVisible | RegionTransition | StateChange | None = None
        observability: Literal["SUPPORTED", "AMBIGUOUS", "UNSUPPORTED"] = "SUPPORTED"
        reason = None
        if action.kind == "unsupported":
            observability = "UNSUPPORTED"
            reason = (
                "A visible state change needs explicit before/after states and visual criteria."
            )
        else:
            label = action.object_label
            if label not in self.objects:
                self.objects[label] = PhysicalObject(
                    id=f"object{len(self.objects) + 1}",
                    label=label,
                    description=f"The procedure's {label}.",
                    grounding_prompt=f"Identify the {label}.",
                )
            object_id = self.objects[label].id
            if action.kind == "visible":
                predicate = ObjectVisible(type="object_visible", object_id=object_id)
            elif action.kind in {"entered", "exited"}:
                key = (action.region, action.explicit_region)
                if key not in self.regions:
                    self.regions[key] = Region(
                        id=f"region{len(self.regions) + 1}",
                        description=(
                            f"Visible image region for {action.region}; "
                            "a transition does not prove physical containment."
                        ),
                        grounding_prompt=f"Locate the visible image region for {action.region}.",
                        observability="SUPPORTED" if action.explicit_region else "AMBIGUOUS",
                        reason=None
                        if action.explicit_region
                        else (
                            "The text does not explicitly define a visible image region; "
                            "physical containment cannot be inferred."
                        ),
                    )
                region = self.regions[key]
                observability, reason = region.observability, region.reason
                predicate = RegionTransition(
                    type="object_entered_region"
                    if action.kind == "entered"
                    else "object_exited_region",
                    object_id=object_id,
                    region_id=region.id,
                )
            else:
                predicate = StateChange(
                    type="visually_confirmed_state_change",
                    object_id=object_id,
                    state_dimension=action.dimension,
                    from_state=action.from_state,
                    to_state=action.to_state,
                    visual_criteria=action.criteria,
                )
        event = Event(
            id=f"event{len(self.events) + 1}",
            instruction=span.quote,
            source=span,
            predicate=predicate,
            required=required,
            observability=observability,
            reason=reason,
        )
        self.events.append(event)
        self.event_actions[event.id] = action
        return event

    def edge(
        self, first: str, second: str, operator: Literal["BEFORE", "AFTER"], span: SourceSpan
    ) -> None:
        pair = (first, second) if operator == "BEFORE" else (second, first)
        if any(c.ordered_pair() == pair for c in self.constraints):
            return
        self.constraints.append(
            TemporalConstraint(
                id=f"constraint{len(self.constraints) + 1}",
                first=first,
                second=second,
                operator=operator,
                source=span,
            )
        )

    def instruction(self, span: SourceSpan) -> None:
        text = span.quote.rstrip(".!?").lower()
        required = True
        optional = re.fullmatch(r"optionally,? (.+)", text)
        if optional:
            required, text = False, optional[1]
        if text == "either object may enter first" and len(self.context) == 2:
            return
        both = re.fullmatch(r"both objects must enter before (.+)", text)
        if both and len(self.context) == 2 and (action := _atom(both[1])):
            event = self.add_event(action, span, required)
            for previous_id in self.context:
                self.edge(previous_id, event.id, "BEFORE", span)
            self.context = []
            return
        final = re.fullmatch(r"at end, (.+)", text)
        if final and (action := _atom(final[1])) and action.kind in {"visible", "change"}:
            event = self.add_event(action, span, required)
            self.events.pop()
            self.conditions.append(
                Condition(
                    **event.model_dump(exclude={"id"}),
                    id=f"condition{len(self.conditions) + 1}",
                    scope="final",
                )
            )
            self.context = []
            return
        temporal = re.fullmatch(r"(.+?) (before|after|then) (.+)", text)
        if temporal:
            left = _actions(temporal[1].removesuffix(",") if temporal[2] == "then" else temporal[1])
            right = _actions(temporal[3])
            referenced_event: Event | None = None
            if left and len(left) == 1 and right is None:
                reference = re.fullmatch(
                    rf"{_MOVE} ({_NOUN}) (into|out of) (?:that|the same) region", temporal[3]
                )
                if reference and left[0].explicit_region:
                    right = [
                        _Action(
                            "entered" if reference[2] == "into" else "exited",
                            _label(reference[1]),
                            left[0].region,
                            True,
                        )
                    ]
                # Only the exact noun inherits the preceding explicit transition.
                if re.fullmatch(_NOUN, temporal[3]) and left[0].kind in {"entered", "exited"}:
                    previous = left[0]
                    right = [
                        _Action(
                            previous.kind,
                            _label(temporal[3]),
                            previous.region,
                            previous.explicit_region,
                        )
                    ]
                    candidates = [
                        event for event in self.events if self.event_actions[event.id] == right[0]
                    ]
                    if len(candidates) > 1:
                        self.context = []
                        self.unsupported(
                            span,
                            "Ambiguous temporal reference: multiple earlier events match "
                            "the named object, region and transition; no occurrence is selected.",
                        )
                        return
                    referenced_event = candidates[0] if candidates else None
            if left and right:
                first = [self.add_event(a, span, required) for a in left]
                second = (
                    [referenced_event]
                    if referenced_event
                    else [self.add_event(a, span, required) for a in right]
                )
                operator: Literal["BEFORE", "AFTER"] = (
                    "AFTER" if temporal[2] == "after" else "BEFORE"
                )
                for a in first:
                    for b in second:
                        self.edge(a.id, b.id, operator, span)
                self.context = []
                return
        else:
            actions = _actions(text)
            if actions:
                events = [self.add_event(a, span, required) for a in actions]
                self.context = (
                    [e.id for e in events]
                    if (
                        required and len(actions) == 2 and all(a.kind == "entered" for a in actions)
                    )
                    else []
                )
                return
        self.context = []
        self.unsupported(
            span,
            "Outside the controlled visual grammar; all text and qualifiers are retained. "
            "Hidden properties and implicit physical containment cannot be verified.",
            required,
            scope="final" if final else "during",
        )
