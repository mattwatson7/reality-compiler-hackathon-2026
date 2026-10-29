# Milestone 2: semantic compiler

Date: 2026-10-27 (Asia/Bangkok). Branch: `milestone-2-semantic-compiler`.
Base: milestone 1, commit `3a0cc49`. User approved the design and GitHub upload.

## Working features

- TaskGraph `2.0`: physical objects, visible regions, four typed predicates,
  stable references, source spans, required/optional events, during/final
  conditions, observability with reasons, BEFORE/AFTER and cycle validation.
- A real deterministic controlled-language semantic compiler, with a limited
  documented vocabulary. It preserves explicit ordering and unordered/optional
  instructions; unknown clauses remain unsupported. It does not infer list order.
- Exact-predicate deterministic evaluation, independent of any AI service. A step
  label/confidence alone cannot prove an event. Positive contradictions can fail;
  absence, overlaps, touching boundaries, repeated occurrences, conflicting
  observations and ambiguous grounding remain UNKNOWN. Final-state evidence must
  reach the clip end. Required unsupported requirements cannot pass.
- Optional-event ordering becomes conditional only when its optional endpoint is
  absent. Observed but ambiguous/repeated optional occurrences cannot bypass order.
- Unique cross-clause elliptical references reuse the earlier event. Multiple
  possible referents become an unsupported ambiguity, without arbitrary selection.
- Reviewed fixture migration with unchanged demo media, timings and verdicts.
  SHA-256 binds declarations to exact videos. Generic v1 migration is unsupported;
  v1 schemas, original snapshots and stored-audit UI rendering remain available.
- Semantic program panel with objects, regions, typed arguments, actual edges,
  required/optional conditions, final states, source quotes, observability and
  compilation source. Both real-Muse and real-video capabilities are labeled
  independently. Video seeking, playback, timeline and expiry are retained.
- Upload syntax validation is local. Each valid video is compiled once in its
  worker after media validation; no duplicate potential paid compilation occurs.

## Mocked, disabled and unavailable

Tracking and event recognition are still mocked. Demos use declared synthetic
observations. Uploads have no event evidence and return UNKNOWN even when the
uploaded bytes are a bundled demo. This is not a real-world video verifier.

The official public Muse Wonder API contract was readable and researched;
`docs/meta-api-contracts.md` records dated sources, availability, endpoint,
authentication, schema, usage, price and rate limits. No known server key is
configured in the process environment or a project `.env`. Account entitlement
and authenticated model access remain unverified. No paid inference, authenticated
Meta model request or smoke test was made. **Actual API spend: $0.**

`MuseWonderCompiler` implements the compiler interface only with a concrete
offline fixture transport. Default construction fails closed, and server config
accepts only fixture mode. The module has no HTTP client, key handling or live
transport. Synthetic HTTP response tests cover the documented envelope, strict
schema conversion, Pydantic graph validation, safe rejection and one repair limit.
They are not recorded live outputs or proof of working Muse access.

Offline contract tests exercise the existing atomic budget system in temporary
databases: verified integer upper bounds before each attempt, retained reservations
on uncertain/failed responses, and verified usage settlement including cache
discounts with integer upward rounding. Missing cache usage detail retains the
reservation. The real persistent application database was not reset. Before any
future live transport, verify account access, current prices and the full input
token bound including schema/prompt overhead; the local $100 ledger cannot
guarantee all Meta billing charges.

Source-span validation proves textual traceability, not general model semantic
faithfulness. The local grammar is deliberately narrow. A visible region crossing
does not prove physical containment, occlusion does not prove insertion, and hidden
charge, sterility or torque cannot be established. Plain closing and seal
application remain unsupported without explicit visible state-change criteria.
Repeated events have no first/last/count selector in this milestone; multiple
candidate occurrences are explicitly UNKNOWN.

No SAM, Muse Spark, public deployment, merge, permissions change or new dependency
is included. The unauthenticated upload application remains local, single-process
and intended for trusted recordings.

## Validation

All required local commands pass:

| Check | Result |
|---|---|
| `uv run pytest --basetemp .pytest-tmp -q` | 156 passed, one upstream Starlette/httpx deprecation warning |
| `uv run ruff check .` | Passed |
| `uv run ruff format --check .` | 34 Python files formatted |
| `uv run mypy` | Passed, 16 application/script modules |
| `npm --prefix frontend test` | 11 passed in two files |
| `npm --prefix frontend run lint` | Passed |
| `npm --prefix frontend run typecheck` | Passed |
| `npm --prefix frontend run build` | Passed |
| `npm --prefix frontend audit --audit-level=moderate` | Zero vulnerabilities |
| Fixture regeneration into an ignored temporary directory | Generated videos load with verified SHA; correct PASS, incorrect FAIL |
| Local `docker build -t reality-compiler:milestone-2 .` | Unavailable: Docker Desktop Linux engine pipe missing |

Initially `uv` could not write its default sandbox cache. The required `uv run`
commands succeed with a process-local `UV_CACHE_DIR` under `.test-tmp/uv-cache`.
No persistent global settings were changed. Docker build was attempted with normal
local configuration as well; its missing engine is independent of sandbox cache
permissions. The existing GitHub workflow includes Linux Docker build verification.

Browser checks against the locally built app confirm correct PASS, incorrect FAIL,
seeking the cup evidence to 3 seconds, independent inactive capability labels,
semantic object/event/constraint rendering and no invented adjacency arrows. A
local screenshot is saved under ignored
`output/playwright/milestone-2-program.png`. API/media tests additionally verify
upload UNKNOWN, video range requests, expiry, source cleanup and compile-once.

Independent specification review found optional-order and elliptical-reference
bugs; both received failing regression tests and fixes. Re-review confirmed both
fixes, and a separate code-quality/security review found no actionable issues.

## Required example coverage

| Objective example | Authoritative deterministic coverage |
|---|---|
| Battery enters case before controller | `test_compiler.py`: elliptical BEFORE, region ambiguity, exact predicates |
| Either object may enter first | `test_compiler.py`: compound/contextual either-order, no invented edge |
| Both objects enter before closing | `test_compiler.py`: two edges, no battery/controller order |
| Seal applied after closing | `test_compiler.py`: AFTER retained; unsupported visible semantics explicit |
| Missing action UNKNOWN | `test_semantics.py`, `test_domain.py` |
| Proven reversed order FAIL | `test_semantics.py`, `test_api.py` incorrect demo |
| Overlap UNKNOWN | `test_semantics.py`, `test_domain.py` |
| Unobservable condition flagged | `test_compiler.py`: hidden properties; `test_semantics.py`: unsupported required condition |
| Invented object reference rejected | `test_semantics.py`, `test_muse.py` |
| Malformed/cyclic output rejected | `test_semantics.py`, `test_domain.py`, `test_muse.py` |

## Material integrations

Official Meta public documentation was read using web access. The authenticated
GitHub connector verified repository access and is used for PR publication; Git
push uploads the branch. The in-app browser verified the locally built UI. No
Meta inference integration, paid service or new plugin was installed. GitHub push,
PR and CI status are reported with the final handoff rather than inferred from
local success.

## Next recommended milestone

Verify Muse account entitlement and a conservative request-cost bound, then add a
small explicitly gated real compiler smoke test and semantic-fidelity evaluation.
Keep video perception a separately approved milestone with real grounded
observations and validation before claiming real-world video verification.

## Exact files changed

Application and tests:

```text
.env.example
.gitignore
AGENTS.md
README.md
backend/app/compiler.py
backend/app/config.py
backend/app/evaluator.py
backend/app/fixtures.py
backend/app/legacy.py
backend/app/main.py
backend/app/migration.py
backend/app/muse.py
backend/app/providers.py
backend/app/schemas.py
backend/app/service.py
backend/tests/test_api.py
backend/tests/test_compiler.py
backend/tests/test_domain.py
backend/tests/test_migration.py
backend/tests/test_muse.py
backend/tests/test_providers_media.py
backend/tests/test_semantics.py
frontend/src/App.tsx
frontend/src/EvidenceViewer.tsx
frontend/src/ProgramView.tsx
frontend/src/SemanticProgram.test.tsx
frontend/src/styles.css
frontend/src/types.ts
scripts/generate_fixtures.py
```

Fixtures and documentation:

```text
fixtures/correct.json
fixtures/incorrect.json
fixtures/taskgraph.schema.json
fixtures/taskgraph-v1.schema.json
fixtures/v1/correct.json
fixtures/v1/incorrect.json
docs/meta-api-contracts.md
docs/milestone-2-design.md
docs/milestone-2-plan.md
docs/milestone-2.md
```

Bundled MP4s, dependency manifests/lockfiles, existing audit databases and global
configuration are unchanged. Generated build/test/cache files stay ignored.
