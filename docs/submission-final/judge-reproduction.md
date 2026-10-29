# Reproduce the demonstrated product

**Generated input. Actual captured Meta evidence. New instructions compile locally. No new paid inference.**

Use the submitted source archive or the approved repository/branch. Requirements: Python 3.12, uv, Node 22.12+ and npm; FFmpeg is already supplied by the Python dependency. Registry access is needed to install locked dependencies. No Meta key, account or model download is needed. The source package does not contain a populated database or private camera footage.

From a new checkout in PowerShell:

```powershell
$env:UV_CACHE_DIR = Join-Path (Get-Location) '.uv-cache'
uv sync --locked
npm --prefix frontend ci
npm --prefix frontend run build
$env:META_ENABLE_PAID_INFERENCE = 'false'
$env:META_SMOKE_TEST_APPROVED = 'false'
$env:META_COMPILER = 'local_rules'
$env:META_SPARK_VISUAL = 'false'
$env:PROVIDER_MODE = 'fixture'
$env:DATA_DIR = Join-Path (Get-Location) ('output/judge-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
uv run python -m scripts.replay_milestone5
uv run python -m scripts.open_capture_review --data-dir $env:DATA_DIR
uv run uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000` followed by the importer's printed `/?run=...` path. Keep that server and data directory for the walkthrough. A fresh isolated ledger contains zero spend; it is **not** the lifetime project ledger, whose exposure remains [private historical cost]. Never delete or reset an existing project database to run this demo.

1. Confirm generated/offline labels. Original **PASS** comes from prior Wonder compilation and captured SAM tracks. Expand the verification program to inspect object references, typed region-entry events, source quotes and the explicit BEFORE edge.
2. Play the video and watch overlays. Seek the two supporting intervals, **0.750–1.125s** and **2.167–2.583s**, and open saved supporting frames. Their IDs are `cv_object1_region1_20_23_0` and `cv_object2_region1_54_58_0`. The historical capture has no original-source mapping; the interface says so.
3. Enter this **new** text under Revised procedure, then click Evaluate same evidence:

   `Move the cup into the visible marked region before moving the blue block into that region.`

   Compare the original with the newly appended **FAIL**. The opposite order is proven; both individual entries remain supported. Inspect matching fingerprints and separate compiler/tracker/observer provenance.
4. Enter another new procedure:

   `Move the blue block into the visible marked region before moving the cup into that region. Ensure the cup is sterile.`

   The new result is **UNKNOWN**: ordering passes, sterility remains explicitly unsupported. Earlier evaluations persist. Imported historical comparisons also appear in the list; the new browser actions append independent results.
5. Reload and restart the same server using the same `DATA_DIR`. The job and appended history remain. Video expires normally after one hour; for a later session create a fresh labeled import, rather than extending old playback.

To inspect **new-upload source mapping**, open a separate application tab, upload `docs/live-validation/live-api-v6-correct/source.mp4`, choose Generated demonstration and Local OpenCV, and use the supported original wording. Draw tight boxes around the blue block, green cup and outlined region in normalized frame zero, then start tracking. This separate run performs local CV on pixels, uses **no SAM**, and is not physical-camera validation. Seek near 2.1s, open Inspect original source frame and click Inspect source at playhead. Normalized frame 50 maps to original decoded frame 50, PTS 25600 × 1/12288. The returned PNG is 320×180. No mapping is grafted onto the old Meta capture.

The [browser export](browser-verification.json), [new local-CV upload](local-cv-upload.json), [screenshots](screenshots/comparison.jpg) and [video manifest](video-manifest.json) document the actual production run. Capture/model IDs are audit identities, not credentials. Semantic objects, regions, predicates and scope must remain compatible; changed identities require a new analysis instead of silently reusing evidence.

Optional full checks: use the commands in [README validation](../../README.md#validation). `uv run python -m scripts.docker_smoke --base-url http://127.0.0.1:8000` runs the offline integration smoke against a fresh zero-cost server. Docker users can use `docker compose up --build` with paid gates disabled; keep the volume. One server process only.

Shells other than PowerShell should set equivalent process environment variables. Stop the loopback server when finished. A hash mismatch, absent dependency or unexpected result is a failed reproduction, not grounds to substitute a predetermined verdict.

For three **separate** synthetic-video local-CV runs, use the inputs included in the
sanitized source bundle at `docs/submission-final/synthetic-videos/`, or regenerate
them with `uv run python -m scripts.generate_synthetic_trio`. Follow the
[exact procedure, first-frame boxes, expected results and API runner](synthetic-validation.md).
This supplement verifies positive reversed-order observations and conservative scene-motion
invalidation. It is independent of the captured Wonder/SAM walkthrough and makes no new
model requests. Current browser testing inspected API-created runs and UI revisions;
the extension blocked file uploads, so three end-to-end UI uploads are not claimed.
