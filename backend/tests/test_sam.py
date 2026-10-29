"""Synthetic SAM contract tests; no live request or camera validation occurs."""

import pytest

from backend.app.sam import SAMContractError, SAMTrackerProvider, decode_one_bit, parse_segmentation
from backend.tests.test_perception import graph, initialization, video


def test_official_one_bit_conformance_vector():
    # Official meta-models/meta-sam compact-api-confidence synthetic conformance case.
    raster = decode_one_bit("!!!!!(QO(0lu8?", 5, 5)
    assert raster.reshape(-1).tolist() == [
        1,
        0,
        0,
        1,
        0,
        0,
        0,
        1,
        1,
        0,
        0,
        0,
        0,
        0,
        0,
        1,
        0,
        1,
        1,
        1,
        1,
        0,
        0,
        0,
        1,
    ]


def test_key_order_and_confidence_exponent_are_not_positional():
    text = wire(confidence="9e-1").replace("x=0;y=0;c=9e-1", "c=.85;y=0;x=0")
    record = parse_segmentation(text, 320, 180, 4, {1})[0][1]
    assert record.confidence == 0.85  # Conservative min of separate box/mask confidences.


@pytest.mark.parametrize("confidence", ["nan", "inf", "1.1", "-0.1", ""])
def test_invalid_or_missing_confidence_never_becomes_decisive(confidence):
    record = parse_segmentation(wire(confidence=confidence), 320, 180, 4, {1})[0][1]
    assert record.confidence == 0.0


@pytest.mark.parametrize("payload", ["!bad", "!!!!!(QO(0lu8", "!!!!!(QO(0lu8?!", "~!!!!(QO(0lu8?"])
def test_malformed_codec_fails_closed(payload):
    with pytest.raises(SAMContractError):
        decode_one_bit(payload, 5, 5)


def wire(index=0, obj=1, x=10, y=20, confidence="0.9"):
    return (
        f"<{index}f>{obj}<|box;x1={x};y1={y};x2={x + 4};y2={y + 4};w=320;h=180;c={confidence}|>"
        f"<|mask;x=0;y=0;c={confidence};data=5,5,!!!!!(QO(0lu8?|>"
    )


def test_explicit_out_of_order_frames_and_sparse_ids_are_keyed_by_value():
    parsed = parse_segmentation(wire(2, 7) + "\n" + wire(0, 3), 320, 180, 4, {3, 7})
    assert set(parsed) == {0, 2}
    assert set(parsed[2]) == {7}
    assert parsed[2][7].mask.sum() == 10


@pytest.mark.parametrize(
    "text",
    [
        wire(4),
        wire(obj=9),
        wire() + "\n" + wire(),
        wire(x=319),
        wire().replace("data=5,5", "data=5,6"),
        wire().replace("<|mask", "<|unknown"),
        wire().replace("w=320", "w=321"),
    ],
)
def test_bad_geometry_ids_and_duplicate_frames_are_rejected(text):
    with pytest.raises(SAMContractError):
        parse_segmentation(text, 320, 180, 4, {1})


def envelope(text, **updates):
    result = {
        "model": "sam-3.1",
        "status": "completed",
        "output": [
            {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": text}],
            }
        ],
        "usage": {"video_frames_processed": 144},
    }
    result.update(updates)
    return result


class Transport:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def dispatch(self, path, body, *, model, upper_bound_microusd):
        self.calls.append((path, body, model, upper_bound_microusd))
        return self.response


def test_missing_frames_permanently_invalidate_track_and_request_is_bounded(tmp_path):
    from backend.app.perception import inspect_video

    path = tmp_path / "generated.mp4"
    video(path)
    meta = inspect_video(path)
    init = initialization(graph(), meta["frame_reference"])
    transport = Transport(envelope(wire(x=20, y=30) + "\n" + wire(2, x=20, y=30)))
    provider = SAMTrackerProvider(init, transport)
    tracks = provider.track(path, graph())
    assert provider.segmentation_text == wire(x=20, y=30) + "\n" + wire(2, x=20, y=30)
    assert tracks[0].samples[0].status == "reliable"
    assert tracks[0].invalid_intervals
    assert all(s.status != "reliable" for s in tracks[0].samples[1:])
    assert len(tracks[0].samples) == 144
    path_arg, body, model, bound = transport.calls[0]
    assert (path_arg, model, bound) == ("/v1/responses", "sam-3.1", 28800)
    assert body["metadata"] == {
        "include_confidence": "true",
        "mask_encoding": "one_bit",
        "propagation_direction": "forward",
    }
    assert "<0f>1<|box;" in body["input"][0]["content"][0]["text"]
    assert body["input"][0]["content"][1]["video_url"].startswith("data:video/mp4;base64,")


@pytest.mark.parametrize(
    "response",
    [
        envelope("", status="incomplete"),
        envelope("", model="other"),
        envelope("", output=[]),
        envelope(
            "",
            output=[
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "refusal", "refusal": "no"}],
                }
            ],
        ),
    ],
)
def test_invalid_response_envelopes_are_safe_failures(tmp_path, response):
    from backend.app.perception import inspect_video

    path = tmp_path / "generated.mp4"
    video(path)
    init = initialization(graph(), inspect_video(path)["frame_reference"])
    with pytest.raises(SAMContractError):
        SAMTrackerProvider(init, Transport(response)).track(path, graph())


def test_a_full_contract_response_drives_existing_deterministic_evaluator(tmp_path):
    """Synthetic geometry stream only; proves adapter/evaluator plumbing, not live SAM."""
    from backend.app.evaluator import evaluate
    from backend.app.perception import LocalRegionObserver, inspect_video

    path = tmp_path / "generated.mp4"
    video(path)
    g = graph()
    metadata = inspect_video(path)
    init = initialization(g, metadata["frame_reference"])
    lines = []
    for index in range(144):
        bx = min(220, 20 + max(0, index - 20) * 10)
        cx = min(220, 20 + max(0, index - 75) * 10)
        left = wire(index, 1, bx, 30)
        right = wire(index, 2, cx, 100).split(">", 1)[1]
        lines.append(left + "," + right)
    transport = Transport(envelope("\n".join(lines)))
    tracks = SAMTrackerProvider(init, transport).track(path, g)
    assert all(not track.invalid_intervals for track in tracks)
    assert all(track.source == "meta_sam" and track.model_id == "sam-3.1" for track in tracks)
    observations = LocalRegionObserver(init).observe(path, g, tracks)
    assert evaluate(g, observations, metadata["duration_s"]).verdict == "PASS"


def test_mask_declared_allocation_is_bounded_before_decoding():
    with pytest.raises(SAMContractError):
        decode_one_bit("!!!!!(QO(0lu8?", 1000000, 1000000)


def test_model_mask_must_correspond_to_prompted_identity_at_frame_zero(tmp_path):
    from backend.app.perception import inspect_video

    path = tmp_path / "generated.mp4"
    video(path)
    g = graph()
    init = initialization(g, inspect_video(path)["frame_reference"])
    tracks = SAMTrackerProvider(init, Transport(envelope(wire(0, 1, 250, 100)))).track(path, g)
    assert tracks[0].samples[0].status != "reliable"


def test_late_missing_mask_invalidates_earlier_event_for_entire_run(tmp_path):
    from backend.app.evaluator import evaluate
    from backend.app.perception import LocalRegionObserver, inspect_video

    path = tmp_path / "generated.mp4"
    video(path)
    g = graph()
    metadata = inspect_video(path)
    init = initialization(g, metadata["frame_reference"])
    lines = []
    for index in range(144):
        bx = min(220, 20 + max(0, index - 20) * 10)
        cx = min(220, 20 + max(0, index - 75) * 10)
        left = wire(index, 1, bx, 30)
        right = wire(index, 2, cx, 100)
        lines.append(right if index == 120 else left + "," + right.split(">", 1)[1])
    tracks = SAMTrackerProvider(init, Transport(envelope("\n".join(lines)))).track(path, g)
    observations = LocalRegionObserver(init).observe(path, g, tracks)
    assert observations
    assert evaluate(g, observations, metadata["duration_s"]).verdict == "UNKNOWN"
    assert all(not item.usable for item in observations if item.predicate.object_id == "object1")
