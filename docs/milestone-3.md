# Milestone 3 implementation and validation

2026-10-27 (Asia/Bangkok). Implements the approved local OpenCV design on
`milestone-3-real-video-perception`. No SAM, live Muse, model downloads or paid calls.

## Working pipeline

- Multipart upload explicitly selects `local_cv` or preserved `mock-upload`.
  Local clips validate before one compilation, normalize to 24 fps within
  1280×720 and 30 seconds, and expose immutable first-frame selection.
- Draw normalized object/region boxes bound to compiled IDs and the normalized
  video SHA-256/frame-zero reference. Unknown IDs, invalid/overlapping boxes,
  user event-time fields, stale/duplicate/expired initialization are rejected.
  Waiting for user input releases the bounded worker slot. SQLite claims the
  initialization atomically. Two local worker threads and one service process.
- Fixed saturated HSV appearance, connected foreground components, bounded
  displacement, area/shape and scene consistency produce samples with frame IDs,
  normalized masks/contours, measured quality, missing/ambiguous states and loss
  intervals. No adaptive identity or recovery. First and last decoded frames are
  sampled. Decode and media operations have frame/time bounds.
- Mask-based region entry/exit uses <=10% outside, >=85% inside, three consecutive
  samples spanning >=0.15s, adjacent gaps <=0.15s and transition duration <=2s.
  Event bounds run from last old-side sample to first confirmed new-side sample;
  full supporting stable runs are saved. Whole-track identity, geometry or gap
  uncertainty makes all that object's raw candidates unusable. Repeated entries,
  unmatched exits and raw candidates remain inspectable.
- The existing exact typed-predicate evaluator determines verdicts. Touching or
  overlapping intervals cannot prove order. Unobserved/unsupported requirements
  remain UNKNOWN. Independent compiler/tracker/observer provenance is persisted.
- Browser selection, actual timestamp seeking, aspect-correct overlays, contours,
  sampled-frame labels, quality/loss JSON, saved supporting JPEGs and timeline.
  Overlays are shown only for reliable sampled display intervals and disappear
  across loss or media expiration. Playback and frame routes are job-owned;
  TTL removes video/images while retaining JSON audit and lifetime budget data.
- Local compiler source is `local_rules`; exact bundled declarations remain
  `fixture`. The exact approved brief has an anchored grammar rule; unknown
  qualifiers stay unsupported. Final-state equality uses 1 microsecond numeric
  tolerance, never one frame/sample interval of missing final evidence.
- The real-recording harness prepares hash-bound normalized frames, validates
  attested manifests, runs the same pipeline, saves raw/evaluated evidence and
  exits nonzero for errors, mismatches or missing three-outcome coverage.

## Evaluation status

**Zero genuine camera recordings are available. Real-world PASS/FAIL/UNKNOWN
validation is UNVERIFIED.** The supplied empty manifest produces an explicit
unverified report and nonzero exit. No generated clip substitutes for a recording.

Synthetic algorithm tests establish frame-derived PASS for block-before-cup,
FAIL for cup-before-block, and UNKNOWN after occlusion. API integration tests run
those generated clips through normalization, one compilation, selection, tracking,
observation, evaluation and saved supporting-frame routes. The two original
fixture outcomes and all legacy audit regressions are retained.

Browser smoke test used a clearly generated regression clip: upload, draw three
rectangles, submit, observe PASS, click evidence to seek frame 30 at 1.25s, inspect
actual boxes/region overlay. This is UI/pipeline evidence only, not real-world
validation. Screenshot: `output/playwright/milestone3-ui-synthetic-smoke.png`.

Local final validation passed all eight contributor commands: **188 backend
tests**, Ruff lint/format, strict mypy, **15 frontend tests**, ESLint, TypeScript
and the production build. `npm audit --audit-level=moderate` reported zero
vulnerabilities. `git diff --check` passed. One upstream Starlette/httpx
deprecation warning remains. GitHub CI results are reported against the pushed
commit in the PR/final handoff. Local Docker engine is unavailable (missing Docker
Desktop Linux engine pipe); CI runs the Docker build. The first default uv cache
attempt could not persist sandbox interpreter metadata. Checks use a workspace
`UV_CACHE_DIR` and `UV_NO_SYNC=1` with the existing locked virtual environment;
no dependencies were installed.

The checked-in [real-recording report](real-recording-evaluation.json) records
zero genuine recordings and no matched outcomes, rather than a success claim.

## Limits and next recording work

Use a fixed camera and distinctly saturated blue block/cup on a plain table.
No object lifting/rotation, occlusion, matching props, camera motion or general
visual-language understanding is supported. The scene-change detector is coarse
and can miss sparse camera motion. Image geometry is not physical containment.
Quality scores are measured heuristics, not probabilities. Local CV emits only
region transitions; final visibility/state-change requirements with no pixel
observer remain UNKNOWN, even though the evaluator supports their contracts.

Follow [recording-capture.md](recording-capture.md) for three held-out 10–30 second
clips and the exact manifest/CLI steps. No credentials are needed. Model access
and account entitlement remain unverified; no live integration is claimed.
GitHub is the only material external integration used for delivery/CI inspection.
