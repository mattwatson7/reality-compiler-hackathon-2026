# Camera review worksheet — unfilled template

Copy this into the ignored `recordings/controlled/` directory for each actual case.
Do not treat this empty worksheet as an attestation or completed acceptance report.
Keep the pre-inference and post-evaluation records separate. Never copy the planned
recording schedule into observed event intervals without watching the actual video.

## Before inference: independent original review

| Required field | Actual reviewer entry |
|---|---|
| Case: correct / reverse / occlusion | |
| Reviewer identity and review time with timezone | |
| Camera operator, device filename and capture time with timezone | |
| Repository filename, byte size and original SHA-256 | |
| Ownership / written permission evidence and permitted publication scope | |
| Consent evidence for any identifiable people | |
| Continuous, normal-speed, untouched original? If not, explain | |
| Native dimensions, duration, frame rate; variable-rate uncertainty | |
| Both identities distinguishable in frame zero? | |
| Target boundary and initial object positions visible? | |
| Entire original watched, including final frame? | |
| Frozen instruction, copied exactly | |

Annotate actual source-time windows. Give bounds for uncertainty rather than a
precise time unsupported by the frames. A hidden action is operator knowledge,
not independently visible ground truth.

| Source start–end | Source frame/PTS when available | Object / region | Visible observation or ambiguity | Identity continuity |
|---|---|---|---|---|
| | | | | |
| | | | | |
| | | | | |

Record separately: expected verdict and rationale; any alternative explanation;
unobservable clauses; whether order can be established without overlapping windows.
Fill the real manifest, run preflight/freeze, and retain the freeze digest and dated
review record independently before starting a job. Record that receipt location.

## After evaluation: actual evidence review

| Required field | Actual reviewer entry |
|---|---|
| Reviewer identity and review time with timezone | |
| Retained freeze digest and matching frozen manifest | |
| Job ID and creation time after freeze | |
| Exact original hash still matches frozen source? | |
| Normalized video hash, frame reference, timing-map file/hash | |
| Compiler name/version and source-grounding limitations | |
| Tracker name/version: local CV or actual SAM? | |
| Observer name/version and any separate Spark use | |
| Actual verdict and check reasons, copied from saved result | |
| Expected verdict, separately copied from frozen record | |
| Mismatch or inconclusive result explanation | |
| Exported job JSON, masks, JPEGs and usage/provenance receipt locations | |

Review every decisive interval in the actual browser and inspect corresponding
masks and source frames. Do not accept high confidence alone. Record missing
identities, sampling gaps, boundary ambiguity, occlusion and final-frame coverage.

| Check / typed predicate and arguments | Evidence ID | Normalized interval / frame indices | Mapped source frames / PTS | Inspected mask/JPEG | Finding |
|---|---|---|---|---|---|
| | | | | | |
| | | | | | |

Record all unsupported requirements and UNKNOWN checks, including absence of
decisive evidence. Save the complete original/normalized playback and frame-zero
selection review findings. Local CV remains a color baseline; structural export
validation cannot prove live Meta execution or camera authenticity. An offline
import remains acceptance pending even when actual and expected labels match.

State the resulting claim narrowly: supplementary local-camera baseline, verified
live camera case with receipts, or pending/inconclusive. Do not claim three-case
acceptance until all three originals and required human/browser/live provenance
reviews support it. No public release permission is implied by completing a review.
