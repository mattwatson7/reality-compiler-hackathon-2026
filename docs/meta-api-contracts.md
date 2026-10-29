# Meta API contracts

## Milestone 5 re-verification (2026-10-28)

The user separately authorized bounded live Wonder/SAM/Spark validation in this
chat on October 28, within the remaining lifetime ledger. Persistent `.env`
flags stay false; only the authorized local validation process enables them.
Before new endpoint calls, re-read the official [models](https://dev.meta.ai/docs/models),
[authentication](https://dev.meta.ai/docs/api-reference),
[chat endpoint](https://dev.meta.ai/docs/api-reference/chat-completions/create-chat-completion),
[chat schemas](https://dev.meta.ai/docs/api-reference/chat-completions/schemas),
[SAM prompt contract](https://dev.meta.ai/docs/sam/segmenting),
[SAM output grammar](https://dev.meta.ai/docs/sam/reading-segmentation), and
[pricing](https://dev.meta.ai/docs/pricing-rate-limits).

The implemented requests remain bounded nonstreaming chat completions with
strict JSON schema and capped output, and frame-zero forward one-bit SAM
responses. Bearer authentication is server-side at the fixed api.meta.ai origin.
The documented context ceilings and Standard prices match the integer bounds
below. Account entitlement must still be freshly discovered at process start.
SAM IDs cannot establish identity after complete occlusion. Model output never
assigns a verdict. No inference occurs in automated tests or CI.

## Authorized smoke update (2026-10-27)

The subsequent single authorized Wonder request returned HTTP 200 but its graph
failed source-span validation. SAM was therefore not dispatched. Both paid gates
are disabled; the consumed authorization cannot be reused. Reported token usage
estimates $0.051884, while the ledger conservatively retains $4.276224. See
[the live smoke record](meta-smoke.md) for sanitized evidence and limitations.
Earlier no-inference/unapproved statements below describe historical milestones.

## Milestone 4 verified status

On 2026-10-27 at 13:28:44 UTC (20:28:44 Bangkok), the implemented backend
transport successfully authenticated one `GET /v1/models` using the local root
`.env`. The account catalog listed `sam-3.1`, `muse-wonder-1.0` and
`muse-spark-1.3`. See the sanitized `meta-discovery-result.json`. This establishes
catalog access, not successful inference. **No inference POST was sent; API
spending is $0.** Historical credential/access statements below describe earlier
milestones and are superseded by this result.

The live HTTP implementation uses Python's TLS-validating HTTPS client with a
fixed `api.meta.ai` origin, no redirect following, 30s socket timeout, 120s
elapsed read cutoff, 96MiB request and 32MiB response limits. Nonstreaming only;
unexpected SSE responses are rejected. Requests are serialized, never retried
automatically, and blocked in CI/pytest. The separate SSE contract helper rejects
truncated streams but is not a production streaming adapter.

Text adapters use the documented `/v1/chat/completions`, `max_completion_tokens`,
strict `response_format.json_schema`, assistant content, exact model/finish checks,
and usage fields already documented below. Wonder uses `muse-wonder-1.0`; Spark
uses Standard `muse-spark-1.3`, not a Contributor variant. Spark's documented
`image_url` content part contains `image_url.url` with local JPEG base64 data URLs:
[image understanding](https://dev.meta.ai/docs/image-understanding) and
[chat schemas](https://dev.meta.ai/docs/api-reference/chat-completions/schemas).

Both paid server gates default false: `META_ENABLE_PAID_INFERENCE` and
`META_SMOKE_TEST_APPROVED`. Fresh authenticated catalog discovery is required
when starting an enabled server; possessing a key alone does not enable a model.
The current session has no permission to set those flags or make inference calls.

Before dispatch, the persistent lifetime ledger reserves a verified upper bound:

| Request | Conservative reservation |
|---|---:|
| SAM video, at most 720 decoded frames, forward from frame zero | 144,000 micro-USD ($0.144000) |
| Wonder, 1,048,576 input-token ceiling plus 4,096 output ceiling | 4,276,224 micro-USD ($4.276224) |
| Spark, same context/output ceilings | 1,328,128 micro-USD ($1.328128) |

These intentionally use the entire published context ceiling, including request
schema and multimodal overhead, rather than an unverified characters/token
estimate. The accepted request is context-limited; output is explicitly capped.
Tools/search, multiple completions, automatic retries and remote video URLs are
not supported. SAM's real transport independently decodes inline video and checks
24fps/1280x720/720-frame bounds before reserving and sending it.

Settlement occurs only after the adapter validates a successful response and
acknowledges it. Missing, invalid or excessive usage, malformed output, timeout
and uncertain requests retain their full reservation. Exact verified token costs
include documented cache discounts, with integer upward rounding; missing cache
detail is uncertain. SAM uses the documented `usage.video_frames_processed`,
minimum 50, at 200 micro-USD/frame. Spark Standard rates are $1.25/M input,
$0.15/M cached input and $4.25/M output. Source: current
[pricing](https://dev.meta.ai/docs/pricing-rate-limits).

A minimal Wonder+SAM smoke test (one compilation, one bounded video, no Spark
and no retries) therefore has a conservative maximum/reservation of
**$4.420224**. Actual verified usage may be much lower, but has not been measured.
Adding one optional Spark final-state request raises the ceiling to $5.748352.
**Explicit human authorization is still required before either test.**

## Milestone 4 pre-dispatch record (2026-10-27)

Re-read current official API reference, models listing schema, SAM overview,
prompt/output guides and pricing. `GET https://api.meta.ai/v1/models` uses
`Authorization: Bearer MODEL_API_KEY`; its JSON response is `object: list` and
`data` containing `id`, `object: model`, `created`, `owned_by` (optional metadata).
This is a catalog read with no generation input. Published pricing meters model
inference, not model catalog reads. Only this non-inference discovery request is
authorized in this session. No inference POST is authorized.

Sources read before dispatch:
- https://dev.meta.ai/docs/api-reference/models/list-models
- https://dev.meta.ai/docs/api-reference/models/schemas
- https://dev.meta.ai/docs/pricing-rate-limits

The local credential file was named `.env.txt`; it was renamed to `.env` without
printing its contents. Presence, Git exclusion and untracked status were verified.
Possession of this key is not evidence of any model entitlement. Discovery result
and actual adapter status will be recorded below after verification.

Checked 2026-10-27 (Asia/Bangkok). Status: public documentation verified;
authenticated account access and execution unverified. Live compilation remains
disabled. No inference call was made and API spend is $0.

## Sources

- [Overview](https://dev.meta.ai/docs/overview)
- [Muse Wonder](https://dev.meta.ai/models/muse-wonder)
- [Models and availability](https://dev.meta.ai/docs/models)
- [API reference and authentication](https://dev.meta.ai/docs/api-reference)
- [Create chat completion](https://dev.meta.ai/docs/api-reference/chat-completions/create-chat-completion)
- [Request, response and usage schemas](https://dev.meta.ai/docs/api-reference/chat-completions/schemas)
- [Structured output](https://dev.meta.ai/docs/structured-output)
- [Pricing and rate limits](https://dev.meta.ai/docs/pricing-rate-limits)

These are official public documentation pages, not evidence of entitlement for
this account. Some rendered pages also contain an identity-confirmation prompt;
their documented contract content was readable without signing in.

## Model and availability

The model catalog lists `muse-wonder-1.0` for Model API, including structured output.
It documents a 1,048,576-token context window. Wonder Full is a separate Muse Code
subscription offering, not a Model API model. Availability is restricted in South
Korea. This project has not authenticated to the models endpoint to check account
availability. Source: [model catalog](https://dev.meta.ai/docs/models).

## Proposed transport contract

For future text-only compilation use `POST https://api.meta.ai/v1/chat/completions`
with `Authorization: Bearer <server-side MODEL_API_KEY>` and JSON content type.
The documented request contains `model`, `messages`, `max_completion_tokens` and
`response_format`. Request one nonstreaming completion, without tools. Sources:
[API authentication](https://dev.meta.ai/docs/api-reference) and
[endpoint](https://dev.meta.ai/docs/api-reference/chat-completions/create-chat-completion).

Use `response_format.type = "json_schema"` with a `json_schema` object containing
`name`, `schema`, and explicit `strict: true`. Strict schemas require a plain object
root, every property required and every object closed to additional properties.
Nested `anyOf` is allowed; `oneOf` and `allOf` are not. Pydantic's default
discriminated-union schema therefore needs a verified transport-schema conversion,
while local validation must retain the strict application contract. The guide
also imposes depth and expansion limits. Source:
[structured output](https://dev.meta.ai/docs/structured-output).

## Response validation

The response envelope documents `id`, `object`, `created`, `model`, `choices` and
optional `usage`. Extract JSON from `choices[0].message.content` only after checking
one choice, assistant role, no refusal and a successful finish reason. Reject
truncation, tool calls and content filtering. Then validate TaskGraph v2 in
Pydantic, including references, cycles and source grounding.

Usage fields are `prompt_tokens`, `completion_tokens`, `total_tokens`, optional
`prompt_tokens_details.cached_tokens`, and optional
`completion_tokens_details.reasoning_tokens`. `max_completion_tokens` covers
reasoning and visible output together. Usage is optional; never replace missing
usage with zero. Source:
[schemas](https://dev.meta.ai/docs/api-reference/chat-completions/schemas).

## Price and limits

The pricing page lists Standard-mode Wonder rates per million tokens: $4 input,
$0.20 cached input and $20 output. Contributor mode is unavailable for Wonder on
Model API. Team limits are 3,000 requests/minute and 4,000,000 tokens/minute.
Recheck prices before enabling dispatch; account-specific access remains
unverified. Source: [pricing](https://dev.meta.ai/docs/pricing-rate-limits).

Use integer micro-USD for accounting. A conservative reservation ignoring cache discount
is `4 * verified_max_input_tokens + 20 * max_completion_tokens` micro-USD.
This is a local calculation from the published rates, not a token-counting
guarantee. The maximum input count must cover all billed request material; no
verified maximum means no paid dispatch. Do not claim a characters-to-tokens
heuristic is a verified bound.

Offline tests also exercise actual-usage calculation with the published cached
rate: `4*(prompt_tokens-cached_tokens) + ceil(cached_tokens/5) + 20*completion_tokens`
micro-USD. Settlement requires an explicit cache breakdown; unavailable detail
retains the bound. Rounding upward avoids floating-point money. These synthetic
usage examples do not establish actual live billing or a verified live input bound.

Every retry requires its own pre-dispatch Store reservation. Missing, inconsistent
or excessive usage retains the full reservation; failures do not erase budget.
Only verified actual usage within the reservation may be settled. The local
lifetime $100 gate does not guarantee all Meta billing charges are bounded.

## Access and implementation status

Available-tool discovery found no Muse inference connector. The known server key
environment variables are absent in this process, and the repository contains
only `.env.example`. No unrelated credentials were inspected. No authenticated
model listing or paid smoke test was attempted. Public documentation access does
not prove authentication or model entitlement.

Milestone 2 implements the provider-neutral response validation boundary and
mocked HTTP contract tests. Its concrete OfflineTransport consumes fixture bytes,
with no HTTP client or credential handling. Live dispatch remains disabled until account
access and a conservative request-cost bound are verified. Mocked HTTP responses
are synthetic contract examples, not recorded live outputs or proof of working
Muse access. Uploaded video verification remains mocked regardless of compiler
status.

## Milestone 4.1 recheck — 2026-10-28

Re-read official [SAM pricing](https://dev.meta.ai/docs/pricing-rate-limits),
[segmenting](https://dev.meta.ai/docs/sam/segmenting), and
[output grammar](https://dev.meta.ai/docs/sam/reading-segmentation) without an
inference request. Pricing documents 50 minimum billed video frames, $0.20/1000
frames, and `usage.video_frames_processed` as billed frames. Forward tracking from
the earliest prompt reaches the end once; nonstreaming is supported. Therefore a
verified 72-frame video with frame-zero forward box prompts reserves 14,400
micro-USD. The transport validates submitted bytes, dimensions and exact prompt
range before accepting that smaller bound. See [reviewed plan and limitations](milestone-4.1-report.md).
Prior historical access statements in this file describe their original milestone;
the 2026-10-27 authorized run did authenticate successfully but failed compilation.
No new account/entitlement probe was performed in the 4.1 offline work.

## Milestone 4.2 live validation — 2026-10-28

The explicit request to complete live integration authorized the prepared SAM
attempt and further bounded validation/debugging. SAM masks decoded successfully;
Wonder+SAM API uploads now demonstrate PASS, FAIL and honest UNKNOWN; Spark final
color-state evidence also reaches deterministic PASS. Failed responses remain
rejected with reservations retained. All input clips are generated; genuine
camera validation is still unverified. See
[the full live report](milestone-4.2-live-report.md) and
[all actual capture receipts](live-validation/index.json). Historical
unapproved/no-inference statements above describe their original milestones.
Persistent root `.env` flags remain false; the bounded local server demonstration
uses explicit process-only flags. Current official contracts/prices were re-read
before these calls, including the documented minimal reasoning control.
