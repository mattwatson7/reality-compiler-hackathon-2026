# Authorized live smoke — 2026-10-27

At 21:56:50–21:57:18 Bangkok (14:56:50–14:57:18 UTC), one authorized
`muse-wonder-1.0` POST returned HTTP 200. Its TaskGraph failed existing strict
validation. The run stopped; **zero SAM requests, zero Spark requests, zero
retries**. Paid gates are false again; persistent server flags stayed false
throughout. The fixed authorization claim is consumed in the existing persistent
SQLite database, in a dedicated `smoke_authorizations` table. Do not reset it or
rerun with another claim without fresh human authorization.
The shipped entry point is also retired in code and rejects execution even if
the database is unavailable or replaced. The runner remains for audit and offline tests.

## Preflight and cost

Official [prices](https://dev.meta.ai/docs/pricing-rate-limits),
[model context/availability](https://dev.meta.ai/docs/models),
[chat contract](https://dev.meta.ai/docs/api-reference/chat-completions/schemas),
[strict schema](https://dev.meta.ai/docs/structured-output),
[SAM prompts](https://dev.meta.ai/docs/sam/segmenting) and
[mask grammar](https://dev.meta.ai/docs/sam/reading-segmentation) were re-read
on 2026-10-27 before dispatch. Fresh authenticated catalog discovery confirmed
Wonder and SAM. Bearer authentication stayed server-side; no new SDK was used.

The existing ledger had $100 available, with eight zero-cost fixture/mock rows.
The authorized combined ceiling was [private historical cost]: Wonder [private historical cost] (full 1,048,576
input ceiling plus 4,096 capped output tokens) and SAM [private historical cost] (at most 720
forward frames). No tools, search, retries, multiple completions or Spark were used.

| Item | Actual reported usage | Estimated charge | Reservation retained |
|---|---|---:|---:|
| Wonder | 121 input, 0 cached, 2,570 output, including 1,804 reasoning; 2,691 total tokens | [private historical cost] | [private historical cost] |
| SAM | Not dispatched | $0 | $0 |
| Spark | Not dispatched | $0 | $0 |

Estimate uses $4/M input, [private historical cost]/M cached and $20/M output. Reasoning is already
included in output; it is not counted twice. This is response usage and a price
estimate, not a verified billing invoice. The rejected adapter result was never
acknowledged or settled. Ledger committed exposure remains [private historical cost]; available
lifetime budget is [private historical cost]. The unused SAM allowance was never reserved.

## Validation result

The live envelope matched the expected chat shape: correct model, one assistant
choice, `finish_reason: stop`, JSON content and internally consistent token usage.
The JSON followed the structural schema but failed TaskGraph semantic validation:
source spans did not equal `procedure[start:end]`. For example s1 uses `[0:51]`
for a 50-character quote, s2 uses `[59:65]` for a 31-character quote, and t1 uses
`[0:65]` for a 90-character quote. The graph also treated missing video as an
unsupported procedure and invented a persistence event. These were not repaired
into an accepted graph. The deterministic evaluator is unchanged.

The synthetic clip was prepared and decoded locally: 72 frames, 24 fps, 320×180,
3 seconds; source-frame timestamps run from 0 through 71/24 seconds. Its hash and
immutable frame-zero reference are recorded. Because the compiler failed, SAM
masks, output frame IDs and observation timestamps could not be validated live.
**No PASS/FAIL/UNKNOWN evaluation was run.** No genuine-camera validation is claimed.

## Fixes and evidence

- Added a durable one-authorization runner with sequential allowances, exact
  reservation caps, no retries, first-success acknowledgment gate and final
  disablement. CI/pytest cannot invoke its live entry point.
- Clarified that compiler observability is checkability, not proof of execution;
  specified exclusive character offsets and prohibited invented persistence or
  repeated events. Added safe validation-stage diagnostics. Prompt improvement
  is **not live verified**; no additional paid request was made.
- Replayed the sanitized actual response offline: rejection and absence of
  retries/settlement are regression-tested. Existing evaluator rules remain intact.
- Review caught an initial authorization marker incompatible with expiring jobs;
  migrated that exact local marker to dedicated durable storage, retaining its
  consumed state and all cost rows. Cleanup and duplicate-claim regressions pass.

Sanitized [result](meta-smoke-result.json) and the actual sanitized
[Wonder response](meta-smoke-wonder-response.json) are retained with hashes.
The private sanitized evidence and synthetic video remain under the ignored
`data/meta-smoke-2026-10-27-one-wonder-one-sam/` directory. Credentials, headers
and reasoning text are excluded; only reasoning token counts are retained.
These files are live failure evidence, not synthetic examples of successful output.

External integrations used: Meta Model API (one catalog read, one Wonder POST),
official Meta documentation through web access, and authenticated GitHub for
PR #3 and CI. SAM inference compatibility remains unverified; new paid testing
requires new explicit authorization. Neither PR #2 nor PR #3 is merged.

## Milestone 4.1 follow-up (2026-10-28)

The architectural follow-up is documented in [milestone-4.1-report.md](milestone-4.1-report.md).
Source IDs are now resolved by application code and semantics checked independently.
A pinned, local TaskGraph and separate SAM-only harness have been prepared offline.
No new paid request was made. SAM-only authorization is pending, for a maximum
reservation of **[private historical cost]**, not the old 720-frame ceiling. The original failed
response and retired authorization above remain unchanged audit evidence.

## Milestone 4.2: new explicit authorization and actual successful inference

The user explicitly requested the prepared SAM execution and continued live
integration debugging on 2026-10-28. That new scope supersedes the historical
pending-approval status of the independent SAM plan, without reusing the old
Wonder authorization. The exact SAM claim was consumed in the persistent ledger;
its entry point is retired again. See [live results and failure evidence](milestone-4.2-live-report.md).
