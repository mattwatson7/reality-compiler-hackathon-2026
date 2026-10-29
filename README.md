# Reality Compiler

**Describe what should happen. Show what happened. Prove whether they match.**

[Watch the 2:26 demo](https://www.youtube.com/watch?v=H0gd17Sj3N8)
— generated input, actual captured Meta evidence, and local procedure revisions.

Reality Compiler compiles written physical procedures into typed requirements and
checks them against timestamped visual evidence. A deterministic evaluator explains
**PASS, FAIL or UNKNOWN**. Compatible revisions reuse preserved observations while
keeping earlier evaluations immutable.

This standalone hackathon release contains a new source snapshot, generated demo
inputs and reviewed historical model evidence. It contains no private repository
history, credentials, runtime database or private camera footage.

## Demonstration and Meta integration

The recorded walkthrough reviews actual previously captured **Muse Wonder 1.0**
semantic compilation and **SAM 3.1** masks/tracks on generated input. New procedure
revisions compile locally and reuse compatible visual evidence. **Muse Spark 1.3**
supports bounded visible final-state interpretation in separate captured examples;
it did not contribute to the generated ordering comparison. Offline reproduction
makes no new inference requests and needs no Meta key. Paid dispatch defaults off.

- [Reproduce the walkthrough](docs/submission-final/judge-reproduction.md)
- [Architecture and model provenance](docs/submission-final/architecture.md)
- [Three synthetic local-CV cases](docs/submission-final/synthetic-validation.md)
- [Official contract research and adapter boundaries](docs/meta-api-contracts.md)

The separate generated correct/reverse/occlusion videos reproduce PASS, FAIL and
UNKNOWN through real upload APIs and local OpenCV. This is a saturated-color
fixed-camera baseline. Synthetic success is not physical-camera acceptance. Region
entry does not prove insertion or containment. The coarse scene-motion guard can
invalidate occluded identities; it does not prove that a camera moved. End-to-end
native browser uploads are not yet verified.

## Install and run

Requires Python 3.12, uv, Node.js 22.12+ and npm. Dependencies are locked; FFmpeg is
supplied by imageio-ffmpeg. No model download, GPU or Meta credential is needed.

```sh
uv sync --frozen --group dev
npm --prefix frontend ci
npm --prefix frontend run build
uv run uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. The bundled fixture buttons are declared synthetic
fixtures. For actual local pixel processing, select Local OpenCV and Generated
demonstration, upload a generated MP4 and select objects/region in frame zero.
The capture-review guide above imports historical Meta evidence into a fresh local
audit directory and explains independently entered revisions.

Configuration belongs in root `.env` or process variables. `.env.example` contains
placeholders only. Keep keys server-side, never in `VITE_*`. Do not enable paid
flags for this walkthrough. Preserve an existing data directory and its ledger.
The application is for trusted local use, with one server process and two workers;
it is not an authenticated hosted service. Docker users may use
`docker compose up --build` and must preserve the data volume.

## Validation

```sh
uv run pytest --basetemp .pytest-tmp -q
uv run ruff check .
uv run ruff format --check .
uv run mypy
npm --prefix frontend test
npm --prefix frontend run lint
npm --prefix frontend run typecheck
npm --prefix frontend run build
uv run python -m scripts.replay_milestone5
```

The audited implementation passed 357 backend and 23 frontend tests, lint,
formatting, types and build. Hosted CI also passed Docker build and a running
container smoke with paid inference disabled. Replay verifies all 17 captured
response hashes. The generated trio has fresh API evidence for PASS/FAIL/UNKNOWN.
Historical milestone documents describe their states at the time; this README and
the final reproduction guide describe the release. Private cost summaries are
removed from the public snapshot; raw model usage/provenance receipts are retained.

## Rights and dependencies

No project-wide license grant has been selected. Public source visibility does not
itself grant a broad reuse license. Third-party dependencies retain their own
licenses; see [dependency inventory](THIRD_PARTY_NOTICES.md). No installed dependency
code or FFmpeg binary is committed. Original private camera media is excluded.
