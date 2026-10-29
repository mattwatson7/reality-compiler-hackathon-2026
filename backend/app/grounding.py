"""Deterministic grounding and a fail-closed, independently parsed semantic gate.

The model interprets source IDs; it never supplies offsets. Acceptance is bounded
by the existing controlled grammar, not a claim of general natural-language proof.
Unknown clauses cannot be promoted to observable semantics by model confidence.
"""

import copy
import json
from typing import Any, NoReturn

from pydantic import ValidationError

from backend.app.compiler import SemanticCompiler, _instructions
from backend.app.meta import MetaContractError
from backend.app.muse import strict_graph_schema
from backend.app.schemas import TaskGraph


def source_catalog(procedure: str) -> list[dict[str, Any]]:
    return [
        {"source_id": f"clause{index}", **span.model_dump()}
        for index, span in enumerate(_instructions(procedure), 1)
    ]


def grounded_schema(procedure: str | None = None) -> dict[str, Any]:
    schema = strict_graph_schema()
    schema["$defs"]["SourceSpan"] = {
        "type": "object",
        "properties": {"source_id": {"type": "string"}, "quote": {"type": "string"}},
        "required": ["source_id", "quote"],
        "additionalProperties": False,
    }
    if procedure is not None:
        declarations = SemanticCompiler().compile(procedure)
        # Constrain generation to independently known multiplicity and verbatim
        # source clauses. Semantic acceptance below remains unchanged.
        for section in ("events", "conditions", "constraints", "objects", "regions"):
            count = len(getattr(declarations, section))
            schema["properties"][section].update(minItems=count, maxItems=count)
        quotes = [s["quote"] for s in source_catalog(procedure)]
        for kind in ("Event", "Condition"):
            schema["$defs"][kind]["properties"]["instruction"]["enum"] = quotes
        catalog = source_catalog(procedure)
        for section, kind in (("events", "Event"), ("conditions", "Condition")):
            alternatives = []
            for requirement in getattr(declarations, section):
                item = copy.deepcopy(schema["$defs"][kind])
                properties = item["properties"]
                for field in ("id", "instruction", "required", "observability", "scope"):
                    if field in properties:
                        properties[field]["enum"] = [getattr(requirement, field)]
                if requirement.observability != "SUPPORTED":
                    properties["reason"] = {"type": "string", "minLength": 1, "maxLength": 2000}
                source = next(s for s in catalog if s["start"] == requirement.source.start)
                properties["source"] = copy.deepcopy(schema["$defs"]["SourceSpan"])
                properties["source"]["properties"]["source_id"]["enum"] = [source["source_id"]]
                properties["source"]["properties"]["quote"]["enum"] = [source["quote"]]
                predicate = requirement.predicate
                if predicate is not None and predicate.type == "visually_confirmed_state_change":
                    # Literal criteria are source text, not prose for the model
                    # to paraphrase. All predicate semantics are still checked.
                    state = copy.deepcopy(schema["$defs"]["StateChange"])
                    state["properties"]["visual_criteria"]["enum"] = [predicate.visual_criteria]
                    properties["predicate"] = {"anyOf": [state, {"type": "null"}]}
                alternatives.append(item)
            if alternatives:
                schema["properties"][section]["items"] = {"anyOf": alternatives}
    return schema


def _reject(path: str, code: str) -> NoReturn:
    # Both path and code are application-owned: never echo provider strings,
    # validation input, arbitrary model IDs, reasons, procedure text or secrets.
    raise MetaContractError(f"Muse graph rejected ({path}: {code})") from None


def _unique_fields(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _reject("task_graph_schema", "duplicate_json_field")
        result[key] = value
    return result


def resolve_graph(content: str, procedure: str) -> TaskGraph:
    try:
        data = json.loads(content, object_pairs_hook=_unique_fields)
    except (ValueError, TypeError):
        _reject("task_graph_schema", "invalid_json")
    if not isinstance(data, dict):
        _reject("task_graph_schema", "expected_object")
    catalog = {s["source_id"]: s for s in source_catalog(procedure)}
    for section in ("events", "conditions", "constraints"):
        items = data.get(section)
        if not isinstance(items, list):
            _reject(section, "expected_list")
        for index, item in enumerate(items):
            path = f"{section}[{index}].source"
            if not isinstance(item, dict):
                _reject(path, "source_reference_expected")
            reference = item.get("source")
            if not isinstance(reference, dict) or set(reference) != {"source_id", "quote"}:
                _reject(path, "source_reference_only_no_offsets")
            identifier = reference.get("source_id")
            if not isinstance(identifier, str) or identifier not in catalog:
                _reject(path, "source_reference_unknown")
            source = catalog[identifier]
            if reference["quote"] != source["quote"]:
                _reject(path, "source_reference_quote_mismatch")
            item["source"] = {k: source[k] for k in ("start", "end", "quote")}
    try:
        graph = TaskGraph.model_validate(data)
    except ValidationError as error:
        # Only schema-owned location names and numeric indices are safe to echo.
        fields = {
            "events",
            "conditions",
            "constraints",
            "objects",
            "regions",
            "source",
            "predicate",
            "type",
            "required",
            "observability",
            "scope",
            "id",
            "instruction",
            "object_id",
            "region_id",
            "first",
            "second",
            "operator",
            "reason",
        }
        location = ".".join(
            str(x) for x in error.errors()[0]["loc"] if type(x) is int or x in fields
        )
        _reject(
            "task_graph_schema" + ("." + location if location else ""),
            "invalid_typed_graph_or_references",
        )
    validate_semantics(graph, procedure)
    return graph


def validate_semantics(graph: TaskGraph, procedure: str) -> None:
    expected = SemanticCompiler().compile(procedure).model_dump(mode="json")
    actual = graph.model_dump(mode="json")
    if actual["procedure"] != procedure or actual["compilation_source"] != "muse":
        _reject("procedure", "source_or_provenance_mismatch")
    for section in ("objects", "regions", "events", "conditions", "constraints"):
        wanted, supplied = expected[section], actual[section]
        if len(wanted) != len(supplied):
            _reject(
                section,
                f"missing_or_fabricated_semantics; expected={len(wanted)} received={len(supplied)}",
            )
        for index, (left, right) in enumerate(zip(wanted, supplied, strict=True)):
            for field in left:
                # Free explanation is not authority. Observability and the full
                # typed predicate remain independently checked. Preserve reason
                # presence requirements through strict TaskGraph validation.
                if field == "reason":
                    continue
                if left[field] != right[field]:
                    source = left.get("source")
                    detail = "source_semantics_mismatch"
                    if source:
                        detail += f"; expected source [{source['start']}:{source['end']}]"
                    _reject(f"{section}[{index}].{field}", detail)
