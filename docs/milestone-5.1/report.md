# Milestone 5.1 final engineering and submission report

October 28, 2026. **Describe what should happen. Show what happened. Prove whether they match.**

## A. Implementation and scope

Continued the existing `milestone-4-meta-integration` branch from `17e2b4f4d4c69159d578bea6f3317781b42e918f`, without changing historical runs or spending authorization.

New uploads now carry a hash-bound decoder-frame/PTS map through explicit 24 fps conversion. The source inspector returns the corresponding original decoded frame, checks the media identities and completed evidence seal, and decodes the same first video stream as normalization. Historical recordings remain explicitly unmapped. The [mapping contract and tests](source-timing.md) explain duplication, dropping, VFR, trimming, nonzero starts, terminal frames and failure boundaries. Evaluation still uses immutable normalized intervals; source display cannot rewrite ordering semantics.

Comparison cards now identify each typed requirement using object labels, explain changed temporal requirements and unsupported conditions, and explicitly identify perception reuse. Comparison evidence links use the evidence player's shared seek handler, including when metadata is still loading. A regression caught the previous wrapper-versus-video error. Another catches microsecond-rounded browser times selecting the preceding source frame. Offline generated/captured-evidence status is visible near the top of the page.

Added an offline controlled-camera preflight, pre-inference expectation freeze, and application-result import harness. It validates source identities, frozen instructions, evidence/provenance and deterministic evaluation. It never promotes untrusted JSON to successful live acceptance. The [recording guide](recording-guide.md) specifies camera geometry, colors, spacing, lighting, continuity, timings, occlusion, filenames and independent annotations. Its three-case template is deliberately incomplete until a human records and inspects originals.

The repository now ignores private `recordings/` sources to prevent accidental staging. No original video, audit record, ledger, capture, historical evaluation or model response was deleted. Existing substantial JSON evidence remains because it supports independent replay.

## B. Physical-world evidence reconciliation

The filesystem contains only the four prior third-party originals under `recordings/external/`. Their SHA-256 values match the earlier inventory and authoritative sources. **No new controlled physical-camera recording is present.** No paid inference or new model-based camera evaluation occurred in this milestone. The following results are historical captured results, freshly reproduced by deterministic replay; human imagery inspection and live model calls belong to milestone 5.

| Original / SHA-256 | Exact source and selected interval | Predeclared expectation | Captured Meta / local CV verdict | What it establishes |
|---|---|---|---|---|
| `cam1.mp4` / `26a4f40bcecbb23bf7f92c5d106ca013155283e9672e94f9efe3807c9f783f56` | Bigenlight `take_03_20260720_205457/cam1.mp4`, repository revision `e0a6957536ea3c3b2ab063376103378428c34a8e`; whole 10.767s | UNKNOWN for purple-block projected-region movement under gripper occlusion | UNKNOWN / UNKNOWN | Identity/visibility uncertainty remains; no hidden containment established. |
| `3_16_peg_eval_continual_success.mp4` / `21da6950563fa18ef0c1f7d93767c6e241651b38535866d6f66fb58e02a94971` | OmniReset authoritative continuous-evaluation asset, bytes matched; first 6s | PASS or UNKNOWN for final green-base visibility, conditional on reliable identity | PASS / UNKNOWN | Selected base visible at the normalized endpoint. Not peg insertion or full task success. |
| `real_nonprehensile.mp4` / `2f0ab52f71f7af787bbcde5040a8611f44415b6ccc3f163ce7077b8df4706b92` | OmniReset authoritative non-prehensile asset, bytes matched; first 8s before intervention/edit | PASS or UNKNOWN for final base visibility | PASS / UNKNOWN | Narrow final visibility only; same-color geometry/occlusion prevents broader inference. |
| `real_perturb.mp4` / `efb06c17f2a90394f539f311efcb41d2b3deb4c5e0840c154f35077ba43c5bd9` | OmniReset authoritative perturbation asset, bytes matched; first 8s before later view change | PASS or UNKNOWN for final base visibility | PASS / UNKNOWN | Narrow selected-prefix visibility only; no claim about the later full recording. |

Original expectations remain in [predeclared-procedures.json](../milestone-5/predeclared-procedures.json); its optimistic legacy source-time approximation is superseded by the documented limitation, not silently corrected. Exact evidence IDs, normalized ranges, masks/model provenance and actual usage remain in [live-results.json](../milestone-5/live-results.json) and the [capture index](../milestone-5/capture-index.json). No new ground truth was chosen after seeing outcomes.

Controlled A/B/C camera acceptance is **pending external originals and separately authorized live validation**. The expected A PASS, B FAIL and C UNKNOWN are hypotheses in the protocol, never evaluator inputs. Generated footage cannot satisfy this requirement.

All four original sources are now exactly attributed. The Bigenlight card declares Apache-2.0; preserve the applicable notices before any future distribution. OmniReset's code license does not establish permission for separately hosted video assets. Public demo assets remain generated-only. See [dated rights research](footage-rights-research.md) and the [machine-readable permissions inventory](provenance-permissions.json).

## C. Procedure comparison and browser validation

The real browser imported a new offline captured-evidence review using the verified generated source and actual prior Meta SAM observations. It then submitted **newly typed instructions**, independently compiled locally through the normal evaluation endpoint. [Browser comparison export](browser-comparison.json) preserves the graphs, typed requirements, verdicts, reuse status, evidence identities and provenance.

| Evaluation | Independently compiled requirements | Actual verdict / reason |
|---|---|---|
| Original: “Slide the blue block into the visible marked region, then place the cup into the same region.” | Prior Wonder compilation: block entry, cup entry, block BEFORE cup | PASS: both entries and disjoint ordering intervals supported. |
| New browser revision: “Move the cup into the visible marked region before moving the blue block into that region.” | New local compilation: cup entry, block entry, cup BEFORE block; compiler-local object IDs differ | FAIL: the same evidence proves reverse order. |
| New browser revision: “Move the blue block into the visible marked region before moving the cup into that region. Ensure the cup is sterile.” | New local compilation: original entries/order plus explicit unsupported sterility requirement | UNKNOWN: the visual order is supported; sterility is not observable in the controlled grammar. |

Supporting captured evidence: `cv_object1_region1_20_23_0` at 0.750–1.125s and `cv_object2_region1_54_58_0` at 2.167–2.583s. These are support intervals; the decisive transition intervals are narrower. All compared evaluations retain the same perception fingerprint. Original result remained PASS. Six evaluations persisted through a real server restart. New revision usage is empty; SAM/Spark were not dispatched again. Spark was not needed for the original generated order comparison either; the demo does not pretend it contributed to this verdict. Original Wonder/SAM provenance is retained, while revisions clearly identify local compilation.

A comparison link sought the actual video to 2.166666s and updated its overlay. Desktop comparison and 390×844 mobile layouts were inspected; document width was 375px with no horizontal overflow. Browser console checks reported no warnings/errors for the verified review/upload journeys. [Desktop](comparison-desktop.jpg), [uncertainty](comparison-unknown.jpg), [mobile](browser-mobile.jpg), and [full offline page](browser-pass-fail.jpg) are actual screenshots on generated input.

A second real browser journey uploaded the existing generated clip, manually selected block/cup/region on normalized frame zero, and ran **actual local OpenCV**, with no Meta calls or fixture event substitution. The result was PASS for its supported region-entry order. [New upload export](browser-upload.json) preserves source/normalized identity, selections, provenance, source map and verdict. This is generated algorithm/browser validation, not camera acceptance. At the cup evidence interval, normalized frame 50 mapped to original decoded frame 50, PTS `25600 × 1/12288 = 2.083333…s`; the original 320×180 PNG loaded. [Selection screenshot](browser-selection.jpg) and [source attribution screenshot](browser-source-attribution.jpg) show the actual interactions.

## D. Demo production status

**No finished playable demo MP4 was produced.** The available browser-control API provides interactions and screenshots without continuous recording. No synthetic UI video was represented as an actual recording. The [120-second production package](demo-production.md) includes complete narration, timed shots, exact browser instructions, screen-recording/edit checklist and annotated screenshot selects. Its generated-only footage avoids unresolved research-video permissions. A human must record/export the sequence and check the participant portal's actual duration/file limits.

## E. Submission and reproducibility

The [submission package](submission.md) includes headline, short/long pitch, problem/opportunity, differentiation, technical architecture, all three model roles, working features, truthful validation, limits, rights and checklist. [Judge reproduction](judge-reproduction.md) gives PowerShell and cross-platform instructions for a new isolated data directory, disabled gates, hash-verified capture replay and real-browser inspection. The isolated zero-cost demo ledger is explicitly distinguished from the unchanged lifetime ledger. Normal media expiry is retained; expired audit history remains. No downloadable bundle of private camera media is needed.

Official [Meta event dates](https://dev.meta.ai/events/global-hackathon) and [Cerebral Valley rules](https://cerebralvalley.ai/e/meta-ai-developer-hackathon/waiver) were rechecked October 28: deadline **November 5, 2026, 09:00 Bangkok / November 4, 21:00 US Eastern**; scoring impact 30%, Meta tooling 25%, execution 20%, demo 25%. Push the Frontier is an appropriate **theme**; indie/startup track and eligibility belong to the entrant. The signed-out [submission page](https://cerebralvalley.ai/e/meta-ai-developer-hackathon/hackathon/submit) did not expose authenticated fields, character limits or video constraints. No participant identity/team/eligibility or portal field was invented. No public deployment requirement was found in the inspected public material; an authenticated form could add details. A deployment is not proposed at this stage because local reproduction already works and public hosting would introduce media/privacy/security obligations.

## F. Cost and authorization

Previous lifetime committed exposure: **[private historical cost]**. New Meta paid requests: **0**. New paid exposure: **$0**. Final lifetime ledger: **[private historical cost] / $100**; remaining **[private historical cost]**. Both root-configured paid gates were read as false without revealing configuration values. All review/smoke processes explicitly disabled paid inference. Failed/uncertain reservations remain intact; no ledger was reset or settled speculatively. The isolated demo's zero ledger is not represented as total project spend.

## G. Verification, review and repository audit

Final full backend suite: **357 passed**, with the existing Starlette/httpx TestClient deprecation warning. Frontend: **21 passed**. Ruff lint/format, strict mypy (33 source files), lock consistency, ESLint, TypeScript and production build passed. Offline replay verified 17 captured-response hashes and reproduced all recorded camera/generated evaluations without network dispatch.

The extended `scripts.docker_smoke` passed against an isolated loopback server: built frontend, fixture PASS/FAIL, playback, append-only revision history, unsupported UNKNOWN, actual upload/normalization/source-map PNG and zero ledger cost. Local Docker engine access failed because Docker Desktop's Linux pipe was absent; this is disclosed rather than counted as a local Docker pass. Hosted CI runs the actual Docker build and this extended running-container smoke. Consult the delivered commit's [PR checks](https://github.com/mattwatson7/reality-compiler/pull/3/checks); the final handoff and PR description record its exact CI run and SHA.

Security checks: npm audit reported zero vulnerabilities; OSV queried 38 locked registry Python packages with zero findings. Pattern-based credential and capture-header scans found no matches; this is a scoped scan, not a guarantee of complete secret detection. No tracked `.env`, database, research recording or production frontend source map was found. The initial 246 tracked files totaled about 6.7 MB; largest was the 1.68 MB live-results audit JSON, which was retained. New images contain only project-generated pixels/UI. Private originals and outputs are ignored and excluded from Docker context. Internal Markdown links were checked after assembling the report.

Independent read-only review caught and verified fixes for video-stream mismatch, missing source-map seal enforcement, and rounded timestamp boundary selection. Regression evidence includes failing-before/passing-after stream/seek/boundary checks. Reviewer also confirmed all nine initial permissions-inventory hashes/sizes and prompted the private-recordings ignore rule. No threshold, ambiguity rule or paid-gate safeguard was weakened. [Structured verification record](verification.json) records commands and qualifications.

Material external integrations: authenticated GitHub connector for repository/PR state and authoritative website source; official Meta/Cerebral Valley web research and actual browser rules inspection; Hugging Face metadata and authoritative public media hash streaming for exact source attribution; OSV vulnerability service; browser automation for local upload, selections, evidence navigation, comparison, restart and mobile checks. No OpenAI API, new plugin/dependency, paid Meta call, external communication, deployment or submission was used. Authenticated participant form and local Docker engine remain unavailable.

## H. Delivery

Existing PR: [mattwatson7/reality-compiler #3](https://github.com/mattwatson7/reality-compiler/pull/3), existing branch `milestone-4-meta-integration`. Completed changes are committed and pushed there; the exact delivered SHA and hosted run are recorded in the final handoff/PR description. **PR #2 and PR #3 remain unmerged.** No permission, waiver, deployment or account setting was changed.

## I. Exact next human actions

1. Sign in to the participant portal, confirm accepted-participant eligibility, team/representative and indie/startup track, and inspect the actual fields/video requirements. Review required terms personally; no agreement has been accepted here.
2. Record/export the two-minute generated/offline demonstration from the supplied production package, keep provenance labels visible, and verify final codec, duration, size, audio/captions and public assets. This is a submission-media blocker; the script/screenshots are ready.
3. Review the final descriptions, repository/CI and demo, then explicitly authorize the final external upload/submission. No merge or deployment is required by this implementation.
4. For the desired stronger physical-world claim, provide the three original controlled recordings following the guide, inspect/annotate/freeze them before inference, and separately authorize any new paid live validation. Until then keep controlled camera acceptance pending. This blocks that claim, not use of the truthful generated/captured-evidence submission.

Optional: pursue OmniReset video permission only if those pixels are wanted publicly; the generated-only package does not need them. Do not publish research-camera frames based on source attribution alone. Recheck official deadline before submission because organizers can change dates.
