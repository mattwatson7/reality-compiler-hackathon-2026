# Verification — October 29, 2026

All commands ran from the repository root with the existing locked environment.
`UV_CACHE_DIR` was set to the ignored workspace `.uv-cache` because the sandbox's
default cache location denied writes. No dependency installation or persistent
global configuration change was needed.

| Check | Result |
| --- | --- |
| `uv run python -m scripts.generate_synthetic_trio` | Three files generated; regenerated hashes identical after formatting |
| `uv run python -m scripts.evaluate_synthetic_trio` | All media, API, provenance, sample, evidence and ledger assertions passed; actual PASS / FAIL / UNKNOWN |
| `uv run pytest --basetemp .pytest-tmp -q` | 357 passed in 322.14 seconds |
| `uv run ruff check .` | Passed |
| `uv run ruff format --check .` | Passed, 110 files |
| `uv run mypy` | Passed, 36 source files |
| `npm --prefix frontend test` | 23 passed, four test files |
| `npm --prefix frontend run lint` | Passed |
| `npm --prefix frontend run typecheck` | Passed |
| `npm --prefix frontend run build` | Passed |
| `git diff --check` | Passed |
| Existing submission demo SHA-256 | Matches `video-manifest.json`: `d83ed0ade7c63427dff898d297a5e86465d8265ce0c2a8c8b75ac8e139a69e5b` |
| Existing documentation preservation | No diff in `docs/submission-final/` or `docs/milestone-5.3/` against local starting commit `fb7450d` |

The backend/test runner emits one existing Starlette deprecation warning about
its httpx TestClient integration. It is not a failed check; no dependency change
was made in response.

The supplied generator initially failed Ruff line-length and formatting checks.
Only its formatting was changed. The new synthetic-specific runner validates
real API behavior and writes fresh isolated run artifacts; no tracker, observer,
compiler, evaluator or application threshold was changed.

Detailed local run artifacts are under
`output/synthetic-trio/1793277159611904500/` (ignored). The complete job JSON
hashes and a portable evidence summary are preserved in [audit.json](audit.json).
Visual review used source frames at 0, 4, 9 and 14.966667 seconds for every clip,
plus normalized tracking overlays around each crossing and frames 64/66 across
the occlusion guard transition. These images are local ignored inspection aids.

The synthetic runner explicitly prevents Meta transport, verifies zero calls,
and uses a separate SQLite database. Its ledger is zero; the existing application
ledger remains unchanged at 63 rows / [private ledger total] micro-USD exposure. Configured
`META_ENABLE_PAID_INFERENCE` and `META_SMOKE_TEST_APPROVED` were checked false
without displaying credentials. This is no-cost local OpenCV validation, not
live Meta validation or genuine physical-camera acceptance.

GitHub connector PR metadata and Git fetch were the only material external
integrations. The first Git fetch was denied write access to `.git/FETCH_HEAD`;
the scoped Git escalation succeeded. No unresolved connector limitation prevented
this task. PR #3 remains unmerged.
