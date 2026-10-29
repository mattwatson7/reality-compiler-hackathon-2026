# Milestone 1 verification — 2026-10-27

Environment: Windows, Python 3.12.15 in `.venv`, Node 22.14.0.

Local automated checks:
- Pytest: 47 passing tests, including real FFmpeg normalization and OpenCV decoding.
- Ruff lint and formatting checks: pass.
- mypy strict backend/scripts checking: pass (12 source files).
- Vitest: 7 passing tests covering evidence seeking, expired/unknown results,
  demo polling, terminal polling errors, draft/result isolation, upload and errors.
- ESLint, TypeScript and Vite production build: pass.
- npm dependency audit: zero reported vulnerabilities.
- `docker compose config --quiet`: pass.

Browser verification with Playwright CLI against the running local FastAPI server:
- Correct sequence returns PASS, incorrect sequence returns FAIL.
- Video metadata: duration 7 seconds, readyState 4, no media decoding error.
- Clicking the cup evidence timestamp seeks to `currentTime === 3`.
- Evidence links and ordering checks are visible with fixture provenance.
- Uploading the bundled correct video through the browser returns UNKNOWN and
  no event observations, while retaining playable normalized video.
- Mobile viewport inspected at 390×844; desktop evidence screenshot inspected.
- Screenshots and CLI snapshots are local ignored artifacts under
  `output/playwright/` and `.playwright-cli/`.

A read-only code review found allocation/cleanup concurrency, multipart spooling,
terminal polling and stale-result issues. Each was fixed, regression tested and
reviewed again; the follow-up found no remaining actionable issues.

Limitations: Docker CLI is installed but the Linux engine pipe is unavailable,
including after launching Docker Desktop. Container build/runtime could not be
verified locally. CI includes `docker build` for a Linux runner; CI has not run
in this local-only repository. Pytest reports one upstream Starlette warning that
its httpx TestClient compatibility is deprecated; all tests still pass.

No Meta endpoint/SDK call is present. No model API, authenticated external
connector, paid inference, deployment, or remote publication was used. Model API
availability and docs remain unverified until approval for the next milestone.
