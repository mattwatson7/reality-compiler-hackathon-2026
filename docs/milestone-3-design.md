# Milestone 3: real visual grounding design

Date: 2026-10-27 (Asia/Bangkok). Status: approved; implementation and validation
recorded in milestone-3.md. Genuine recording acceptance remains unverified.
Base: clean `main` at `61b8447`. Branch: `milestone-3-real-video-perception`.

## Objective and existing architecture

Verify exactly one static-camera tabletop procedure: move the blue block into
the visible marked region before moving the cup into that region. Manual object
and region initialization is allowed; event times always come from decoded video.
Region entry describes visible image geometry, not physical containment.

Reviewed AGENTS.md, README.md, milestone-2.md, meta-api-contracts.md, provider,
service, API, schema, evaluator, compiler and media code, frontend evidence
viewer and CI configuration. Compiler, tracker and observer protocols are already
separate. Upload compilation already occurs once after media validation. Keep
these boundaries, exact fixture SHA binding and legacy audit compatibility.

Issues to address: the local compiler incorrectly reports `fixture`; upload
tracking is empty; current track samples lack frame IDs, quality and loss states;
evidence lacks frame references; final conditions compare timestamps by exact
float equality. The existing evaluator's exact predicate/argument matching,
repetition rejection and disjoint interval ordering remain authoritative.

## Alternatives

1. Recommended: manually initialized local CV, using existing OpenCV. CPU-feasible,
   no new dependency or model access. Requires visually distinct objects, stable
   camera, clear background and conservative rejection of identity ambiguity.
2. Hosted SAM 3.1. Officially documented, but this session has no configured Meta
   key or verified account entitlement. Defer rather than fabricate a live route.
3. Local SAM 3.1. Official 3.5 GB gated checkpoint; this machine has about 6 GB
   GPU memory, with feasibility unverified. Defer weight downloads and dependency
   installation. Findings and contracts are in sam-integration.md.

## Workflow and bounds

Keep demo endpoints unchanged. Add explicit `fixture` / `local_cv` runtime modes;
`sam_live` is rejected with an explanatory error. Preserve the mock-upload path
for compatibility and unsupported/uninitialized recordings.

For local CV, upload and validate the clip, normalize at most 30 seconds and
1280x720 bounding dimensions, compile once, then expose a first-frame preview and
an awaiting-initialization job state. The UI lets the user draw one rectangle for
the marked region and a tight rectangle for each object. Bind selections to
compiled object/region IDs and that job's first normalized frame. Validate finite
normalized coordinates, minimum size, distinct nonoverlapping object selections,
known IDs and an immutable frame reference. Initialization contains no event
timestamps. Submit it once to the existing bounded worker queue; duplicate or
expired submissions fail safely. Release queue slots while awaiting user input.

Add job-owned first-frame and supporting-frame endpoints; accept only server
generated frame indices and job IDs. Expiration removes preview/evidence images
alongside video and returns 410 while retaining JSON audit. Pending initialization
expires through the same cleanup policy. Preserve partial-upload cleanup, size
limits, local-only operation and SQLite budget data.

## Perception and identity

New perception contracts extend v2 without rewriting legacy classes. Each sample
records frame index, normalized-video timestamp, normalized box or null, mask
summary/contour, measured quality components, status and provenance. Each track
has a stable application object ID and explicit missing/ambiguous intervals.
Record source/normalized video hashes and transformation metadata so frame
references unambiguously identify the displayed video.

The local tracker learns a fixed HSV appearance model from foreground pixels
inside each selection; require a dominant saturated color for this baseline.
Recommend a blue block and a distinctly colored saturated cup, on a plain table.
Segment candidate components from actual frames and compare fixed appearance,
area/shape and bounded displacement with the previous reliable sample. Never
adapt identity to a hand or new appearance. Reject competing candidates, masks
shared by both objects, severe area changes, weak segmentation or camera motion.
Document thresholds and expose measured quality as a heuristic, not calibrated
probability. No manual identity recovery after loss in this milestone.

Decode with bounded wall time and frame count; sample at 12 Hz from normalized
24 fps media, including first and last decoded frames. Keep maximum valid
adjacent-sample gap at 0.15 s. Scene motion outside object areas invalidates
fixed-camera assumptions. Missing or ambiguous tracking makes all events for
that object unusable for this run; retain raw candidates and diagnostics for
inspection. This conservative whole-track policy prevents a hidden repeated
entry during loss from becoming a unique decisive occurrence.

## Deterministic events

Compute the fraction of each foreground mask inside the selected rectangular
region. Outside means <=10%; inside means >=85%; intermediate overlap is a
transition band. Confirm a stable side with three consecutive reliable samples
spanning at least 0.15 s. No single bounding-box overlap confirms entry.

An entry needs confirmed outside followed by confirmed inside with uninterrupted
valid tracking; exit reverses those states. Event uncertainty starts at the last
reliable old-side sample and ends at the first new-side sample in the subsequently
confirmed run. Support frames include both full stable runs and intervening
samples. Long boundary dwell beyond 2 s produces UNKNOWN for that occurrence.
Event quality is the minimum supporting quality with an explicit recipe; never
assign an invented 0.99 confidence. Values below the evaluator's threshold cannot
be decisive. Store explanation, object and region IDs, exact predicate, frame
indices and timestamp bounds. All confirmed repeated transitions are retained;
multiple matching occurrences remain UNKNOWN under the existing evaluator.

Already inside at frame zero is no entry. Missing initial frames, tracker loss,
ambiguous identity or unresolved geometry cannot prove an event. Overlapping or
touching event intervals cannot prove order. Detect exits even though the primary
demo asks for entry, and retain them in the observation audit. Only exact graph
predicate matches can generate evaluator candidates; unsupported requirements
remain unsupported. Model/CV output never sets the verdict directly.

The controlled compiler accepts the brief's exact sentence using a narrowly
anchored rule and creates the same explicit blue-block BEFORE cup graph as the
existing grammar. Unknown suffixes remain unsupported. Use `local_rules` as the
compiler source; fixture declarations remain `fixture`.

For final-state comparisons use only a small numeric tolerance (1 microsecond)
for representation error. A sampled observation must explicitly cover the last
decoded frame's display interval to clip end. Do not permit a whole sampling
interval of missing final evidence merely to make the equality check pass.

## API and frontend evidence

Health and results distinguish compiler source, perception mode, real-pixel
processing and actual SAM usage. Local-CV status states the exact supported task
and initialization requirement. Keep observations and diagnostics in persisted
results alongside independent compiler/tracker/observer provenance.

Add a first-frame selection component, then render the selected region and actual
sample boxes/contours with stable labels on the video. Respect media aspect ratio,
rotation/normalization and letterboxing. Draw overlays only for a valid nearby
sample; never interpolate across loss. Show missing/ambiguous intervals and
quality components. Timeline markers and evidence links seek the corresponding
timestamp and expose saved supporting frames. Fixture mode stays prominently
synthetic; local CV explicitly says SAM was not used. Preserve legacy rendering.

## Evaluation and delivery

Separate synthetic algorithm regression tests from genuine recording evaluation.
The repository currently contains only the two generated fixture MP4s. Do not
claim real-world PASS/FAIL validation without actual recordings.

Provide a CLI harness accepting a manifest of genuine files, first-frame boxes,
region, expected verdict and provenance. It runs the same tracking, event and
evaluation implementation, reports observed/expected verdicts and evidence, and
fails on mismatch. Capture three held-out 10-30 second clips: block then cup,
cup then block, and occlusion/ambiguity. Start with both objects visible outside
the region, hold still for one second before/after each motion, separate actions
by at least one second and end with both visible. For the ambiguity clip, hide
an object near the boundary. No manual event times or generated substitutes.

Add deterministic tests for geometry, hysteresis, boundary flicker, gaps, identity
collisions, repetition, initial-inside state, overlap, timestamps, provenance,
unsupported predicates and frame-derived end-to-end API behavior. UI tests cover
selection mapping, overlays, absence of overlays across loss, labels, timeline,
seek and expiration. Preserve all existing fixture and legacy regressions.

Run the eight commands in AGENTS.md, npm audit, and Docker build if the engine is
available. Report actual local and branch CI outcomes separately. Update README,
AGENTS, milestone-3.md and SAM research; commit completed implementation separately
from this design. Push the requested branch and open a PR without merging.
No paid calls, public deployment, production changes or ledger reset.

Acceptance remains incomplete until implementation checks pass and genuine
recordings establish PASS, FAIL and UNKNOWN with inspectable real-frame evidence.
If recordings are unavailable, deliver the harness and capture instructions and
explicitly report that real-recording criteria remain unverified.

## Baseline validation before implementation

On 2026-10-27, the unchanged application passed 156 backend tests (one upstream
Starlette/httpx deprecation warning), Ruff lint and format checks, strict mypy,
11 frontend tests, ESLint, TypeScript and the production frontend build.
`uv run` failed querying its interpreter because the sandbox could not persist
its cache; backend checks used existing `.venv/Scripts` executables instead.
Docker CLI is present, but `docker info` cannot connect to the Docker Desktop
Linux engine pipe, so a Docker build is unavailable. These are baseline results,
not evidence that Milestone 3 is implemented. GitHub connector access verified
the main commit; no branch CI or real-recording evaluation has run.
