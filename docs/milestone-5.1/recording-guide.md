# Controlled camera recording and acceptance protocol

Status on 2026-10-28: **pending external footage**. The inventory contains only
`cam1.mp4`, `3_16_peg_eval_continual_success.mp4`, `real_nonprehensile.mp4`, and
`real_perturb.mp4` under `recordings/external/`. These prior third-party research
clips do not establish controlled temporal PASS/FAIL/UNKNOWN coverage. No new
camera recording, paid call, or camera acceptance is claimed by this protocol.

## Record three originals

Use a tripod directly above a matte charcoal tabletop, lens 70–100 cm above it,
optical axis perpendicular to the table. Frame a 60 cm wide × 34 cm high work
area; keep the whole marked target and both starting objects in view. Lock
focus, exposure and white balance. Use 1280×720 landscape, 30 fps constant rate
(25 or 29.97 fps originals are acceptable with recorded timestamp mapping),
normal speed, 15 seconds per clip, MP4/H.264, below 100 MB. Do not crop, edit,
stabilize, retime, add transitions, or recompress the original after capture.
The application will independently normalize it to 24 fps. Preserve the camera
file byte for byte and keep its original device filename in private capture notes.

Use one solid saturated blue block, about 5×5×5 cm, and one solid yellow cup,
about 6 cm diameter and 8 cm high. Prefer matte surfaces without matching blue
or yellow patterns elsewhere. Neither object may be visually identical to the
other or the background. Illuminate from two diffuse lamps, avoid glare, shadows
over the target, flicker, automatic exposure changes and direct sunlight.

In the recorded image, mark a thin white rectangle with its *inner* boundary
at normalized coordinates x=0.55, y=0.25, width=0.35, height=0.50 (approximately
448×360 pixels at 720p). This is a visible image region, not a receptacle: it
does not demonstrate containment, insertion, sterility or any hidden state.
Start the block centered around (0.18, 0.35) and cup around (0.18, 0.70), with
at least 10 cm clear separation between their visible silhouettes and at least
10 cm from the target. End the block around (0.66, 0.38), cup around (0.80, 0.62),
keeping their projected silhouettes separated by at least one object width.
Adjust physical positions before starting to meet the image coordinates.

Hold still from 0–3 s. Move the first object steadily during 3–5 s, release it
fully within the marked region and remove the hand. Hold still during 5–8 s.
Move the second object during 8–10 s. Remove the hand and hold the full scene
until the clip ends at 15 s. Use a thin stick from outside the image to push
objects, or grip a visible rim away from the object's identifiable surface.
Hands must not obscure either identity or cross another object. The three-second
gap makes event intervals independently separable. Retake before inference if
the intended clear recording has identity loss; preserve failed takes separately.

| Scenario | Required filename under repository root | Action sequence | Predeclared expectation |
| --- | --- | --- | --- |
| A correct | `recordings/controlled/correct.mp4` | Blue block first, yellow cup second | PASS only if both typed region transitions and order are proven |
| B reverse | `recordings/controlled/reverse.mp4` | Yellow cup first, blue block second | FAIL only if the opposite order is proven |
| C occlusion | `recordings/controlled/occlusion.mp4` | At 3 s place an opaque gray card between lens and block/path/target; keep cup visible; move block behind card during 3–7 s; uncover at 8 s and move cup during 10–12 s | UNKNOWN where block identity or entry timing cannot be established |

For C, show both objects clearly during the first three seconds. Cover the
block completely before it could cross the target boundary; keep it covered
for at least two seconds. Do not assert recovered identity when it reappears.
If other decisive failure evidence exists, report the actual result instead of
forcing UNKNOWN. Never tune thresholds or expectations after a model run.

## Predeclare and freeze before inference

The fixed original instruction is:

> Move the blue block into the visible image region target, then move the yellow cup into the visible image region target.

Before opening any inference path, independently watch all three original clips.
Record source SHA-256, capture timestamp with timezone, actual operator, ownership
or written permission basis, and private/public distribution permission. Obtain
consent for any identifiable people; avoid faces, voices, personal documents,
screens and private surroundings. A provenance declaration is a human attestation,
not automated proof of authenticity or legal permission. Do not publish footage
without the user's explicit publication authorization.

Copy `controlled-manifest.example.json` to
`recordings/controlled/manifest.json`. The example is deliberately invalid until
real hashes, operator, rights, capture dates and independently observed intervals
replace every placeholder. Paths are relative to the manifest. Ground-truth
intervals are human observations on the original timeline; annotate visible
entry windows, release/still periods, and obscured intervals honestly. They are
never inputs to perception or evaluation. Preserve notes separately from model
outputs. Check the original first-frame scene and terminal frames independently.

From the repository root, after supplying actual originals:

```powershell
uv run python -m scripts.controlled_recordings --preflight recordings/controlled/manifest.json
uv run python -m scripts.controlled_recordings --freeze recordings/controlled/manifest.json --output recordings/controlled/frozen-expectations.json
```

Both commands are offline and perform no inference. Preflight checks schema,
original bytes, distinct sources, size, 10–20 s media bounds and annotation bounds.
Known bundled/generated MP4s and prior research hashes are rejected; this cannot
detect every synthetic or edited video. Freeze creates a new file exclusively;
it never overwrites an existing freeze. Save its printed SHA-256 in an independent
dated review record **before inference**, along with the frozen file. The digest
detects later changes when compared to that retained value. Local files and local
timestamps are not tamper-proof notarization. An independently retained receipt
and reviewer chronology remain necessary. Changed sources or expectations need
a fresh study, with earlier declarations/results retained, never overwritten.

## Execute only after separate paid authorization

Keep both paid flags disabled. This harness has no compiler/model dispatch,
network transport, keys or configuration changes. The next steps are a protocol
for a future separately authorized live session, not permission to enable it.

Use the actual browser upload workflow for each original after the freeze.
Require original normalization → independent Wonder compilation → manual immutable
frame-zero object/region selection → SAM tracking → deterministic observations →
Spark only where appropriate → deterministic evaluation. Save the completed
`GET /api/jobs/{job_id}` JSON, its exact normalized `video.mp4`, mapping metadata,
SAM mask file, saved evidence JPEGs and provider usage/capture records before
retention expiry. Do not present local CV, offline capture replay or a fixture
as that full live pipeline. Manual selection binds compiled object IDs and region
IDs to normalized frame zero; do not insert human event times into observations.

Example offline import after a real completed application run (replace SEAL):

```powershell
uv run python -m scripts.controlled_recordings --import-result recordings/controlled/correct-job.json --frozen recordings/controlled/frozen-expectations.json --seal SEAL --case correct --normalized recordings/controlled/correct-video.mp4 --output recordings/controlled/correct-import.json
```

Repeat for `reverse` and `occlusion`. The importer checks creation after the
freeze, source/normalized identities, instruction equality, typed schemas,
evidence references, saved frame indices and independent provider provenance.
It reruns the normal deterministic evaluator over the exported graph and
observations and rejects a changed result. Expected labels are compared only
after evaluation; filenames never determine a verdict. Import output **always
remains acceptance pending**: untrusted JSON can claim provenance, so an offline
structural check cannot independently establish that live stages occurred.

## Human and browser acceptance gate

Create a dated private review report for each case containing source/normalized
hashes, retained freeze seal, job ID, instruction, expected and actual verdict,
every decisive evidence ID and normalized interval, corresponding source frame
mapping/precision, model IDs and usage records, observer version, mask-file hash,
and exact inspected JPEG/mask references. Record reviewer identity and review time.
Explain all failed or unknown predicates and whether final evidence reaches the
clip endpoint. Separate the frozen human annotation from the model observation.

In the actual browser, play each entire original, inspect normalized frame zero,
draw/select both objects and target, inspect masks before/during/after every
entry, check identity continuity and occlusion, and click every decisive interval
to verify the source frame mapping and geometry. Save browser screenshots and
the human inspection report. A high confidence value alone proves nothing.
Compare all three imports and reviews; report mismatches openly. Only call this
live camera acceptance when all three original scenarios have verified live
production provenance, trustworthy evidence, expected coverage, and completed
human/browser inspection. A pending or inconclusive case remains pending.

For B, independently compile the reversed procedure and reuse compatible saved
perception through the normal application re-evaluation endpoint. Also compile
the original procedure plus a sterile-cup requirement. Preserve original history,
prove the perception fingerprint is unchanged and no new SAM/Spark calls occurred,
and retain each independently compiled graph and actual check reasons. Expected
triples are A PASS/FAIL/UNKNOWN; B FAIL/PASS/FAIL only when the order violation is
decisive; C UNKNOWN wherever decisive observations remain unavailable. These
expectations never override evaluator output.
