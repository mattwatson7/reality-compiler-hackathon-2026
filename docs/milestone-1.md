# Milestone 1 design and execution plan

Goal: a runnable local fixture demonstration of compiling procedures and reviewing
timestamped, evidence-backed ordering results. No Meta network requests or SDKs.

Architecture: React/Vite calls FastAPI through /api. Pydantic forbids unknown fields
and validates TaskGraph references and acyclicity. Independent compiler, tracker,
and event observer protocols isolate future model integrations. The mock compiler
splits explicit numbered or newline steps, creates ordering constraints, and makes
no claim to understand arbitrary prose. Demo observations apply only to bundled
synthetic videos. User uploads produce no observations and therefore UNKNOWN.

Evaluation: each step has one occurrence interval with evidence and confidence.
An ordering constraint passes only when the first interval ends before the next
starts, fails only when the reverse is established, and is unknown for overlap,
missing, ambiguous, low-confidence or invalid evidence. The run fails if any
constraint fails, is unknown if any required step/constraint is unknown, and
otherwise passes. Every decisive result references validated video evidence.

Storage/lifecycle: SQLite persists status, graph and result. Videos live under
opaque IDs, expire after configurable TTL, and are swept periodically and on
access. Worker failure is recorded; interrupted jobs become failed at restart.
Uploads have byte and duration limits and are decoded through OpenCV, normalized
to browser H.264 with FFmpeg, and never treated as fixture inference. Single
service process, local trusted use, no authentication in this milestone.

Cost: integer micro-USD reservations in SQLite use BEGIN IMMEDIATE to enforce an
aggregate $100 cap before dispatch. Reservations remain charged conservatively
on failure until explicitly settled. No paid provider is enabled; mock calls
reserve zero. A future provider must reserve a verified upper bound before calls.

UI: dark instrument panel with a procedure editor, fixture buttons, upload,
progress, video, seekable evidence entries and readable TaskGraph. A persistent
fixture/mock banner distinguishes simulation from live inference.

Execution and checks:
- [x] Write evaluator/schema/cost tests, run to establish missing behavior.
- [x] Implement strict schemas, provider protocols, mocks, ordering evaluator.
- [x] Write API/lifecycle tests and implement jobs, uploads, SQLite, TTL and ledger.
- [x] Generate two deterministic synthetic videos and matching observation fixtures.
- [x] Write frontend tests and implement editor, polling and evidence seeking.
- [x] Add Docker, local instructions, env examples and contributor boundaries.
- [x] Run pytest, Ruff, mypy, frontend tests, ESLint, TypeScript and production build.
- [x] Exercise the real HTTP workflow and review all requirements.
- [x] Commit the completed milestone after final verification.

Scope limits: no live inference, authentication, deployment, distributed queue,
or claim that fixtures validate arbitrary physical procedures. Approval is required
before milestone 2. Official Meta API documentation must be read before any real
model endpoint or SDK implementation; model availability is unverified here.
