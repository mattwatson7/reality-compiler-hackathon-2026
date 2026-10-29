# Milestone 4: Meta integration

2026-10-27, Asia/Bangkok. Stacked on Milestone 3; PR #2 is not merged.

## Implemented

- Secure server-side root `.env`/process loading with redacted secret objects.
  `.env`, filename variants and Docker context are excluded; no key is tracked or
  sent to the frontend. The user's Windows `.env.txt` was renamed to `.env`
  without displaying or changing the value. Presence/Git checks passed.
- Explicit non-inference discovery CLI; no network at import/default startup,
  and no Meta API requests allowed in CI/pytest. One actual authenticated catalog
  read listed SAM 3.1, Wonder 1.0 and Spark 1.3. All inference remains unverified.
- Fixed-origin bounded HTTP transport, no redirect/retry, one active request,
  disabled-by-default paid gates, model entitlement checks, independent request
  cost validation and existing persistent $100 ledger. Failed/unknown requests
  retain full integer reservations; successful adapter validation and complete
  usage are required to settle. Audit records include model/reserved/actual cost.
- `SAMTrackerProvider` builds real documented frame-zero box requests and decodes
  one-bit segmentation into provider-neutral tracks, contours and region overlap.
  Missing frames, bad IDs/masks, occlusion/loss and confidence uncertainty cannot
  prove events. Model output never determines the final verdict.
- `LiveMuseWonderCompiler` requests strict TaskGraph v2 from natural language,
  validates schema, references, source and clause coverage, and rejects known
  hidden-property clauses that have lost their unsupported requirement. No retry.
  Source traceability is not a semantic-faithfulness guarantee; inspect the graph.
- Opt-in `MuseSparkObserver` handles only explicitly supported final visibility or
  visual-state requirements, using actual frame zero/final six JPEGs and tracked
  object boxes. Exact predicates/IDs/indices and unbroken reliable tracking are
  required. Missing/unsupported claims remain UNKNOWN. Spark never supplies region
  events, repairs identity loss or overrides deterministic order.
- Studio selector distinguishes Local OpenCV (no Meta model), disabled/enabled
  Meta SAM and synthetic fixtures. Per-observation/model provenance, actual saved
  frames, overlays, quality and usage/reservations remain inspectable. No silent
  fallback after paid failure: explicitly rerun Local OpenCV, preserving the audit.
- Recording harness adds `--provider meta_sam`, using the same lifetime ledger,
  gates and adapter. The default remains local_cv. No genuine clips are bundled.

## Setup and authorization

Keep both flags **false** in this session. No paid authorization has been given.

```dotenv
MODEL_API_KEY=your-server-side-key
META_ENABLE_PAID_INFERENCE=false
META_SMOKE_TEST_APPROVED=false
META_COMPILER=local_rules
META_SPARK_VISUAL=false
PROVIDER_MODE=fixture
```

Confirm catalog access without printing credentials or generating content:

```powershell
uv run python -m scripts.meta_discovery --output data/meta-discovery.json
```

The backend reads the root key even when the shell does not inherit it. Process
environment takes precedence. Root `.env` also supplies Meta feature flags; use
the existing uvicorn `--env-file .env` option for other deployment settings.
No credentials or discovery calls are required for Local OpenCV or fixtures.
After a separately approved smoke test, enabling both flags makes startup perform
fresh catalog discovery; only listed models become selectable. Set
`META_COMPILER=muse_wonder` for SAM-job compilation, optionally
`META_SPARK_VISUAL=true` for supported final-state claims. Local OpenCV uploads
always keep local compilation and geometry, regardless of Meta settings.

See [contracts](meta-api-contracts.md) for current sources, prices and verified
reservations. One Wonder+SAM test, no retries/Spark, reserves at most **[private historical cost]**;
one optional Spark request adds [private historical cost]. Actual usage is not yet measured.
The conservative ceiling uses the whole documented context window for token
overhead. Unknown bills retain this bound, so expect the ledger to remain
conservative if usage detail is unavailable.

## Validation and genuine limitations

Adapter/network-policy tests use synthetic envelopes and in-memory transports.
The official codec conformance vector is synthetic too. No paid test/CI request
is possible through the real transport. Final local checks and GitHub CI are
reported against the delivery commit in the PR/handoff.

Local final checks: **238 backend tests**, Ruff lint/format, strict mypy,
**16 frontend tests**, ESLint, TypeScript and production build all passed.
`npm audit --audit-level=moderate` found zero vulnerabilities. Exact credential
value scanning of project files and built frontend returned clean without
printing the value. One upstream Starlette/httpx deprecation warning remains.
Local Docker build is unavailable because Docker Desktop's Linux engine pipe
is missing; the GitHub workflow includes its build. Workspace uv cache and the
existing virtual environment were used; nothing was installed locally.

Browser smoke verified the actual catalog status, disabled paid inference,
disabled SAM option, and enabled OpenCV/fixture controls. Screenshot:
`output/playwright/milestone4-disabled-meta-status.png`.

Actual live activity: one authenticated `GET /v1/models`; **zero inference calls,
zero API spend, no weights, no new installed dependencies**. Live inference,
model output/billing compatibility and real-world PASS/FAIL/UNKNOWN remain
unverified. Catalog listing is not proof that an inference will succeed.

Capture the three physical recordings in [recording-capture.md](recording-capture.md)
and retain provenance/hash-bound boxes. Then, after explicit paid authorization,
run the same manifest with `--provider meta_sam`. Never count generated clips or
mocked SAM outputs as genuine recording success. Static selected image regions
still assume a fixed camera; occlusion or identity ambiguity is nondecisive.

Material integrations: official Meta docs and authenticated Meta model catalog;
GitHub connector for stacked PR/CI. No OpenAI, SAM SDK or other model service was
used as a substitute for actual Meta access.
