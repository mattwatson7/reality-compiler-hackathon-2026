# Verification — October 29, 2026

Fresh checks on the existing runtime plus documentation supplement:

| Check | Result |
|---|---|
| Backend pytest | 357 pass; one existing Starlette/httpx deprecation warning |
| Ruff lint / format | Pass; 102 files formatted |
| mypy | Pass; 34 source files |
| uv lock --check | Pass; 39 packages resolved |
| Frontend tests | 23 pass, 4 files |
| Frontend lint / typecheck / build | Pass |
| Offline replay | 17 response hashes verified; historical results reproduced; no network calls |
| Four original camera files | Full decode and hashes match historical inventory |
| Film / ZIP | Manifest hashes match; ZIP CRC passes; runtime hash mismatches zero |
| Ledger / gates | Read-only query: [private ledger total] micro-USD, 63 reservations; both gates false |
| Existing cube ingestion | New offline preparation succeeds; original bytes unchanged |
| New source mapping | 258 normalized frames map to original PTS; index 257 → source index 321, PTS 164352, source time 10.7 s |

The preparation smoke used only existing `recordings/external/cam1.mp4`, writing
ignored `output/m53-existing-cube-preflight/`. It invoked no compiler, tracker,
model or evaluation. Its normalized duration is 10.75 s at 24 fps; original remains
10.766667 s at 30 fps. Metadata, frame zero and `video.timing.json` are available
locally. The new map does not retrofit older captured runs or establish camera
authenticity. No actual verdict was generated or expected label changed.

External integrations: authenticated GitHub PR read (open/unmerged/base head),
Hugging Face dataset metadata/license read, web research of original publishers.
Official waiver re-read failed through web; earlier authenticated form findings
remain dated October 28. No new credit-balance verification, Docker run, portal
submission, host upload, external communication or publication occurred.

The preserved source ZIP remains the tested 5.2 snapshot. New documentation and
the landing-page pointer are outside that unchanged archive; publish this supplement
alongside it if desired. Source-file pattern scans from 5.2 are not represented as
a fresh exhaustive secret scan. No application code or dependency changed.
