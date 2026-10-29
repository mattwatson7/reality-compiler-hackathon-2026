def test_capture_review_imports_actual_evidence_without_paid_dispatch_or_ledger_reset(tmp_path):
    from backend.app.config import Settings
    from backend.app.service import JobService
    from scripts.open_capture_review import import_capture

    # An offline imported run must stay offline even on a Wonder-configured server.
    svc = JobService(Settings(data_dir=tmp_path, compiler_mode="muse_wonder"))
    try:
        svc.store.reserve_cost("existing-uncertain-request", 12345)
        ledger = svc.store.ledger()
        first = import_capture(svc)
        second = import_capture(svc)
        assert first != second
        job = svc.get_job(first)
        assert job["execution_mode"] == "offline_capture_review"
        assert job["footage_origin"] == "generated"
        assert job["result"]["verdict"] == "PASS"
        assert svc.store.ledger() == ledger
        assert [h["result"]["verdict"] for h in svc.evaluation_history(first)] == [
            "PASS",
            "FAIL",
            "FAIL",
            "UNKNOWN",
        ]
        revised = svc.reevaluate(
            first,
            "Move the cup into the visible marked region before "
            "moving the blue block into that region.",
        )
        assert revised["reuse_status"] == "reused"
        assert revised["result"]["verdict"] == "FAIL"
        assert revised["inference_usage"] == []
        assert svc.store.ledger() == ledger
    finally:
        svc.pool.shutdown(wait=True)


def test_review_cli_service_does_not_recover_another_servers_active_jobs(tmp_path):
    from backend.app.store import Store
    from scripts.open_capture_review import review_service

    store = Store(tmp_path / "runs.sqlite")
    store.create_job("existing", {"status": "processing"})
    service = review_service(tmp_path)
    try:
        assert store.get_job("existing")["status"] == "processing"
    finally:
        service.pool.shutdown(wait=True)
