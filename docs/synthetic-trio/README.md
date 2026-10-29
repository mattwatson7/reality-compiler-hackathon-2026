# Synthetic trio: no-cost local pipeline validation

Evaluated on October 29, 2026 (Asia/Bangkok). These inputs are generated graphics,
not physical-camera recordings. Genuine-camera validation remains **unverified**.
Nothing was placed in `recordings/controlled/` or added to camera acceptance data.

Generator commit `36d4095` was merged into the local
`milestone-4-meta-integration` branch without discarding the two local camera-review
documentation commits. Existing demo and submission materials were preserved.

## Actual results

One procedure was used unchanged for all three uploads:

> Move the blue block into the visible marked region before moving the cup into that region.

| Input | Actual evaluator result | Observed transition intervals, normalized seconds |
| --- | --- | --- |
| `correct.mp4` | PASS | Block 4.166667–4.500000; cup 9.000000–9.250000 |
| `reverse.mp4` | FAIL | Cup 4.000000–4.250000; block 9.166667–9.500000 |
| `occlusion.mp4` | UNKNOWN | No usable crossings; both identities invalidated from 2.750000 to 15.000000 |

The first two runs confirm both typed region-entry predicates. The evaluator
proves the requested order in the first run and its reverse in the second. Each
decisive check cites actual saved evidence IDs and timestamp ranges; the wider
supporting evidence intervals are retained separately in [audit.json](audit.json).
Region entry describes image overlap, not physical containment or insertion.

Both objects retain all 181 reliable samples in the first two clips: frame 0,
every second normalized frame through 358, then frame 359. `object1` is the blue
block; `object2` is the yellow cup; `region1` is the visible outlined target.
Selections are fixed boxes drawn from frame zero, identical across cases, bound
to each normalized video's hash and compiled IDs. No event times, identity
recovery, fixture observations or hand-authored semantic graphs were supplied.

The occlusion run has 33 reliable, one ambiguous and 147 missing samples **per
object**. The large moving gray card triggers the coarse scene-motion guard at
2.75 seconds, before the block is fully covered. Both tracks are then invalidated
for the rest of the clip, including the cup that remains visible. This is the
current conservative scene-motion limitation, not proof that the camera moved
and not a demonstration of isolated object-occlusion handling. No guard or
threshold was weakened to obtain a verdict. No application correctness defect
was established by this trio.

## Media and pipeline checks

All three required files exist in ignored `recordings/synthetic/`. Each source
fully decodes to **450 frames, 15 seconds, 1280×720, 30 fps, H.264**. Both OpenCV
and a full FFmpeg `-xerror` decode succeeded. SHA-256 values are in the audit.
Formatting the supplied generator reproduced byte-identical videos.

The runner exercises the actual FastAPI upload, asynchronous job processing,
immutable-frame initialization and evidence-serving routes using TestClient.
The application normalizes each source to 360 frames at 24 fps, tracks pixels
at 12 Hz including first/last frames, observes region overlap and invokes the
real deterministic evaluator. Source-frame/PTS mappings are checked against the
450-frame source inventory and 360-frame normalized inventory. Saved frames
referenced by every decisive evidence item are fetched through the API.

Compiler, tracker and observer provenance remain separate: `local_rules`,
`local_cv.fixed_hsv.v1`, and `mask_hysteresis.v1`. SAM and Muse were not used.
No UI/browser interaction is claimed by this API validation.

## Reproduce

From the repository root with the locked development dependencies already present:

```powershell
$env:UV_CACHE_DIR = Join-Path $PWD '.uv-cache'
uv run python -m scripts.generate_synthetic_trio
uv run python -m scripts.evaluate_synthetic_trio
```

The second command prints the actual verdicts and the path to a new report under
ignored `output/synthetic-trio/<run>/`. It retains complete job JSON, raw tracks,
observations, source timing, normalized videos, original uploads, supporting
frames and an isolated SQLite job database. It does not assert desired verdicts.
The API media lifetime is 24 hours; this runner does not launch a persistent
server. A new run never replaces an earlier report or the application database.

Both existing paid flags must be false. The runner also blocks Meta transport
and verifies that it was never invoked. It compares the existing default
application ledger rows read-only before/after and checks its separate job store
has zero cost/reservations. The existing ledger remains **63 entries with
[private ledger total] micro-USD ([private historical cost]) lifetime exposure**, including uncertain
reservations. No ledger reset or paid inference occurred.

GitHub's authenticated connector confirmed PR #3 is open and unmerged; Git fetch
retrieved the generator. There were no Meta service calls or new external model
claims. No deployment, permission change, external media upload or PR merge was
performed. Physical-camera acceptance remains outside what these synthetic
inputs can establish.

See [verification.md](verification.md) for repository checks.
