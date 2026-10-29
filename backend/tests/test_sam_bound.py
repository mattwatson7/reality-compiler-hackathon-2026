import base64

import pytest
from pydantic import SecretStr

from backend.app.meta import MetaClient, MetaDisabled, ModelCatalog
from backend.app.store import Store
from scripts.meta_smoke import synthetic_clip


def sam_body(path):
    return {
        "model": "sam-3.1",
        "stream": False,
        "input": [
            {
                "role": "user",
                "type": "message",
                "content": [
                    {
                        "type": "input_text",
                        "text": "<0f>1<|box;x1=24;y1=39;x2=51;y2=66;w=320;h=180|>",
                    },
                    {
                        "type": "input_video",
                        "video_url": "data:video/mp4;base64,"
                        + base64.b64encode(path.read_bytes()).decode(),
                    },
                ],
            }
        ],
        "metadata": {
            "propagation_direction": "forward",
            "mask_encoding": "one_bit",
            "include_confidence": "true",
        },
    }


def make_client(tmp_path, response):
    return MetaClient(
        key=SecretStr("test-secret"),
        store=Store(tmp_path / "runs.sqlite"),
        paid_enabled=True,
        smoke_approved=True,
        catalog=ModelCatalog(("sam-3.1",), True),
        request=lambda *args: response,
    )


def test_actual_submitted_bytes_determine_tight_reservation(tmp_path):
    path = tmp_path / "clip.mp4"
    synthetic_clip(path)
    c = make_client(tmp_path, {"model": "sam-3.1", "usage": {"video_frames_processed": 72}})
    raw = c.dispatch("/v1/responses", sam_body(path), model="sam-3.1", upper_bound_microusd=1)
    assert c.usage[0]["reserved_microusd"] == 14400
    assert c.store.ledger()["committed_microusd"] == 14400
    c.acknowledge(raw)
    assert c.usage[0]["actual_microusd"] == 14400


@pytest.mark.parametrize("mutation", ["direction", "prompt", "media", "dimensions"])
def test_tighter_bound_rejects_unverified_range_before_reserving(tmp_path, mutation):
    path = tmp_path / "clip.mp4"
    synthetic_clip(path)
    body = sam_body(path)
    if mutation == "direction":
        body["metadata"]["propagation_direction"] = "both"
    elif mutation == "prompt":
        body["input"][0]["content"][0]["text"] = "<0f>cup<30f>cup"
    elif mutation == "media":
        body["input"][0]["content"][1]["video_url"] = "https://untrusted.example/clip.mp4"
    else:
        body["input"][0]["content"][0]["text"] = body["input"][0]["content"][0]["text"].replace(
            "w=320", "w=640"
        )
    c = make_client(tmp_path, {})
    with pytest.raises(MetaDisabled):
        c.dispatch("/v1/responses", body, model="sam-3.1", upper_bound_microusd=14400)
    assert c.store.ledger()["reservations"] == 0


def test_excess_actual_usage_cannot_settle_tighter_reservation(tmp_path):
    path = tmp_path / "clip.mp4"
    synthetic_clip(path)
    c = make_client(tmp_path, {"model": "sam-3.1", "usage": {"video_frames_processed": 73}})
    raw = c.dispatch("/v1/responses", sam_body(path), model="sam-3.1", upper_bound_microusd=14400)
    c.acknowledge(raw)
    assert not c.usage[0]["usage_verified"]
    assert c.store.ledger()["committed_microusd"] == 14400


def test_inconsistent_lower_billed_frames_cannot_settle_complete_request(tmp_path):
    path = tmp_path / "clip.mp4"
    synthetic_clip(path)
    c = make_client(tmp_path, {"model": "sam-3.1", "usage": {"video_frames_processed": 50}})
    raw = c.dispatch("/v1/responses", sam_body(path), model="sam-3.1", upper_bound_microusd=14400)
    c.acknowledge(raw)
    assert not c.usage[0]["usage_verified"]
    assert c.store.ledger()["committed_microusd"] == 14400
