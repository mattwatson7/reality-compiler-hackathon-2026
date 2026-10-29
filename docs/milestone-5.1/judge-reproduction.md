# Judge reproduction without Meta credentials

This walkthrough uses existing generated media and actual captured Meta responses. It creates a new **offline capture review** run. New revisions compile with local controlled-language rules. It performs no new Meta inference and does not establish new camera validation.

Prerequisites: an existing compatible Python/uv, Node/npm and ffmpeg installation; repository checkout with committed generated media and capture JSON. No new plugin or global configuration is required. Dependency installation requires normal registry access. Run from repository root in PowerShell.

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
# Choose a new directory; never delete or reset the project's existing data/ledger.
$reviewDir = Join-Path (Get-Location) ('output/judge-review-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
$env:DATA_DIR = $reviewDir
uv run python -m scripts.replay_milestone5
uv run python -m scripts.open_capture_review --data-dir $reviewDir
uv run uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000` followed by the importer's printed `/?run=...` path. The server uses the same isolated data directory as the importer. A new isolated ledger is not the lifetime spending ledger: its zero usage must never be described as the project's total spend. The existing project ledger is left untouched at [private historical cost] committed exposure.

Check the generated/offline labels and provider provenance. Inspect the original PASS, supporting event intervals and tracking overlays. Enter the reversed procedure from [the demo sequence](demo-production.md) and compare FAIL. Enter the original order plus sterility and inspect UNKNOWN. Make another supported wording edit yourself; the local compiler independently compiles it. Incompatible objects, regions, predicates or scope must be rejected rather than silently reusing evidence.

The replay command checks all 17 response digests and recomputes deterministic results. The importer separately checks source and normalized generated-media hashes and preserves captured provenance. Use the displayed evidence IDs/times, not a pretyped substitute. Reload the page or restart the same server with the same `DATA_DIR` to verify retained history while media remains within its normal lifetime.

Playback expires under normal retention. Do not extend an expired old job or bypass access controls. If a fresh review is needed, run the importer again against the isolated directory to create a new review run from verified committed captures. Stop the loopback server when done. Keep the local output directory untracked.

Cross-platform equivalent: set the same process environment variables with your shell's syntax and use a new local data directory. Commands otherwise use the same Python modules, npm scripts and loopback server. This guide does not run the paid smoke scripts.

If hash verification fails, stop and report the named asset. If dependencies/ffmpeg are unavailable, report the missing prerequisite; do not claim a working browser reproduction. The isolated demo is not a public deployment, and no Meta credentials are required.
