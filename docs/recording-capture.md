# Capture and evaluate three genuine recordings

No genuine recordings are bundled. The two fixture animations and generated test
clips are synthetic algorithm tests, never real-world validation. Provenance in
the harness is a human attestation; it cannot authenticate an arbitrary video.

Use a tripod or fixed overhead mount, a plain table, a blue block and a cup with
a distinctly different saturated color (red is suitable). Avoid blue/red clothing,
reflections, shadows, matching props and exposure changes. Mark a rectangular
target with neutral tape. Keep both objects completely visible in separate lanes,
outside the target initially. A white/transparent cup is unsuitable for this HSV
baseline. Objects must retain roughly the same visible size and shape.

Record three **held-out** clips, each 10–30 seconds and under 100 MB:

1. `correct`: hold still for one second, slide the block into the target, pause
   at least one second, slide the cup into the target. Hold both visibly inside
   for one second before stopping. Expected **PASS**.
2. `reverse`: repeat with cup first, block second. Expected **FAIL**.
3. `occlusion`: hide the block with a hand near the target boundary during its
   move, then reveal it and move the cup. Expected **UNKNOWN**. Do not supply
   manual recovery or event times.

Do not move the camera, lift/rotate objects, edit timing, or crop between actions.
The coarse scene-motion guard rejects substantial background changes, but sparse
camera motion can escape it. A fixed camera is an input assumption, not a verified
physical fact. Scores are heuristics, not calibrated probabilities. A region entry
proves only visible image geometry, never physical insertion/containment.

## Prepare and annotate

From the repository root, prepare each camera file in a **new** output directory:

```powershell
uv run python -m scripts.evaluate_recordings --prepare recordings/correct.mov --output output/correct-prepared
uv run python -m scripts.evaluate_recordings --prepare recordings/reverse.mov --output output/reverse-prepared
uv run python -m scripts.evaluate_recordings --prepare recordings/occlusion.mov --output output/occlusion-prepared
```

This validates and normalizes to 24 fps within 1280×720, writes `video.mp4`,
`frame-0.jpg`, and `prepare.json` with source/normalized SHA-256 and immutable
first-frame reference. Preparation itself does not establish real-world success.
Do not annotate the original camera frame: rotation and dimensions may change.

Copy `docs/recordings.example.json` to `recordings/manifest.json`. Keep the exact
procedure. For each prepared clip add an entry like the following. Replace both
hashes, paths, capture time, description, and **all** example boxes with measurements
from your own first normalized frame. IDs `object1`, `object2`, `region1` come from
compiling the exact procedure (blue block, cup, marked region respectively).

```json
{
  "id": "correct",
  "file": "correct.mov",
  "source_sha256": "COPY_FROM_PREPARE_JSON",
  "normalized_file": "../output/correct-prepared/video.mp4",
  "normalized_sha256": "COPY_FROM_PREPARE_JSON",
  "expected_verdict": "PASS",
  "provenance": {
    "kind": "genuine_recording",
    "captured_at": "2026-10-27T19:00:00+07:00",
    "description": "Held-out physical camera recording; identify operator and setup"
  },
  "initialization": {
    "objects": {
      "object1": {"x": 0.05, "y": 0.15, "width": 0.1, "height": 0.15},
      "object2": {"x": 0.05, "y": 0.6, "width": 0.1, "height": 0.15}
    },
    "regions": {
      "region1": {"x": 0.6, "y": 0.05, "width": 0.35, "height": 0.85}
    }
  }
}
```

Coordinates are top-left `x/frame_width`, `y/frame_height`,
`width/frame_width`, `height/frame_height`. Tight object boxes must not overlap;
boxes must be finite and remain inside the frame. No timestamps belong in the
manifest. The studio's first-frame rectangle workflow can also be used to obtain
normalized boxes: inspect the resulting job JSON's `initialization`.

## Run and inspect

```powershell
uv run python -m scripts.evaluate_recordings --manifest recordings/manifest.json --output output/real-evaluation
```

The harness runs the application's compiler, tracker, observer and evaluator,
retains normalized playback and supporting JPEGs, and writes `report.json` plus
per-record results, raw candidates, sample quality, invalid intervals and hashes.
It checks hashes against preparation before trusting annotation. Known bundled
fixture hashes are refused as genuine recordings.

Exit 0 means all three expected verdicts matched on attested recordings. Exit 1
means a mismatch/error; exit 2 means inputs or outcome coverage are incomplete.
An empty manifest explicitly reports zero recordings and `unverified`. Review
every verdict against its actual frames; a matched manifest is not a substitute
for checking what was recorded. Store private recordings outside Git and share
only deliberately reviewed artifacts. No keys, SAM, GPU, downloads or paid calls
are required.
