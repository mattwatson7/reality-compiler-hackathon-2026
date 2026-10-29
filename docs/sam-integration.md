# SAM integration research

## Milestone 4 adapter

The local account's authenticated `GET /v1/models` now lists `sam-3.1`.
`SAMTrackerProvider` is implemented against the current hosted contract, including
actual custom one-bit decoding, source-pixel inclusive box conversion, explicit
frame indices, prompted stable-ID mapping and exact foreground-mask overlap.
**No SAM inference was called. All adapter response fixtures are synthetic, not
captured live outputs; inference is not live-verified.** Earlier "key absent"
statements below are historical and superseded by the M4 discovery result.

Official sources rechecked 2026-10-27:
- [Prompt and metadata contract](https://dev.meta.ai/docs/sam/segmenting)
- [Output grammar](https://dev.meta.ai/docs/sam/reading-segmentation)
- [Official protocol/codec](https://github.com/meta-models/meta-sam/blob/main/protocol/sam3.md)
- [Pricing](https://dev.meta.ai/docs/pricing-rate-limits)

One nonstreaming `POST /v1/responses` contains `model: sam-3.1`, a user message
with box prompts in `input_text` and `input_video.video_url` containing normalized
local MP4 data. Metadata strings are `include_confidence: true`,
`mask_encoding: one_bit`, and `propagation_direction: forward`. Values are strings
on the wire. IDs are integers chosen by the request and mapped to application IDs.
Frame zero starts forward propagation through the submitted clip. Geometry, not
the model, enters the existing deterministic region observer and evaluator.

One-bit encoding uses the official custom base85 alphabet/length prefix plus an
adaptive arithmetic coder; Python base85/bit packing would be incorrect. The
implementation is checked against the official synthetic 5×5 conformance vector.
Lossless encoding is explicitly rejected; the adapter requests one-bit output.
Unordered frames are keyed by their explicit indices; unexpected or duplicate IDs,
bad dimensions, malformed masks, conflicting masks and incomplete responses fail
closed. Any missing frame/identity or low confidence causes permanent uncertainty,
never interpolation/recovery. Missing model confidence is nondecisive, not an
invented probability. Model IDs and provider provenance remain in the audit/UI.

Bounds: 1–16 objects, 32MB normalized MP4, 30s/24fps/1280×720, 8MB segmentation
text, 921,600 pixels per mask, 32M total decoded mask pixels, 15s per mask and
90s parsing/conversion cutoffs. Large valid segmentation results may be rejected
conservatively. No SDK, model weights or new package installation was needed.
OpenCV remains functional independently, including with all Meta gates disabled.

The server requires explicit paid approval flags, a key and fresh catalog access.
No test or CI may contact Meta. The ledger reserves at least [private historical cost] per SAM video
before dispatch, and settles only validated successful responses with verified
billed-frame usage. See [M4 contract/accounting record](meta-api-contracts.md).

Checked 2026-10-27 (Asia/Bangkok). Research only; no SAM inference or model
download has occurred. Selected implementation proposal: local OpenCV, pending
design review. Public availability and account entitlement are separate facts.

## Hosted Meta API

The official [model catalog](https://dev.meta.ai/docs/models) lists `sam-3.1` for
image/video boxes and masks. This is an actual documented hosted model, not an
inference from the open-weight release. The [SAM overview](https://dev.meta.ai/docs/sam/overview)
documents `POST https://api.meta.ai/v1/responses`, bearer authentication, a user
message containing `input_text` and `input_image` or `input_video`, streaming or
nonstreaming output, and MP4/MOV with H.264, H.265 or MPEG-4 video. The endpoint
returns geometry; it does not evaluate procedures.

The [prompt guide](https://dev.meta.ai/docs/sam/segmenting) supports one concept
per request, or box/point prompts with chosen object IDs and source frame indices.
Prompt types cannot be mixed. Coordinate conversion must account for display
rotation and preview scaling. Forward, backward and bidirectional propagation
are documented. It also describes confidence requests and media attachment.

The [output contract](https://dev.meta.ai/docs/sam/reading-segmentation) uses
special-token text in `output_text`, streamed through `response.output_text.delta`
and terminated by `response.completed`. Explicit `<Nf>` frame indices may skip
or arrive out of order. Records pair an integer object ID with a source-pixel box
and encoded mask. Mask dimensions are height,width; payloads are base85, with
lossless or one-bit encoding. Optional `c` is per-record confidence. IDs must be
mapped by value, never array position, and continuity is not guaranteed across
full occlusion, leaving/reentering the frame or very long clips. Empty output is
a valid no-match result. A future adapter must validate completeness and bounds.

[Client-library documentation](https://dev.meta.ai/docs/sam/client-libraries)
describes parsing/decoding helpers, including `@meta-sam/parser`; the guides show
OpenAI-compatible Python/TypeScript clients and direct HTTP. None is installed
or used by this research. Application Observation types remain separate from
the vendor wire format.

[Authentication reference](https://dev.meta.ai/docs/api-reference):
`Authorization: Bearer $MODEL_API_KEY`; `GET /v1/models` lists account models.
No `MODEL_API_KEY` or `META_API_KEY` is configured in this process, and no project
`.env` exists. No authenticated request was attempted. Tool discovery found no
dedicated Meta SAM inference connector. Public documentation is reachable, but
account access is unverified; installed unrelated model services are not evidence
of Meta entitlement.

[Published pricing and limits](https://dev.meta.ai/docs/pricing-rate-limits):
[private historical cost]/1,000 images, [private historical cost]/1,000 video frames, at least 50 billed frames per video
request, with `usage.video_frames_processed` reporting billed frames. Published
team limit: 3,000 requests/minute, no token limit for SAM. Recheck before any live
dispatch. A future reservation must cover every request, minimum billing and
verified maximum processed frames before network access; uncertain usage retains
the full reservation. This research establishes no executable paid request bound.

## Local Meta release

The official [release notes](https://github.com/facebookresearch/sam3/blob/main/RELEASE_SAM3p1.md)
date SAM 3.1 Object Multiplex to March 27, 2026 and link its checkpoint and video
examples. This is distinct from the hosted `sam-3.1` API contract.

The [official repository](https://github.com/facebookresearch/sam3) requires
Python 3.12+, PyTorch 2.7+ and CUDA 12.6+ hardware. Its local example constructs
`build_sam3_video_predictor`, starts a session from MP4/JPEG frames and initializes
an object prompt. The shared [predictor source](https://github.com/facebookresearch/sam3/blob/main/sam3/model/sam3_base_predictor.py)
defines `handle_request` / `handle_stream_request`, prompt dispatch and video
propagation. These are local Python interfaces, not hosted HTTP endpoints.

The official [checkpoint listing](https://huggingface.co/facebook/sam3.1/tree/main)
shows `sam3.1_multiplex.pt` at 3.5 GB and requires approval of access conditions.
No HF token is configured in the checked process variables. No checkpoint was
downloaded or access conditions accepted. `nvidia-smi` reports an RTX 4050 Laptop
GPU with 6,141 MiB VRAM. That inventory does not establish sufficient runtime
memory: weights, activations, video state and dependencies must also fit. No
verified minimum VRAM or benchmark on this machine was established.

## Decision and remaining uncertainty

Use the already-installed OpenCV dependency for a bounded, manually initialized
real-pixel baseline. No additional dependencies, GPU requirement, paid API calls
or simulated SAM responses are needed. Expose `local_cv` separately from fixtures;
reject `sam_live` until authenticated access and a tested adapter exist.

SAM is documented both locally and as a hosted API. Its usability for this
account and hardware remains unverified. A later SAM milestone must verify
entitlement, current contract/prices, bounded inputs/output/timeouts and budget
reservation, then obtain explicit paid-smoke-test authorization. Do not present
this document or synthetic contract tests as a working integration.

Actual API spend for this research: $0. No persistent configuration, credentials,
production systems or existing audit/budget data were changed.

## Milestone 3 implementation status

The approved local OpenCV approach is implemented with actual frame decoding,
manual first-frame object/region initialization, fixed HSV tracking, conservative
mask transition events, TaskGraph v2 evaluation and frame-backed UI evidence.
Compiler, visual tracker and observer remain separately replaceable protocols.
No SAM endpoint/SDK was called, weights downloaded, new dependencies installed,
or paid request dispatched. `sam_live` remains rejected. Existing fixture videos
retain their exact SHA-bound declarations. See [milestone-3.md](milestone-3.md)
for checks and the explicitly unverified genuine-recording acceptance criteria.
