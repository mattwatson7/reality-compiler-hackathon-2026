"""Synthetic algorithm regressions; these are not genuine recording evaluations."""

from pathlib import Path

import cv2
import numpy as np
import pytest

from backend.app.compiler import SemanticCompiler


def graph():
    return SemanticCompiler().compile(
        "Move the blue block into the visible marked region before moving the cup into that region."
    )


def test_normalized_selection_rejects_out_of_bounds():
    from backend.app.perception import Box

    with pytest.raises(ValueError):
        Box(x=0.9, y=0.1, width=0.2, height=0.1)
    with pytest.raises(ValueError):
        Box(x=float("nan"), y=0.1, width=0.2, height=0.1)


def video(path: Path, reverse=False, occluded=False):
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 24, (320, 180))
    for i in range(144):
        frame = np.full((180, 320, 3), 220, dtype=np.uint8)
        # Distinct saturated objects move in separate lanes to a common region.
        bx = min(220, 20 + max(0, i - (75 if reverse else 20)) * 10)
        cx = min(220, 20 + max(0, i - (20 if reverse else 75)) * 10)
        if not (occluded and 30 <= i < 45):
            cv2.rectangle(frame, (bx, 30), (bx + 24, 54), (255, 0, 0), -1)
        cv2.rectangle(frame, (cx, 100), (cx + 24, 124), (0, 0, 255), -1)
        writer.write(frame)
    writer.release()


def initialization(g, reference):
    from backend.app.perception import Box, Initialization

    # IDs come from the compiler, not a hand-authored parallel semantic graph.
    objects = {}
    for obj in g.objects:
        y = 29 / 180 if "block" in obj.label.lower() else 99 / 180
        objects[obj.id] = Box(x=19 / 320, y=y, width=27 / 320, height=27 / 180)
    return Initialization(
        frame_reference=reference,
        objects=objects,
        regions={r.id: Box(x=0.6, y=0.05, width=0.35, height=0.85) for r in g.regions},
    )


@pytest.mark.parametrize("reverse,expected", [(False, "PASS"), (True, "FAIL")])
def test_decoded_pixels_establish_temporal_order(tmp_path, reverse, expected):
    from backend.app.evaluator import evaluate
    from backend.app.perception import LocalCVTracker, LocalRegionObserver, inspect_video

    path = tmp_path / "generated.mp4"
    video(path, reverse=reverse)
    g = graph()
    metadata = inspect_video(path)
    init = initialization(g, metadata["frame_reference"])
    tracks = LocalCVTracker(init).track(path, g)
    observations = LocalRegionObserver(init).observe(path, g, tracks)
    assert evaluate(g, observations, metadata["duration_s"]).verdict == expected
    assert all(t.samples[0].frame_index == 0 and t.samples[-1].frame_index == 143 for t in tracks)
    assert all(o.evidence.frame_indices for o in observations)
    assert all(o.confidence != 0.99 for o in observations)


def test_loss_never_recovers_identity_or_proves_order(tmp_path):
    from backend.app.evaluator import evaluate
    from backend.app.perception import LocalCVTracker, LocalRegionObserver, inspect_video

    path = tmp_path / "occlusion.mp4"
    video(path, occluded=True)
    g = graph()
    metadata = inspect_video(path)
    init = initialization(g, metadata["frame_reference"])
    tracks = LocalCVTracker(init).track(path, g)
    observations = LocalRegionObserver(init).observe(path, g, tracks)
    assert evaluate(g, observations, metadata["duration_s"]).verdict == "UNKNOWN"
    damaged = next(t for t in tracks if t.invalid_intervals)
    first_loss = next(i for i, s in enumerate(damaged.samples) if s.status != "reliable")
    assert all(s.status != "reliable" for s in damaged.samples[first_loss:])


def test_truncated_provider_tracks_cannot_prove_unique_entry(tmp_path):
    from backend.app.evaluator import evaluate
    from backend.app.perception import LocalCVTracker, LocalRegionObserver, inspect_video

    path = tmp_path / "generated.mp4"
    video(path)
    g = graph()
    metadata = inspect_video(path)
    init = initialization(g, metadata["frame_reference"])
    tracks = LocalCVTracker(init).track(path, g)
    tracks[0].samples = tracks[0].samples[:-2]
    observed = LocalRegionObserver(init).observe(path, g, tracks)
    assert evaluate(g, observed, metadata["duration_s"]).verdict == "UNKNOWN"


def event_graph():
    return SemanticCompiler().compile(
        "The blue block enters the visible image region target before "
        "the cup enters the visible image region target."
    )


def overlap_track(values, gap_at=None):
    from backend.app.perception import VisualSample, VisualTrack

    return VisualTrack(
        object_id="object1",
        samples=[
            VisualSample(
                frame_index=i * 2,
                time_s=i / 12 + (0.25 if gap_at is not None and i >= gap_at else 0),
                status="reliable",
                confidence=0.9,
                region_overlap={"region1": value},
            )
            for i, value in enumerate(values)
        ],
    )


def transitions(values, gap_at=None):
    from backend.app.perception import LocalRegionObserver

    g = event_graph()
    init = initialization(g, "unit-first-frame")
    return LocalRegionObserver(init)._transitions(overlap_track(values, gap_at), "region1", g)


def test_hysteresis_uses_mask_stable_runs_and_uncertainty_bounds():
    observed = transitions([0.0] * 5 + [0.5, 0.8] + [1.0] * 5)
    assert len(observed) == 1
    assert observed[0].start_s == 4 / 12
    assert observed[0].end_s == 7 / 12
    assert observed[0].frame_indices == list(range(4, 20, 2))
    assert observed[0].usable


def test_initial_inside_and_boundary_flicker_do_not_invent_entry():
    assert transitions([1.0] * 12) == []
    assert transitions([0.0] * 5 + [1.0, 0.5, 1.0, 0.4, 1.0, 0.5]) == []


def test_repeated_entries_and_unmatched_exit_remain_in_audit():
    observed = transitions([0.0] * 4 + [1.0] * 4 + [0.0] * 4 + [1.0] * 4)
    assert [o.predicate.type for o in observed] == [
        "object_entered_region",
        "object_exited_region",
        "object_entered_region",
    ]
    assert observed[1].event_id.startswith("unmatched_")
    assert observed[0].event_id == observed[2].event_id == "event1"


def test_sampling_gap_makes_raw_events_unusable():
    observed = transitions([0.0] * 4 + [1.0] * 4 + [0.0] * 4, gap_at=8)
    assert observed and all(not o.usable for o in observed)


@pytest.mark.parametrize("overlap", [None, float("nan"), -0.1, 1.1])
def test_incomplete_geometry_cannot_hide_repeated_occurrences(overlap):
    from backend.app.perception import LocalRegionObserver

    g = event_graph()
    track = overlap_track([0.0] * 4 + [1.0] * 4 + [0.0] * 4 + [1.0] * 4)
    if overlap is None:
        track.samples[10].region_overlap.clear()
    else:
        track.samples[10].region_overlap["region1"] = overlap
    observer = LocalRegionObserver(initialization(g, "reference"))
    observations = observer._transitions(track, "region1", g)
    assert observations and all(not o.usable for o in observations)


def test_long_boundary_dwell_is_not_decisive():
    observed = transitions([0.0] * 4 + [0.5] * 30 + [1.0] * 4)
    assert observed and not observed[0].usable


def test_unresolved_long_boundary_dwell_invalidates_earlier_unique_occurrence():
    observed = transitions([0.0] * 4 + [1.0] * 4 + [0.5] * 30)
    assert observed and not observed[0].usable


def test_selection_requires_exact_ids_frame_and_nonoverlap():
    from backend.app.perception import validate_selection

    g = event_graph()
    init = initialization(g, "reference")
    validate_selection(init, g, "reference")
    with pytest.raises(ValueError, match="immutable"):
        validate_selection(init, g, "other")
    init.objects["object2"] = init.objects["object1"]
    with pytest.raises(ValueError, match="overlap"):
        validate_selection(init, g, "reference")
    del init.objects["object2"]
    with pytest.raises(ValueError, match="each compiled object"):
        validate_selection(init, g, "reference")


def test_competing_color_components_invalidate_identity(tmp_path):
    from backend.app.perception import LocalCVTracker, inspect_video

    path = tmp_path / "duplicate.mp4"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 24, (320, 180))
    for _ in range(24):
        frame = np.full((180, 320, 3), 220, dtype=np.uint8)
        cv2.rectangle(frame, (20, 30), (44, 54), (255, 0, 0), -1)
        cv2.rectangle(frame, (150, 30), (174, 54), (255, 0, 0), -1)
        cv2.rectangle(frame, (20, 100), (44, 124), (0, 0, 255), -1)
        writer.write(frame)
    writer.release()
    g = event_graph()
    init = initialization(g, inspect_video(path)["frame_reference"])
    tracks = LocalCVTracker(init).track(path, g)
    assert tracks[0].invalid_intervals
    assert all(s.box is None for s in tracks[0].samples)


def test_scene_motion_invalidates_static_camera_assumption(tmp_path):
    from backend.app.perception import LocalCVTracker, inspect_video

    path = tmp_path / "scene.mp4"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 24, (320, 180))
    for i in range(24):
        frame = np.full((180, 320, 3), 220 if i < 8 else 100, dtype=np.uint8)
        cv2.rectangle(frame, (20, 30), (44, 54), (255, 0, 0), -1)
        cv2.rectangle(frame, (20, 100), (44, 124), (0, 0, 255), -1)
        writer.write(frame)
    writer.release()
    g = event_graph()
    init = initialization(g, inspect_video(path)["frame_reference"])
    tracks = LocalCVTracker(init).track(path, g)
    assert all(t.invalid_intervals for t in tracks)
    assert all("Scene motion" in t.invalid_intervals[0]["reason"] for t in tracks)
