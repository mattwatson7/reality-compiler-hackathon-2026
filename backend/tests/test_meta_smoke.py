import sqlite3

import pytest
from pydantic import SecretStr

from backend.app.meta import MetaContractError, MetaDisabled, ModelCatalog
from backend.app.store import Store
from scripts.meta_smoke import (
    AUTHORIZATION_ID,
    SmokeClient,
    claim_authorization,
    migrate_authorization,
)


def client(store, request):
    return SmokeClient(
        key=SecretStr("test-secret"),
        store=store,
        paid_enabled=True,
        smoke_approved=True,
        catalog=ModelCatalog(("muse-wonder-1.0", "sam-3.1"), True),
        request=request,
    )


def wonder(c):
    return c.dispatch(
        "/v1/chat/completions",
        {
            "model": "muse-wonder-1.0",
            "max_completion_tokens": 4096,
        },
        model="muse-wonder-1.0",
        upper_bound_microusd=4276224,
    )


def test_claim_cannot_be_repeated_even_after_restart(tmp_path):
    path = tmp_path / "runs.sqlite"
    claim_authorization(Store(path))
    with pytest.raises(sqlite3.IntegrityError):
        claim_authorization(Store(path))
    assert Store(path).get_job(AUTHORIZATION_ID) is None
    assert Store(path).expired_jobs(1e20) == []


def test_consumed_legacy_claim_is_migrated_without_restoring_allowance(tmp_path):
    store = Store(tmp_path / "runs.sqlite")
    store.create_job(AUTHORIZATION_ID, {"status": "consumed_finished"})
    migrate_authorization(store)
    assert store.expired_jobs(1e20) == []
    with pytest.raises(sqlite3.IntegrityError):
        claim_authorization(store)


def test_first_failure_blocks_all_further_calls(tmp_path):
    calls = []

    def fail(*args):
        calls.append(args)
        raise TimeoutError("secret remote data")

    c = client(Store(tmp_path / "runs.sqlite"), fail)
    with pytest.raises(MetaContractError):
        wonder(c)
    with pytest.raises(MetaDisabled):
        wonder(c)
    with pytest.raises(MetaDisabled):
        c.dispatch("/v1/responses", {}, model="sam-3.1", upper_bound_microusd=144000)
    assert len(calls) == 1
    assert c.store.ledger()["committed_microusd"] == 4276224


def test_sam_requires_validated_first_success_and_rejects_spark(tmp_path):
    calls = []
    c = client(Store(tmp_path / "runs.sqlite"), lambda *args: calls.append(args) or {})
    raw = wonder(c)
    with pytest.raises(MetaDisabled):
        c.dispatch("/v1/responses", {}, model="sam-3.1", upper_bound_microusd=144000)
    c.acknowledge(raw)
    c.dispatch("/v1/responses", {}, model="sam-3.1", upper_bound_microusd=144000)
    with pytest.raises(MetaDisabled):
        c.dispatch("/v1/responses", {}, model="sam-3.1", upper_bound_microusd=144000)
    with pytest.raises(MetaDisabled):
        c.dispatch("/v1/chat/completions", {}, model="muse-spark-1.3", upper_bound_microusd=1328128)
    assert len(calls) == 2
    assert sum(x["reserved_microusd"] for x in c.usage) == 4420224


def test_excess_bound_blocks_without_network_or_reservation(tmp_path):
    c = client(Store(tmp_path / "runs.sqlite"), lambda *args: pytest.fail("network"))
    with pytest.raises(MetaDisabled):
        c.dispatch(
            "/v1/chat/completions", {}, model="muse-wonder-1.0", upper_bound_microusd=4276225
        )
    assert c.store.ledger()["reservations"] == 0


def test_consumed_live_entrypoint_is_retired_even_with_execution_flag(monkeypatch):
    from scripts import meta_smoke

    monkeypatch.setattr("sys.argv", ["meta_smoke", "--execute-authorized-once"])
    monkeypatch.setattr(meta_smoke, "Settings", None)
    with pytest.raises(MetaDisabled, match="consumed"):
        meta_smoke.main()
