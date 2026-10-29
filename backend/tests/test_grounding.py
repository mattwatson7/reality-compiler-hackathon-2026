import copy
import json

import pytest

from backend.app.compiler import SemanticCompiler
from backend.app.meta import MetaContractError
from backend.app.meta_semantics import LiveMuseWonderCompiler
from backend.tests.test_meta_semantics import Transport, envelope
from backend.tests.test_milestone3_contract import PROCEDURE


def wire(text=PROCEDURE):
    from backend.app.grounding import source_catalog

    graph = SemanticCompiler().compile(text).model_dump(mode="json")
    graph["compilation_source"] = "muse"
    catalog = source_catalog(text)
    for item in [*graph["events"], *graph["conditions"], *graph["constraints"]]:
        span = item["source"]
        source = next(c for c in catalog if c["start"] == span["start"] and c["end"] == span["end"])
        item["source"] = {"source_id": source["source_id"], "quote": source["quote"]}
    return graph


def compile_wire(data, text=PROCEDURE):
    return LiveMuseWonderCompiler(Transport(envelope(json.dumps(data)))).compile(text)


def test_source_ids_are_stable_exact_unicode_positions():
    from backend.app.grounding import source_catalog

    text = "  1. The cup is visible.\n2. The cup is visible.\n3. 🔵 unknown."
    sources = source_catalog(text)
    assert sources == source_catalog(text)
    assert len({s["source_id"] for s in sources}) == 3
    for s in sources:
        assert text[s["start"] : s["end"]] == s["quote"]


def test_grounded_output_resolves_without_model_offsets():
    result = compile_wire(wire())
    assert len(result.events) == 2
    assert not result.conditions
    assert result.events[0].source.quote == PROCEDURE


@pytest.mark.parametrize(
    "mutation,diagnostic",
    [
        ("offset", "source_reference"),
        ("unknown", "source_reference"),
        ("quote", "source_reference"),
        ("missing", "source_reference"),
        ("duplicate", "events"),
        ("observability", "observability"),
        ("predicate", "predicate"),
        ("edge", "constraints"),
        ("persistence", "conditions"),
        ("optional", "required"),
        ("object", "objects"),
    ],
)
def test_adversarial_semantics_are_rejected(mutation, diagnostic):
    data = wire()
    if mutation == "offset":
        data["events"][0]["source"]["start"] = 1
    elif mutation == "unknown":
        data["events"][0]["source"]["source_id"] = "invented"
    elif mutation == "quote":
        data["events"][0]["source"]["quote"] = "Move the cup."
    elif mutation == "missing":
        del data["events"][0]["source"]
    elif mutation == "duplicate":
        extra = copy.deepcopy(data["events"][0])
        extra["id"] = "event3"
        data["events"].append(extra)
    elif mutation == "observability":
        data["events"][0].update(observability="UNSUPPORTED", reason="No video")
    elif mutation == "predicate":
        data["events"][0]["predicate"]["object_id"] = "object2"
    elif mutation == "edge":
        data["constraints"] = []
    elif mutation == "persistence":
        extra = copy.deepcopy(data["events"][0])
        extra.update(id="condition1", scope="during")
        data["conditions"].append(extra)
    elif mutation == "optional":
        data["events"][0]["required"] = False
    elif mutation == "object":
        data["objects"][0]["label"] = "red block"
    with pytest.raises(MetaContractError, match=diagnostic):
        compile_wire(data)


@pytest.mark.parametrize(
    "text",
    [
        "Move it into that region.",
        "The battery is charged.",
        "The cup enters visible image region mat without spilling.",
        "Optionally, the cup is visible. The block is visible.",
        "The cup is visible. The cup is visible.",
    ],
)
def test_qualifiers_ambiguity_hidden_and_repeated_clauses_are_preserved(text):
    result = compile_wire(wire(text), text)
    expected = SemanticCompiler().compile(text)
    assert result.model_dump(exclude={"compilation_source"}) == expected.model_dump(
        exclude={"compilation_source"}
    )
    data = wire(text)
    if data["conditions"]:
        condition = data["conditions"][0]
        condition.update(
            observability="SUPPORTED",
            reason=None,
            predicate={"type": "object_visible", "object_id": "fabricated"},
        )
        with pytest.raises(MetaContractError):
            compile_wire(data, text)


def test_correct_quote_wrong_occurrence_is_rejected():
    text = "The cup is visible. The cup is visible."
    data = wire(text)
    data["events"][0]["source"] = data["events"][1]["source"]
    with pytest.raises(MetaContractError, match="source"):
        compile_wire(data, text)


def test_actual_failure_correcting_spans_alone_still_fails_semantic_gate():
    from backend.app.config import ROOT
    from backend.app.grounding import validate_semantics
    from backend.app.schemas import TaskGraph

    raw = json.loads((ROOT / "docs/meta-smoke-wonder-response.json").read_text())
    data = json.loads(raw["choices"][0]["message"]["content"])
    for item in [*data["events"], *data["constraints"]]:
        quote = item["source"]["quote"]
        start = PROCEDURE.index(quote)
        item["source"] = {"start": start, "end": start + len(quote), "quote": quote}
    # A span-only fix admits the recorded invented event to TaskGraph. The
    # independent semantic boundary must still reject it; never repair live data.
    graph = TaskGraph.model_validate(data)
    with pytest.raises(MetaContractError):
        validate_semantics(graph, PROCEDURE)


@pytest.mark.parametrize(
    "text",
    [
        "The cup is visible. The block is visible.",
        "The cup enters visible image region mat before the block enters visible image region mat.",
        "The cup enters visible image region mat after the block enters visible image region mat.",
    ],
)
def test_invalid_temporal_constraints_are_rejected_even_when_acyclic(text):
    data = wire(text)
    if data["constraints"]:
        data["constraints"][0]["operator"] = (
            "BEFORE" if data["constraints"][0]["operator"] == "AFTER" else "AFTER"
        )
    else:
        data["constraints"] = [
            {
                "id": "constraint1",
                "operator": "BEFORE",
                "first": "event1",
                "second": "event2",
                "source": copy.deepcopy(data["events"][0]["source"]),
            }
        ]
    with pytest.raises(MetaContractError, match="constraints"):
        compile_wire(data, text)


def test_unknown_qualifier_cannot_be_removed_to_obtain_supported_event():
    text = "The cup enters visible image region mat without spilling."
    data = wire(text)
    supported = wire("The cup enters visible image region mat.")
    data.update(
        objects=supported["objects"],
        regions=supported["regions"],
        events=supported["events"],
        conditions=[],
    )
    data["events"][0]["source"] = wire(text)["conditions"][0]["source"]
    data["events"][0]["instruction"] = text
    with pytest.raises(MetaContractError):
        compile_wire(data, text)


def test_diagnostics_never_echo_model_secret_or_injected_source_id():
    data = wire()
    data["events"][0]["source"]["source_id"] = "secret-provider-string"
    with pytest.raises(MetaContractError) as error:
        compile_wire(data)
    assert "events[0].source" in str(error.value)
    assert "secret-provider-string" not in str(error.value)


def test_duplicate_json_fields_are_contradictory_and_rejected():
    from backend.app.grounding import resolve_graph

    data = json.dumps(wire())
    data = data.replace('"required": true', '"required": false, "required": true', 1)
    with pytest.raises(MetaContractError, match="duplicate_json_field"):
        resolve_graph(data, PROCEDURE)
