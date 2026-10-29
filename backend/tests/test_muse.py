"""Synthetic contract fixtures only; these are not recorded Meta responses."""

import copy
import json
from pathlib import Path

import httpx
import pytest

from backend.app.muse import (
    DispatchBound,
    MuseContractError,
    MuseDisabled,
    MuseWonderCompiler,
    OfflineResponse,
    OfflineTransport,
    strict_graph_schema,
)
from backend.app.store import CAP_MICROUSD, BudgetExceeded, Store

PROCEDURE = "Show the cup."


def graph():
    return {
        "version": "2.0",
        "procedure": PROCEDURE,
        "compilation_source": "muse",
        "objects": [{"id": "cup", "label": "cup", "description": "cup"}],
        "regions": [],
        "constraints": [],
        "conditions": [],
        "events": [
            {
                "id": "show",
                "instruction": PROCEDURE,
                "source": {"start": 0, "end": len(PROCEDURE), "quote": PROCEDURE},
                "predicate": {"type": "object_visible", "object_id": "cup"},
            }
        ],
    }


def response(payload=None, *, finish="stop", refusal=None, usage="valid", status=200):
    body = {
        "id": "fixture",
        "object": "chat.completion",
        "created": 1,
        "model": "muse-wonder-1.0",
        "choices": [
            {
                "index": 0,
                "finish_reason": finish,
                "message": {
                    "role": "assistant",
                    "content": json.dumps(graph() if payload is None else payload),
                    "refusal": refusal,
                },
            }
        ],
    }
    if usage == "valid":
        body["usage"] = {
            "prompt_tokens": 100,
            "completion_tokens": 20,
            "total_tokens": 120,
            "prompt_tokens_details": {"cached_tokens": 0},
        }
    elif usage is not None:
        body["usage"] = usage
    # httpx is dev-only; MockTransport never makes a network request.
    with httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(status, json=body))
    ) as client:
        result = client.post("https://fixture.invalid/v1/chat/completions")
    return OfflineResponse(result.status_code, result.content)


def compiler(tmp_path: Path, responses):
    store = Store(tmp_path / "ledger.db")
    transport = OfflineTransport(responses)
    adapter = MuseWonderCompiler(
        store=store, transport=transport, bound=DispatchBound(1000, 100, verified=True)
    )
    return adapter, store, transport


def test_default_is_disabled():
    with pytest.raises(MuseDisabled, match="disabled"):
        MuseWonderCompiler()


def test_valid_graph_request_and_integer_settlement(tmp_path):
    adapter, store, transport = compiler(tmp_path, [response()])
    assert adapter.compile(PROCEDURE).compilation_source == "muse"
    assert store.ledger()["committed_microusd"] == 800
    request = transport.requests[0]
    assert request["url"] == "https://api.meta.ai/v1/chat/completions"
    assert request["body"]["model"] == "muse-wonder-1.0"
    assert request["body"]["max_completion_tokens"] == 100
    assert request["body"]["response_format"]["json_schema"]["strict"] is True


@pytest.mark.parametrize("change", ["reference", "cycle", "span", "procedure", "source"])
def test_invalid_graph_repair_is_bounded_and_reserved(tmp_path, change):
    bad = graph()
    if change == "reference":
        bad["events"][0]["predicate"]["object_id"] = "invented"
    elif change == "cycle":
        bad["constraints"] = [
            {
                "id": "loop",
                "operator": "BEFORE",
                "first": "show",
                "second": "show",
                "source": bad["events"][0]["source"],
            }
        ]
    elif change == "span":
        bad["events"][0]["source"]["quote"] = "invented"
    elif change == "procedure":
        bad["procedure"] = "Changed text!"
    else:
        bad["compilation_source"] = "fixture"
    adapter, store, transport = compiler(tmp_path, [response(bad), response(bad), response()])
    with pytest.raises(MuseContractError, match="graph"):
        adapter.compile(PROCEDURE)
    assert len(transport.requests) == 2
    assert store.ledger()["committed_microusd"] == 12_000


def test_one_repair_can_succeed(tmp_path):
    bad = graph()
    bad["events"][0]["predicate"]["object_id"] = "invented"
    adapter, store, transport = compiler(tmp_path, [response(bad), response()])
    assert adapter.compile(PROCEDURE).procedure == PROCEDURE
    assert len(transport.requests) == 2
    assert store.ledger()["committed_microusd"] == 6800


@pytest.mark.parametrize(
    "item",
    [
        response(finish="length"),
        response(refusal="No"),
        response(status=401),
        response(status=429),
        OfflineResponse(200, b"not json"),
        OfflineResponse(200, b"{}"),
        RuntimeError("secret payload"),
    ],
)
def test_uncertain_or_rejected_response_never_retries_or_releases_budget(tmp_path, item):
    adapter, store, transport = compiler(tmp_path, [item, response()])
    with pytest.raises(MuseContractError) as caught:
        adapter.compile(PROCEDURE)
    assert "secret" not in str(caught.value)
    assert len(transport.requests) == 1
    assert store.ledger()["committed_microusd"] == 6000


@pytest.mark.parametrize(
    "usage",
    [
        None,
        {},
        {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 99},
        {"prompt_tokens": 1001, "completion_tokens": 20, "total_tokens": 1021},
        {"prompt_tokens": True, "completion_tokens": 20, "total_tokens": 21},
        {"prompt_tokens": 100, "completion_tokens": 101, "total_tokens": 201},
        {
            "prompt_tokens": 100,
            "completion_tokens": 20,
            "total_tokens": 120,
            "prompt_tokens_details": {"cached_tokens": 101},
        },
    ],
)
def test_unverified_usage_retains_full_reservation(tmp_path, usage):
    adapter, store, _ = compiler(tmp_path, [response(usage=usage)])
    adapter.compile(PROCEDURE)
    assert store.ledger()["committed_microusd"] == 6000


def test_budget_blocks_before_transport(tmp_path):
    adapter, store, transport = compiler(tmp_path, [response()])
    store.reserve_cost("previous", CAP_MICROUSD)
    with pytest.raises(BudgetExceeded):
        adapter.compile(PROCEDURE)
    assert transport.requests == []


def test_unverified_bound_disabled(tmp_path):
    with pytest.raises(MuseDisabled):
        MuseWonderCompiler(
            store=Store(tmp_path / "x.db"),
            transport=OfflineTransport([]),
            bound=DispatchBound(1000, 100, verified=False),
        )


def test_strict_schema_has_required_fields_closed_objects_and_anyof():
    schema = strict_graph_schema()
    assert schema["type"] == "object"
    encoded = json.dumps(schema)
    assert '"oneOf"' not in encoded and '"discriminator"' not in encoded
    assert '"anyOf"' in encoded

    def visit(value):
        if isinstance(value, dict):
            assert "default" not in value
            if value.get("type") == "object":
                assert value["additionalProperties"] is False
                assert set(value["required"]) == set(value["properties"])
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(copy.deepcopy(schema))


@pytest.mark.parametrize("mutation", ["tools", "role", "choices", "model", "content", "size"])
def test_envelope_rejections_are_terminal(tmp_path, mutation):
    raw = response()
    body = json.loads(raw.content)
    if mutation == "tools":
        body["choices"][0]["message"]["tool_calls"] = [{"id": "unexpected"}]
    elif mutation == "role":
        body["choices"][0]["message"]["role"] = "user"
    elif mutation == "choices":
        body["choices"] *= 2
    elif mutation == "model":
        body["model"] = "unverified-model"
    elif mutation == "content":
        body["choices"][0]["finish_reason"] = "content_filter"
    encoded = json.dumps(body).encode() if mutation != "size" else b" " * 1_000_001
    adapter, store, transport = compiler(tmp_path, [OfflineResponse(200, encoded), response()])
    with pytest.raises(MuseContractError):
        adapter.compile(PROCEDURE)
    assert len(transport.requests) == 1
    assert store.ledger()["committed_microusd"] == 6000


def test_invalid_json_graph_can_repair_without_replaying_raw_payload(tmp_path):
    body = json.loads(response().content)
    body["choices"][0]["message"]["content"] = "secret invalid payload"
    adapter, store, transport = compiler(
        tmp_path, [OfflineResponse(200, json.dumps(body).encode()), response()]
    )
    assert adapter.compile(PROCEDURE).version == "2.0"
    assert "secret" not in json.dumps(transport.requests[1])
    assert store.ledger()["reservations"] == 2


def test_second_attempt_requires_its_own_available_budget(tmp_path):
    bad = graph()
    bad["events"][0]["predicate"]["object_id"] = "missing"
    adapter, store, transport = compiler(tmp_path, [response(bad), response()])
    store.reserve_cost("previous", CAP_MICROUSD - 6000)
    with pytest.raises(BudgetExceeded):
        adapter.compile(PROCEDURE)
    assert len(transport.requests) == 1
    assert store.ledger()["committed_microusd"] == CAP_MICROUSD


@pytest.mark.parametrize("procedure", ["", "   ", "x" * 10001])
def test_invalid_local_procedure_does_not_dispatch(tmp_path, procedure):
    adapter, store, transport = compiler(tmp_path, [response()])
    with pytest.raises(ValueError):
        adapter.compile(procedure)
    assert not transport.requests
    assert store.ledger()["reservations"] == 0


@pytest.mark.parametrize("cached, expected", [(0, 800), (50, 610), (1, 797), (100, 420)])
def test_exact_cache_pricing_rounds_up_fractional_microusd(tmp_path, cached, expected):
    usage = {
        "prompt_tokens": 100,
        "completion_tokens": 20,
        "total_tokens": 120,
        "prompt_tokens_details": {"cached_tokens": cached},
    }
    adapter, store, _ = compiler(tmp_path, [response(usage=usage)])
    adapter.compile(PROCEDURE)
    assert store.ledger()["committed_microusd"] == expected


@pytest.mark.parametrize("details", ["absent", None, {}])
def test_missing_cache_breakdown_retains_full_reservation(tmp_path, details):
    usage = {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120}
    if details != "absent":
        usage["prompt_tokens_details"] = details
    adapter, store, _ = compiler(tmp_path, [response(usage=usage)])
    adapter.compile(PROCEDURE)
    assert store.ledger()["committed_microusd"] == 6000
