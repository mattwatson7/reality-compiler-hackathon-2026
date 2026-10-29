from concurrent.futures import ThreadPoolExecutor

import pytest

from backend.app.store import BudgetExceeded, Store


def test_cost_cap_is_atomic_and_persistent(tmp_path):
    path = tmp_path / "runs.sqlite"
    store = Store(path)

    def reserve(_):
        try:
            store.reserve_cost("test", 30_000_000)
            return True
        except BudgetExceeded:
            return False

    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(pool.map(reserve, range(8))) == 3
    assert Store(path).ledger()["committed_microusd"] == 90_000_000
    with pytest.raises(BudgetExceeded):
        store.reserve_cost("test", 10_000_001)
    store.reserve_cost("test", 10_000_000)


def test_settlement_refunds_only_unused_reservation(tmp_path):
    store = Store(tmp_path / "runs.sqlite")
    reservation = store.reserve_cost("compiler", 10_000_000)
    with pytest.raises(ValueError):
        store.settle_cost(reservation, 10_000_001)
    store.settle_cost(reservation, 1_000_000)
    assert store.ledger()["committed_microusd"] == 1_000_000
    with pytest.raises(ValueError):
        store.settle_cost(reservation, 0)
    for value in [-1, 1.5, True]:
        with pytest.raises(ValueError):
            store.reserve_cost("compiler", value)


def test_job_restart_and_expiry_preserve_audit_metadata(tmp_path):
    store = Store(tmp_path / "runs.sqlite")
    store.create_job("abc", {"status": "queued", "expires_at": 10, "progress": 0})
    store.recover_interrupted()
    assert store.get_job("abc")["status"] == "failed"
    assert store.expired_jobs(9) == []
    assert store.expired_jobs(10) == ["abc"]
    store.update_job("abc", status="expired", media_url=None)
    assert store.expired_jobs(11) == []
    assert store.get_job("abc")["media_url"] is None


def test_allocating_job_survives_concurrent_orphan_sweep(tmp_path, monkeypatch):
    from pathlib import Path

    from backend.app.config import Settings
    from backend.app.service import JobService

    service = JobService(Settings(data_dir=tmp_path))
    original_mkdir = Path.mkdir

    def mkdir_then_sweep(path, *args, **kwargs):
        result = original_mkdir(path, *args, **kwargs)
        if path.parent == service.media_dir:
            service.cleanup()
        return result

    monkeypatch.setattr(Path, "mkdir", mkdir_then_sweep)
    try:
        job_id, directory = service.allocate("Lift cup.", "mock-upload")
        assert directory.is_dir()
        assert service.store.get_job(job_id)["status"] == "queued"
    finally:
        service.pool.shutdown()
