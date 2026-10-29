import pytest


def test_container_smoke_rejects_live_provider_before_post():
    from scripts.docker_smoke import validate_health

    with pytest.raises(ValueError, match="paid"):
        validate_health(
            {
                "mode": "fixture",
                "real_muse_compilation": False,
                "meta": {"paid_inference_enabled": True, "sam_selectable": False},
            }
        )


def test_container_smoke_rejects_live_compiler_even_with_disabled_sam():
    from scripts.docker_smoke import validate_health

    with pytest.raises(ValueError, match="fixture"):
        validate_health(
            {
                "mode": "fixture",
                "real_muse_compilation": True,
                "meta": {"paid_inference_enabled": False, "sam_selectable": False},
            }
        )


@pytest.mark.parametrize("error", [ConnectionResetError, ConnectionAbortedError, TimeoutError])
def test_container_readiness_survives_transport_startup_race(error, monkeypatch):
    from scripts.docker_smoke import wait_for_health

    attempts = []
    health = {"status": "ok"}

    def request():
        attempts.append(1)
        if len(attempts) == 1:
            raise error("Container port exists before HTTP worker is ready")
        return health

    monkeypatch.setattr("scripts.docker_smoke.time.sleep", lambda _: None)
    assert wait_for_health(request) == health
    assert len(attempts) == 2
