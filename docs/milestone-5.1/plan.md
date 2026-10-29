# Milestone 5.1 execution plan

Goal: a truthful, reproducible submission built around independent procedure evaluations of immutable evidence.

Starting state: milestone-4-meta-integration at 17e2b4f; PR #3 open, unmerged. Only four prior third-party camera files are present under recordings/external. Controlled correct/reverse/occlusion originals are absent. Preserve all history and the [private historical cost] lifetime ledger. No paid inference, deployment, submission, or merge.

Execution uses the planning, systematic-debugging, test-driven-development and parallel-agent skills. Independent documentation and camera-harness work have separate ownership; source mapping and browser correctness stay with the primary agent. Independent read-only review follows implementation.

- [x] P0: investigate and reproduce encoder timestamp behavior; add deterministic source PTS/frame mapping and regression tests (25, 29.97, 30 fps, short/VFR/trimmed media). Bind mapping to hashes; leave historical runs unchanged and explicitly unmapped.
- [x] P0: reconcile inventory/hashes; deliver exact recording guide and predeclared acceptance harness, mark physical controlled validation pending.
- [x] P1: repair evidence navigation, expose source attribution, improve procedure comparison and verify real browser desktop/mobile journey and screenshots.
- [x] P2: rights inventory, official deadline/rules, complete two-minute recording and submission package; strengthen isolated offline judge reproduction without credentials or ledger mutations.
- [x] P3: audit tracked data, dependencies/secrets/docs; all backend/frontend/replay checks, independent review, commit/push to existing PR #3 and verify hosted Docker CI. Leave both PRs unmerged.

Validation: uv run pytest --basetemp .pytest-tmp -q; uv run ruff check .; uv run ruff format --check .; uv run mypy; uv lock --check; npm --prefix frontend test; npm --prefix frontend run lint; npm --prefix frontend run typecheck; npm --prefix frontend run build; npm audit; locked Python dependency vulnerability check; sanitized capture/secret audit; offline replay; real browser; hosted Docker CI.

## Completion evidence

357 backend tests and 21 frontend tests pass; lint/format/types/lock/build/replay/security/links and isolated smoke pass. Actual desktop/mobile browser comparison, new local CV upload/manual selection, source-frame inspection, and restart persistence were verified. Final delivered SHA/hosted Docker CI are recorded in the PR and final handoff. Physical camera acceptance remains pending new originals and separately authorized live validation; no demo MP4 or authenticated participant fields are claimed.
