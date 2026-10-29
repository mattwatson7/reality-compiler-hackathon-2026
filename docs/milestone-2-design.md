# Milestone 2 semantic compiler: audit and proposed design

Date: 2026-10-27 (Asia/Bangkok). Status: approved by the user and implemented.
Validation and current limitations are recorded in milestone-2.md.

## Existing implementation audit

Reviewed AGENTS.md, README.md, all backend application modules, all five backend
test modules, frontend source and tests, fixture generation and existing milestone
documentation. The checkout is clean at milestone 1 commit `3a0cc49` on
`codex/reality-compiler-m1`, with origin `mattwatson7/reality-compiler`.

- `schemas.py`: version 1 has objects with labels, instruction steps and ordering
  edges. It validates references and cycles but has no predicate semantics,
  observability, optionality, requirements or final-state contract.
- `evaluator.py`: a unique, confident observation with valid evidence marks a step
  PASS. Its `step_id` cannot establish which predicate or arguments were observed.
  Strict disjoint interval ordering is conservative; preserve that behavior.
- `providers.py`: the mock compiler splits instructions and invents ordering
  between every adjacent pair. Trackers and event observers have independent
  protocols, and uploads have no observations. Preserve provider independence.
- `service.py` and `main.py`: an upload compiles during input validation and again
  in its worker. This is harmless at zero cost but would cause duplicate paid
  calls. Compilation is also always wrapped in a zero-dollar mock reservation.
  Paid accounting must belong to the actual dispatch boundary.
- `store.py`: atomic integer micro-USD reservations and conservative settlement
  already implement the lifetime budget invariant. Preserve this database.
- Frontend: TaskGraph v1 is hard-coded. The program view draws arrows based on
  array adjacency, independently of actual constraints. Render real edges only.
- Existing fixtures bind declared observations through the demo route; uploads
  cannot borrow fixture events. Preserve this boundary and timestamp seeking.

Baseline verification: 47 pytest tests and 7 Vitest tests pass; Ruff lint and
format, strict mypy, ESLint, TypeScript and production build pass. Pytest reports
one upstream Starlette/httpx deprecation warning. `uv run` fails on an inaccessible
sandbox interpreter-cache path; the same checks pass using existing `.venv`
executables directly. Docker CLI exists, but its Linux engine pipe is unavailable.
These are milestone 1 baseline checks, not milestone 2 acceptance results.

## Alternatives and recommendation

1. **Recommended: versioned v2 core with an explicit v1 migration boundary.**
   Typed predicates become the only basis for new evaluation. Bundled fixtures
   receive reviewed semantic declarations; arbitrary legacy instructions remain
   unsupported rather than acquiring invented meaning.
2. Add optional predicate metadata to v1. Less code initially, but leaves two
   incompatible meanings of step PASS under the same version; reject this option.
3. Replace everything, including stored runs. Simplifies new types but breaks
   historical audit and demo compatibility; reject this option.

## TaskGraph v2

Use a required `version: "2.0"`, strict Pydantic models, finite bounded values and
bounded collections. Keep original instructions for inspection and source spans
for every emitted event, condition and temporal requirement. Objects have stable
IDs, descriptions and optional visual grounding prompts. Region definitions have
stable IDs, coordinate semantics and explicit visual grounding; a region is not
a claim of physical containment.

Support exactly four discriminated predicates initially:

- `object_visible(object_id)` asserts visible identity during an interval.
- `object_entered_region(object_id, region_id)` requires an observed transition
  from outside to inside a defined visible image region.
- `object_exited_region(object_id, region_id)` requires the reverse transition.
- `visually_confirmed_state_change(object_id, state_dimension, from_state,
  to_state)` requires visible before/after states with explicit visual criteria.

Region transitions do not establish insertion or containment. Occlusion is not a
transition. State changes cannot establish sterility, torque, charge, a hidden
seal, or other invisible properties. Unsupported claims remain separate required
conditions with a reason; they are never silently dropped or encoded as a fake
supported predicate. Region grounding ambiguity similarly prevents PASS.

Events carry stable IDs, a typed predicate, a required/optional flag, source span,
observability (`SUPPORTED`, `AMBIGUOUS`, `UNSUPPORTED`) and a reason when not
supported. Temporal constraints name two event IDs and an explicit `BEFORE` or
`AFTER` operator. Normalize AFTER for cycle checking, preserving its source form.
Dependencies are represented by those edges; unordered events have no edge.
Required conditions and final-state requirements reference supported visible
predicates or carry an explicit unsupported reason. Final states must be supported
at the observable end of the clip; observing a transient intermediate state is
insufficient.

Reject duplicate IDs, dangling references, wrong argument shapes, unsupported
operators, self edges, normalized duplicate edges, cycles and malformed source
spans. Constraints cannot silently make an optional action mandatory: a constraint
involving an absent optional event is nonblocking and is reported as conditional.
Always retain at least one required requirement; an empty/optional-only graph
cannot vacuously verify a procedure.

## Predicate-aware deterministic evaluation

An observation contains an occurrence ID, event ID, the exact predicate and its
typed arguments, positive/contradictory polarity, confidence and traceable timed
evidence. Event IDs alone are insufficient. Preserve finite duration, interval
coverage, unique evidence identity, provenance and confidence validation.

Only an exact semantic match can support PASS. Missing or invalid evidence is
UNKNOWN. Positive contradictory observations can support FAIL; contradictory
claims for the same occurrence produce UNKNOWN rather than silently passing.
Distinct repeated occurrences remain explicit: v2 initially accepts one
unambiguous occurrence per required event; multiple candidates produce UNKNOWN.
Do not select the first, last or highest-confidence candidate. More expressive
repetition selectors are outside this milestone.

BEFORE passes for strictly disjoint correctly ordered intervals and fails only
for a strictly proven reverse order. Overlap and touching are UNKNOWN. AFTER has
the inverse semantics. Unknown or unsupported required conditions prevent overall
PASS; a proven required contradiction yields overall FAIL. Optional checks are
shown but do not independently block overall PASS. Validate that every referenced
evidence ID exists and every decisive check contains valid evidence.

## Compilation and compatibility

The default fixture compiler recognizes a documented, small controlled vocabulary
and the bundled examples. It must preserve explicit BEFORE/AFTER, both-before,
unordered and optional wording. Unknown prose is returned with unsupported
requirements, without invented ordering. This is a limited deterministic
semantic compiler, not general natural-language understanding.

Keep v1 parsing/export available for legacy fixtures and audit records. Only the
two bundled fixture declarations receive an explicit v2 mapping, derived from
their animation definitions, with unchanged evidence timing and playback. Generic
v1 instructions migrate as unsupported unless semantic declarations exist.
Keep endpoint paths and job lifecycle compatible; document the response version
change and test both v1 parsing and v2 API output. Never rewrite stored audit data
or reset the ledger automatically.

## Muse contract and access gate

The public API contract is documented in `meta-api-contracts.md`. No Meta MCP
connector for Muse inference was found among available tools. No `MODEL_API_KEY`,
`META_API_KEY` or `MUSE_API_KEY` exists in this process environment; the repository
has `.env.example` but no `.env`. Account entitlement and authenticated availability
remain unverified. Do not inspect unrelated credential stores or make a paid call.

Complete a compiler response-validation interface and mocked contract tests. Live
dispatch stays disabled while access is unverified. If later enabled with verified
access, use only the documented contract, fixed endpoint/model, bounded response
size, timeout, no implicit HTTP retries, and at most one structured-output repair
attempt. Validate every response with Pydantic and source-span checks; structural
validation alone cannot guarantee that a model preserved instruction meaning.
Reject refusals, truncation and invalid semantics safely, without mock fallback
masquerading as live success. Diagnostics must not expose credentials or raw
provider payloads.

Every future paid attempt, including repair, needs an atomic verified upper-bound
reservation before dispatch. No dispatch if its maximum cannot be verified.
Account for input, schema/prompt overhead and reasoning plus visible output.
Settle only verified usage at documented rates within the reservation; uncertain
requests retain it. The local ledger cannot guarantee all Meta billing charges.
A smoke test requires a separate explicit flag and configured credentials; no
paid inference in CI or routine tests.

Validate upload syntax locally before queueing. Compile exactly once after media
validation in the worker and persist its graph. Keep compilation provenance
separate from perception provenance. Preserve the bounded single-process queue,
media limits, source cleanup and expiry behavior.

## Frontend and acceptance

The program panel displays objects, region definitions, typed events and arguments,
actual temporal constraints, required/final conditions, unsupported reasons and
compilation source. Separate labels indicate whether real Muse compilation and
real video perception are active. A live compiler with mock perception still
returns UNKNOWN for uploads. Preserve demo playback, timeline links and expiry.

Write failing deterministic tests before behavior changes. Cover all ten examples
in the objective, exact-argument mismatches, repeated occurrences, conflicts,
optional events, final-state timing, fixture migration and API compatibility.
Mocked compiler contracts cover malformed output, invented references, cycles,
refusal, truncation, bounded retry and retained budget reservations. No HTTP mock
is described as a recorded live Meta response.

Run every AGENTS.md check and Docker build if an engine is available. Update
README, AGENTS, exported schemas and milestone status documentation. Implement on
`milestone-2-semantic-compiler`, commit the completed milestone separately, push
and open an unmerged PR as authorized in the objective. No deployment, SAM or
Muse Spark integration belongs to this milestone.

## Approval and execution status

The user approved this design and requested implementation and GitHub upload.
Implementation uses the requested milestone-2-semantic-compiler branch in the
existing checkout. Review tightened optional-event ordering, cross-clause action
references and integer cached-token settlement. Observable final-state changes,
as well as final visibility, are supported when evidence reaches the clip end.
No new predicate types, dependencies, credentials or persistent global settings
were added. No paid model call was made. See milestone-2.md for final evidence.
