# Readiness verification — October 29, 2026

Runtime baseline: `cafb74c2485fe1637f9434b43e5b68a50d5de3c3`. This delivery changes documentation and generated audit assets, not application behavior, thresholds, dependencies or configuration.

| Check | Actual result |
|---|---|
| `uv run --offline pytest --basetemp .pytest-tmp -q` | 357 passed in 105.88 s; existing Starlette/httpx deprecation warning |
| `uv run --offline ruff check .` | Passed |
| `uv run --offline ruff format --check .` | Passed; 110 files |
| `uv run --offline mypy` | Passed; 36 source files |
| `npm --prefix frontend test` | 23 passed; four files |
| Frontend lint / typecheck / build | All passed |
| `uv lock --check --offline` | Passed; 39 packages |
| `npm --prefix frontend audit --audit-level=high` | Zero vulnerabilities |
| `uv run --offline python -m scripts.replay_milestone5` | All 17 response hashes and captured deterministic results verified; no new inference |
| Three fresh loopback uploads | Real local-CV PASS / FAIL / UNKNOWN, actual source SHA-256 and evidence frames verified |
| Browser inspection | Three results, timestamp seeking, tracking diagnostics, source inspection; independently entered FAIL/UNKNOWN revisions and matching fingerprint |
| Immutability | Entire original job JSON and first evaluation unchanged for each clip after browser actions; all earlier revisions retained |
| Ledger | Entire existing cost table unchanged; [private ledger total] micro-USD lifetime exposure; new isolated ledger zero |
| Delivery ZIP | Five expected entries; CRC, extraction and every hash passed; Downloads copies match |
| Demo | Existing SHA-256 matches; full audio/video decode passed; 11 fresh chapter samples inspected; Chrome played through to 145.621 s, 1920×1080, no media error |
| Public source | Rebuilt with explicit exclusions, credential scans, entry hashes and extraction validation; see current source manifest |
| Extracted-source reproduction | Offline replay verified 17 captures; packaged synthetic MP4s reproduced PASS / FAIL / UNKNOWN through the upload harness with zero Meta calls. Used the existing locked dependency environment; no fresh dependency installation is claimed. |

`UV_CACHE_DIR` was set to the repository's ignored `.uv-cache` for these commands.
The initial default-cache attempts failed on sandbox cache writes; using the permitted
workspace cache resolved them without a dependency install or persistent configuration change.

## Hosted CI

Authenticated GitHub verified [run 40874811113](https://github.com/mattwatson7/reality-compiler/actions/runs/40874811113)
for the exact baseline commit: **success**. Job `verify` passed backend/frontend checks,
offline replay, dependency audit, actual Docker build and the paid-disabled running-container
integration smoke. The subsequent local documentation/package changes have not been pushed,
so no hosted run for the local delivery commit is claimed. Runtime files match the checked baseline.
PR #2 and PR #3 were both open and unmerged when inspected.

## Limits and integrations

Full end-to-end UI uploads remain **unverified**: the Chrome extension requires local-file
access permission; its native fallback did not provide usable input geometry. No permission
was changed. Real HTTP uploads plus actual Chrome inspection are documented separately in
[the audit](synthetic-validation.json). One large screenshot timed out; viewport screenshots
were retained. Direct range filling did not seek; actual keyboard seek/source mappings were
used. These browser-control limitations are not hidden by the API success.

Material external integrations: authenticated **GitHub connector** (repository privacy,
PR status and CI step results), authenticated **Chrome browser connector** (submission form,
official rules and local application/video checks), and official **Meta event web page**
(deadline). No fresh Meta API or model-catalog request was needed; account entitlement is
historical, not reverified. No OpenAI API development was undertaken. Local FFmpeg/OpenCV
performed media checks. Local `gh` authentication is not established; public hosting URLs
do not yet exist. No additional plugin or dependency was installed.

The source and film remain prepared for review. Publication, external video upload, consent,
submission and merging were not performed. Controlled physical-camera acceptance remains
unverified and is not required for the truthful synthetic demonstration described here.
