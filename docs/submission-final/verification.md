# Final verification report

October 28, 2026. Continued the existing branch from `31c9d9fcf9406d073df379ffa2da1f21b138a851` and preserved prior captures, results and ledger. No architectural milestone was added.

## Delivered behavior

Captured-evidence review now explains Wonder's original requirements, SAM tracks, deterministic judgment and local revision compilation near the top of the page. Spark's separate role and absence from this order comparison are explicit. Matching fingerprints are visible above side-by-side verdicts only when the selected revision actually reused the same evidence. Provider provenance appears beside each result. The isolated review ledger is labeled to avoid confusing it with lifetime spending.

The actual film was produced with installed tools, exported, fully decoded and independently opened in Chromium for playback and seeking. All eleven chapter samples were visually inspected; readable full-size comparison/source frames were checked. [Video manifest](video-manifest.json) records exact bytes, SHA-256, measured track/container durations and browser results. The narration is synthetic local speech. One historical selection still is explicitly labeled; all other chapters use genuine application recordings with editorial cuts. No invented model activity or verdict is present.

## Checks

| Check | Result |
|---|---|
| `uv run pytest --basetemp .pytest-tmp -q` | 357 passed; one existing Starlette/httpx TestClient deprecation warning |
| Ruff lint and format | Passed |
| `uv run mypy` | Passed, 34 source files |
| `uv lock --check` | Passed |
| `npm --prefix frontend test` | 23 passed, including reuse match/mismatch and new-analysis cases |
| Frontend lint, TypeScript, production build | Passed |
| npm audit | Zero vulnerabilities |
| Offline replay | All 17 response hashes verified; historical deterministic results reproduced; zero new network calls |
| Fresh generated-input browser recording | Actual original PASS; newly typed FAIL and UNKNOWN; empty new inference usage; matching fingerprints; original unchanged |
| Playback, overlays, evidence navigation | Real clip played; timestamp seek and supporting frames inspected |
| New generated local-CV upload | Real frame-zero boxes; PASS; original decoded source frame 50 inspected through source map; no SAM |
| Responsive comparison | 390×844 viewport, no horizontal overflow; [mobile screenshot](screenshots/mobile-comparison.jpg) |
| Clean source setup | New directory with no `.env`, database or dependencies; locked uv sync, npm ci/build, hash replay and capture import passed |
| Clean real-browser reproduction | PASS/FAIL/UNKNOWN, empty revision usage, playback, reload and six-entry history verified; isolated ledger zero |
| Restart persistence | All six evaluation IDs and fingerprints preserved after stopping and starting the clean server process |
| Extended loopback smoke | Served built frontend, fixture PASS/FAIL, normalization/source PNG, unsupported UNKNOWN and zero cost passed |
| Local Docker engine | Unavailable: Docker Desktop Linux engine pipe absent; no local Docker success claimed |
| Final hosted Docker/CI | Exact final head result is reported in [PR #3](https://github.com/mattwatson7/reality-compiler/pull/3) and the final handoff after push; [current checks](https://github.com/mattwatson7/reality-compiler/pull/3/checks) |

The clean reproduction used a sanitized candidate source snapshot with its own virtual environment and npm install. Runtime source hashes are retained in [source package manifest](source-package-manifest.json); final packaging compares them to that tested snapshot. Later reporting changes do not alter tested runtime code. The local source-only ZIP and film stay excluded from Git until separate publication/hosting authorization.

An independent read-only review found a production-tool guard gap: the source-inspection run could have been mislabeled if a different run ID was supplied. The recorder now checks completed status, generated origin, local-CV mode, no inference usage and the exact known generated-source hash before filming. The actual exported source run satisfies every guard. No application regression or false current verdict was identified.

The authenticated submission form **was inspected**. It asks for Public GitHub Repository, 3-Minute Demo Video link, team/track/theme, project and Meta answers, feedback and publication consent. No HTML length limits were declared, and hidden/server limits remain unverified. No deployed-app field was present. The current private repository does not meet the public field without a publication decision. [Exact portal findings](portal-requirements.md) replace the prior signed-out limitation.

Lifetime exposure remains [private historical cost], both paid gates false, new paid requests zero. Controlled physical-camera recordings remain absent. The [human-action checklist](human-actions.md) distinguishes publication, video hosting, eligibility/terms and final submission from the completed reversible work.

Material integrations and scoped security/rights checks are recorded in [security-rights.md](security-rights.md). No new dependencies, paid calls, deployment, hackathon submission, visibility change or PR merge occurred.
