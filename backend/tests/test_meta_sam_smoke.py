import json
import sqlite3

import pytest
from pydantic import SecretStr

from backend.app.meta import MetaContractError, MetaDisabled, ModelCatalog
from backend.app.store import Store


def test_sam_live_entrypoint_is_unapproved_even_with_execution_flag(monkeypatch):
    from scripts import meta_sam_smoke

    monkeypatch.setattr("sys.argv", ["sam_smoke", "--execute-authorized-once"])
    with pytest.raises(MetaDisabled, match="authorization"):
        meta_sam_smoke.main()


def test_independent_authorization_is_durable_and_not_old_claim(tmp_path):
    from scripts.meta_sam_smoke import AUTHORIZATION_ID, claim_authorization
    from scripts.meta_smoke import AUTHORIZATION_ID as OLD_ID

    store = Store(tmp_path / "runs.sqlite")
    claim_authorization(store)
    assert AUTHORIZATION_ID != OLD_ID
    with pytest.raises(sqlite3.IntegrityError):
        claim_authorization(Store(store.path))
    assert not store.expired_jobs(1e20)


def test_sam_client_allows_one_sam_only_and_defers_settlement(tmp_path):
    from scripts.meta_sam_smoke import SAMOnlyClient

    c = SAMOnlyClient(
        key=SecretStr("test-secret"),
        store=Store(tmp_path / "runs.sqlite"),
        paid_enabled=True,
        smoke_approved=True,
        catalog=ModelCatalog(("sam-3.1", "muse-wonder-1.0"), True),
        request=lambda *args: {},
    )
    for model in ("muse-wonder-1.0", "muse-spark-1.3"):
        with pytest.raises(MetaDisabled):
            c.dispatch("/v1/chat/completions", {}, model=model, upper_bound_microusd=14400)
    # Tight bound must reject even a synthetic transport with unbounded media.
    with pytest.raises(MetaDisabled):
        c.dispatch("/v1/responses", {}, model="sam-3.1", upper_bound_microusd=14400)
    assert not c.usage


def test_reviewed_local_graph_has_only_two_entries_and_explicit_order():
    from scripts.meta_sam_smoke import reviewed_graph

    graph = reviewed_graph()
    assert graph.compilation_source == "local_rules"
    assert len(graph.events) == 2 and not graph.conditions
    assert graph.constraints[0].ordered_pair() == ("event1", "event2")
    assert all(e.observability == "SUPPORTED" for e in graph.events)


def test_pinned_preflight_never_needs_a_key_or_network(monkeypatch):
    from backend.app.meta import MetaClient
    from scripts import meta_sam_smoke

    monkeypatch.setattr(MetaClient, "discover", lambda *args: pytest.fail("network"))
    monkeypatch.setattr(meta_sam_smoke, "server_key", lambda: pytest.fail("key read"))
    graph = meta_sam_smoke.reviewed_graph()
    assert graph.procedure
    plan = json.loads(meta_sam_smoke.PLAN_PATH.read_text())
    assert plan["maximum_reservation_microusd"] == 14400
    assert plan["authorization_status"] == "pending_human_approval"


def sam_fixture(tmp_path, mode="valid"):
    from backend.app.perception import inspect_video
    from backend.tests.test_sam import envelope, wire
    from scripts.meta_sam_smoke import SAMOnlyClient, reviewed_graph
    from scripts.meta_smoke import selections, synthetic_clip

    path = tmp_path / "synthetic.mp4"
    synthetic_clip(path)
    graph = reviewed_graph()
    initialization = selections(graph, inspect_video(path)["frame_reference"])
    lines = []
    for i in range(72):
        first = wire(i, 1, 25, 40)
        second = wire(i, 2, 75, 110).split(">", 1)[1]
        lines.append(first + "," + second)
    if mode == "missing":
        del lines[35]
    elif mode == "overlap":
        lines[35] = wire(35, 1, 25, 40) + "," + wire(35, 2, 25, 40).split(">", 1)[1]
    response = envelope("\n".join(lines), usage={"video_frames_processed": 72})
    calls = []

    def request(*args):
        calls.append(args)
        if mode == "timeout":
            raise TimeoutError("private-provider-string")
        return response

    client = SAMOnlyClient(
        key=SecretStr("test-secret"),
        store=Store(tmp_path / "runs.sqlite"),
        paid_enabled=True,
        smoke_approved=True,
        catalog=ModelCatalog(("sam-3.1",), True),
        request=request,
    )
    return client, path, graph, initialization, calls


def test_sam_only_success_reports_usage_and_settles_only_validated_masks(tmp_path):
    from scripts.meta_sam_smoke import run_once

    client, path, graph, initialization, calls = sam_fixture(tmp_path)
    tracks = run_once(client, path, graph, initialization)
    assert len(tracks) == 2 and len(calls) == 1
    assert client.reported_usage == {"video_frames_processed": 72}
    assert client.usage[0]["reserved_microusd"] == 14400
    assert client.usage[0]["actual_microusd"] == 14400
    with pytest.raises(MetaDisabled):
        run_once(client, path, graph, initialization)
    assert len(calls) == 1


@pytest.mark.parametrize("mode", ["missing", "overlap", "timeout"])
def test_sam_only_failure_retains_reservation_and_consumes_attempt(tmp_path, mode):
    from scripts.meta_sam_smoke import run_once

    client, path, graph, initialization, calls = sam_fixture(tmp_path, mode)
    with pytest.raises(MetaContractError) as error:
        run_once(client, path, graph, initialization)
    assert "private-provider-string" not in str(error.value)
    assert len(calls) == 1
    assert client.store.ledger()["committed_microusd"] == 14400
    assert not client.usage[0]["usage_verified"]
    with pytest.raises(MetaDisabled):
        run_once(client, path, graph, initialization)
    assert len(calls) == 1


@pytest.mark.parametrize(
    "usage",
    [
        None,
        {},
        {"video_frames_processed": 50},
        {"video_frames_processed": 73},
        {"video_frames_processed": True},
    ],
)
def test_valid_sam_masks_with_unknown_or_excess_usage_retain_full_bound(tmp_path, usage):
    from scripts.meta_sam_smoke import run_once

    client, path, graph, initialization, calls = sam_fixture(tmp_path)
    original = client._request

    def replace_usage(*args):
        response = original(*args)
        if usage is None:
            response.pop("usage", None)
        else:
            response["usage"] = usage
        return response

    client._request = replace_usage
    tracks = run_once(client, path, graph, initialization)
    assert len(tracks) == 2 and len(calls) == 1
    assert client.store.ledger()["committed_microusd"] == 14400
    assert client.usage[0]["actual_microusd"] is None
    assert not client.usage[0]["usage_verified"]


def test_reviewed_artifact_bytes_are_platform_stable_lf():
    from scripts.meta_sam_smoke import GRAPH_PATH, PLAN_PATH, SELECTION_PATH

    for path in (GRAPH_PATH, PLAN_PATH, SELECTION_PATH):
        assert b"\r" not in path.read_bytes()
