import pytest
from pydantic import SecretStr


def test_key_loads_from_root_dotenv_without_exposing_value(tmp_path, monkeypatch):
    from backend.app.meta import load_key

    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    (tmp_path / ".env").write_text('MODEL_API_KEY="unit-test-secret"\n')
    key = load_key(tmp_path)
    assert key.get_secret_value() == "unit-test-secret"
    assert "unit-test-secret" not in repr(key)
    monkeypatch.setenv("MODEL_API_KEY", "process-secret")
    assert load_key(tmp_path).get_secret_value() == "process-secret"


def test_default_gate_never_dispatches_or_reserves(tmp_path):
    from backend.app.meta import MetaClient, MetaDisabled
    from backend.app.store import Store

    store = Store(tmp_path / "runs.sqlite")
    client = MetaClient(key=SecretStr("secret"), store=store)
    with pytest.raises(MetaDisabled):
        client.dispatch("/v1/responses", {}, model="sam-3.1", upper_bound_microusd=10000)
    assert store.ledger()["reservations"] == 0


def test_transport_reserves_before_dispatch_and_keeps_uncertain_cost(tmp_path):
    from backend.app.meta import MetaClient, ModelCatalog
    from backend.app.store import Store

    store = Store(tmp_path / "runs.sqlite")
    calls = []

    def request(method, path, body):
        calls.append((method, path, store.ledger()["committed_microusd"]))
        return {"model": "sam-3.1", "usage": {}}

    client = MetaClient(
        key=SecretStr("secret"),
        store=store,
        paid_enabled=True,
        smoke_approved=True,
        catalog=ModelCatalog(("sam-3.1",), True),
        request=request,
    )
    client.dispatch("/v1/responses", {}, model="sam-3.1", upper_bound_microusd=10000)
    assert calls == [("POST", "/v1/responses", 144000)]
    assert store.ledger()["committed_microusd"] == 144000


@pytest.mark.parametrize(
    "response,retained",
    [
        ({"model": "sam-3.1", "usage": {"video_frames_processed": 50}}, 10000),
        ({"model": "sam-3.1", "usage": {"video_frames_processed": 51}}, 10200),
        ({"model": "sam-3.1", "usage": {"video_frames_processed": 999}}, 144000),
        ({"model": "unexpected", "usage": {"video_frames_processed": 50}}, 144000),
    ],
)
def test_sam_verified_cost_never_exceeds_reservation(tmp_path, response, retained):
    from backend.app.meta import MetaClient, ModelCatalog
    from backend.app.store import Store

    store = Store(tmp_path / "runs.sqlite")
    client = MetaClient(
        key=SecretStr("secret"),
        store=store,
        paid_enabled=True,
        smoke_approved=True,
        catalog=ModelCatalog(("sam-3.1",), True),
        request=lambda *args: response,
    )
    response = client.dispatch("/v1/responses", {}, model="sam-3.1", upper_bound_microusd=20000)
    client.acknowledge(response)
    assert store.ledger()["committed_microusd"] == retained


def test_partial_stream_is_rejected():
    from backend.app.meta import MetaContractError, parse_sse

    incomplete = b'data: {"type":"response.output_text.delta","delta":"partial"}\n\n'
    with pytest.raises(MetaContractError):
        parse_sse(incomplete)
    full = incomplete + b'data: {"type":"response.completed","response":{"model":"sam-3.1"}}\n\n'
    assert parse_sse(full)["output_text"] == "partial"


def test_timeout_retains_reservation_and_suppresses_remote_detail(tmp_path):
    from backend.app.meta import MetaClient, MetaContractError, ModelCatalog
    from backend.app.store import Store

    def timeout(*args):
        raise TimeoutError("sensitive-remote-payload")

    store = Store(tmp_path / "runs.sqlite")
    client = MetaClient(
        key=SecretStr("unit-secret"),
        store=store,
        paid_enabled=True,
        smoke_approved=True,
        catalog=ModelCatalog(("sam-3.1",), True),
        request=timeout,
    )
    with pytest.raises(MetaContractError) as error:
        client.dispatch("/v1/responses", {}, model="sam-3.1", upper_bound_microusd=1)
    assert "sensitive" not in str(error.value)
    assert store.ledger()["committed_microusd"] == 144000


def test_budget_exhaustion_prevents_transport(tmp_path):
    from backend.app.meta import MetaClient, ModelCatalog
    from backend.app.store import BudgetExceeded, Store

    store = Store(tmp_path / "runs.sqlite")
    store.reserve_cost("earlier", 99_900_000)
    calls = []
    client = MetaClient(
        key=SecretStr("unit-secret"),
        store=store,
        paid_enabled=True,
        smoke_approved=True,
        catalog=ModelCatalog(("sam-3.1",), True),
        request=lambda *args: calls.append(args),
    )
    with pytest.raises(BudgetExceeded):
        client.dispatch("/v1/responses", {}, model="sam-3.1", upper_bound_microusd=1)
    assert not calls


def test_network_is_disabled_under_automated_tests():
    from backend.app.meta import MetaClient, MetaDisabled

    with pytest.raises(MetaDisabled, match="automated tests"):
        MetaClient(key=SecretStr("unit-secret")).discover()


def test_verified_usage_is_not_settled_before_adapter_validation(tmp_path):
    from backend.app.meta import MetaClient, MetaContractError, ModelCatalog
    from backend.app.meta_semantics import LiveMuseWonderCompiler
    from backend.app.store import Store

    store = Store(tmp_path / "runs.sqlite")
    response = {
        "model": "muse-wonder-1.0",
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 10,
            "total_tokens": 110,
            "prompt_tokens_details": {"cached_tokens": 0},
        },
        "choices": [],
    }
    client = MetaClient(
        key=SecretStr("unit-secret"),
        store=store,
        paid_enabled=True,
        smoke_approved=True,
        catalog=ModelCatalog(("muse-wonder-1.0",), True),
        request=lambda *args: response,
    )
    with pytest.raises(MetaContractError):
        LiveMuseWonderCompiler(client).compile("The cup is visible.")
    assert store.ledger()["committed_microusd"] == 4 * 1048576 + 20 * 4096
