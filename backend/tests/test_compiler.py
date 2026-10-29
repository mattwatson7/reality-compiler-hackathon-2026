import pytest

from backend.app.compiler import SemanticCompiler, validate_procedure
from backend.app.schemas import RegionTransition, StateChange


def compile_text(text):
    graph = SemanticCompiler().compile(text)
    for item in [*graph.events, *graph.conditions, *graph.constraints]:
        assert text[item.source.start : item.source.end] == item.source.quote
    return graph


def test_before_retains_elliptical_controller_and_ambiguous_containment():
    graph = compile_text("Battery enters case before controller.")
    assert len(graph.events) == 2
    assert all(isinstance(e.predicate, RegionTransition) for e in graph.events)
    assert len(graph.constraints) == 1
    assert graph.constraints[0].operator == "BEFORE"
    assert all(r.observability == "AMBIGUOUS" for r in graph.regions)


def test_after_preserves_operator_and_unsupported_seal_and_closing():
    graph = compile_text("Seal applied after closing.")
    assert len(graph.events) == 2
    assert graph.constraints[0].operator == "AFTER"
    assert all(e.observability == "UNSUPPORTED" for e in graph.events)


def test_cross_clause_elliptical_reference_reuses_unique_event():
    graph = compile_text(
        "Battery enters the visible image region case.\n"
        "Controller enters the visible image region case after battery."
    )
    assert len(graph.events) == 2
    assert graph.constraints[0].second == graph.events[0].id
    assert graph.constraints[0].first == graph.events[1].id
    assert not graph.conditions


def test_elliptical_reference_with_multiple_prior_matches_is_unsupported():
    graph = compile_text(
        "Battery enters the visible image region case.\n"
        "Battery enters the visible image region case.\n"
        "Controller enters the visible image region case after battery."
    )
    assert len(graph.events) == 2
    assert not graph.constraints
    assert graph.conditions[0].required
    assert graph.conditions[0].observability == "UNSUPPORTED"
    assert "ambiguous" in graph.conditions[0].reason.lower()


def test_optional_elliptical_reference_does_not_duplicate_required_event():
    graph = compile_text(
        "Battery enters the visible image region case.\n"
        "Optionally, controller enters the visible image region case after battery."
    )
    assert len(graph.events) == 2
    assert graph.events[0].required
    assert not graph.events[1].required
    assert graph.constraints[0].second == graph.events[0].id


def test_full_repeated_action_remains_a_separate_occurrence():
    graph = compile_text(
        "Battery enters the visible image region case.\n"
        "Controller enters the visible image region case after "
        "battery enters the visible image region case."
    )
    assert len(graph.events) == 3
    assert graph.constraints[0].second == graph.events[2].id


def test_elliptical_reference_does_not_reuse_wrong_region_or_direction():
    graph = compile_text(
        "Battery exits the visible image region case.\n"
        "Battery enters the visible image region mat.\n"
        "Controller enters the visible image region case after battery."
    )
    assert len(graph.events) == 4
    assert graph.constraints[0].second == graph.events[3].id


def test_both_before_closing_has_two_edges_no_between_objects():
    graph = compile_text("Battery and controller enter case before closing.")
    assert len(graph.events) == 3
    assert len(graph.constraints) == 2
    assert {c.second for c in graph.constraints} == {graph.events[2].id}


def test_either_order_explicit_compound_has_no_edges():
    graph = compile_text("Battery and controller enter case in either order.")
    assert len(graph.events) == 2
    assert not graph.constraints


def test_contextual_both_and_either_preserve_no_invented_pair_order():
    graph = compile_text(
        "Battery and controller enter case. Either object may enter first. "
        "Both objects must enter before closing."
    )
    assert len(graph.events) == 3
    assert len(graph.constraints) == 2
    assert not graph.conditions


def test_unordered_instructions_do_not_acquire_edges():
    graph = compile_text("1. Battery is visible.\n2. Controller is visible.")
    assert len(graph.events) == 2
    assert not graph.constraints


def test_optional_only_cannot_vacuously_pass():
    graph = compile_text("Optionally, battery is visible.")
    assert not graph.events[0].required
    assert graph.conditions[0].required
    assert graph.conditions[0].observability == "UNSUPPORTED"


@pytest.mark.parametrize("text", ["Battery is charged.", "Case is sterile."])
def test_hidden_conditions_remain_unsupported(text):
    graph = compile_text(text)
    assert graph.conditions[0].predicate is None
    assert graph.conditions[0].observability == "UNSUPPORTED"


@pytest.mark.parametrize(
    "text",
    [
        "Battery is visible unless damaged.",
        "Battery enters case without touching controller.",
        "Battery is visible and charged.",
        "Battery enters case before controller, if charged.",
        "Either object may enter first.",
        "Battery is not visible.",
        "Battery enters case twice.",
    ],
)
def test_partial_grammar_cannot_discard_qualifiers(text):
    graph = compile_text(text)
    assert any(c.observability == "UNSUPPORTED" for c in graph.conditions)
    assert not graph.events
    assert not graph.constraints


def test_explicit_visible_region_entry_and_exit():
    graph = compile_text(
        "Battery enters the visible image region case; Battery exits the visible image region case"
    )
    assert [e.predicate.type for e in graph.events] == [
        "object_entered_region",
        "object_exited_region",
    ]
    assert graph.regions[0].observability == "SUPPORTED"
    assert "containment" in graph.regions[0].description


def test_state_change_requires_visible_criteria():
    graph = compile_text(
        "Case visibly changes closure from open to closed "
        "(visual criteria: lid visibly covers opening)."
    )
    predicate = graph.events[0].predicate
    assert isinstance(predicate, StateChange)
    assert predicate.state_dimension == "closure"
    assert predicate.visual_criteria == "lid visibly covers opening"


def test_final_visible_condition_is_explicit():
    graph = compile_text("At end, battery is visible.")
    assert graph.conditions[0].scope == "final"
    assert graph.conditions[0].predicate.type == "object_visible"


def test_hidden_final_condition_retains_final_scope():
    graph = compile_text("At end, battery is charged.")
    assert graph.conditions[0].scope == "final"
    assert graph.conditions[0].observability == "UNSUPPORTED"


def test_claiming_visual_criteria_does_not_make_hidden_dimensions_visible():
    graph = compile_text(
        "Battery visibly changes electrical energy from low to high "
        "(visual criteria: indicator is green)."
    )
    assert not graph.events
    assert graph.conditions[0].observability == "UNSUPPORTED"


def test_exact_demo_semantics_no_unstated_order():
    graph = compile_text(
        "1. Move the blue block onto the mat.\n2. Place the cup on the mat.\n"
        "3. Raise the green card."
    )
    assert len(graph.events) == 3
    assert not graph.constraints
    assert all(e.observability == "SUPPORTED" for e in graph.events)
    assert isinstance(graph.events[2].predicate, StateChange)


@pytest.mark.parametrize("text", ["", " \n", "x" * 10001, "\n".join(["x"] * 31)])
def test_grammar_input_limits(text):
    with pytest.raises(ValueError):
        validate_procedure(text)


def test_thirty_unknown_instructions_are_retained():
    text = "\n".join(f"{i}. Unknown action {i}." for i in range(1, 31))
    validate_procedure(text)
    graph = compile_text(text)
    assert len(graph.conditions) == 30
