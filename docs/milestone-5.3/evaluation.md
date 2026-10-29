# Offline ingestion and human review

No new dependency, paid dispatch, gate change or ledger reset is needed. Work from
the repository root. Originals remain under ignored `recordings/`; preparation
writes new ignored directories. Never overwrite a prior study or its annotations.

## Before model inference

1. Copy original camera bytes once into the filenames in [acquisition](acquisition.md).
   Preserve the device filename and capture/rights notes separately. Compute hashes:

```powershell
Get-FileHash recordings/controlled/*.mp4 -Algorithm SHA256
Copy-Item docs/milestone-5.1/controlled-manifest.example.json recordings/controlled/manifest.json
```

2. Watch the entire originals, including first and final frames. Replace every
   placeholder with actual capture date/timezone, operator, rights evidence, hashes
   and observed intervals. The scheduled action times are instructions for recording,
   **never ground truth**. Record partial/full occlusion and uncertainty, object
   identity and boundary crossings. Freeze one instruction for all three cases.
   Annotation is kept separate from tracker observations and actual verdicts.
   Use the [unfilled human review worksheet](human-review-template.md) to retain
   the independent pre-inference notes and separate post-evaluation findings.

```powershell
uv run python -m scripts.controlled_recordings --preflight recordings/controlled/manifest.json
uv run python -m scripts.controlled_recordings --freeze recordings/controlled/manifest.json --output recordings/controlled/frozen-expectations.json
```

Retain the printed SHA-256 with an independent dated reviewer record. Local hashes
detect changes against that receipt; they are not tamper-proof notarization.
Preflight rejects placeholders, wrong hashes, non-original fixtures and bad media.
It does not establish authenticity or guarantee model coverage.

3. Prepare independently normalized video/frame zero without compiling or inference:

```powershell
uv run python -m scripts.evaluate_recordings --prepare recordings/controlled/correct.mp4 --output output/m53-correct
uv run python -m scripts.evaluate_recordings --prepare recordings/controlled/reverse.mp4 --output output/m53-reverse
uv run python -m scripts.evaluate_recordings --prepare recordings/controlled/occlusion.mp4 --output output/m53-occlusion
```

Each new directory has `prepare.json`, `video.mp4`, `video.timing.json` and saved
frame zero. Source bytes remain unchanged. Metadata binds both hashes. Normalized
frame index i maps to time i/24; use `video.timing.json`'s source frame/PTS mapping,
including duplicates and dropped frames. Never infer source PTS as i/native-fps.
Mapping is decoder provenance, not proof of object identity. Older captures retain
their explicit unmapped status; do not backfill invented source times.

For exhaustive frame inspection, use the installed FFmpeg binary (shown by
`uv run python -c "from backend.app.media import ffmpeg_binary; print(ffmpeg_binary())"`).
Set `$ffmpegPath` to that path, then extract all normalized frames:

```powershell
New-Item -ItemType Directory output/m53-correct/all-frames
& $ffmpegPath -nostdin -i output/m53-correct/video.mp4 -vsync 0 -start_number 0 output/m53-correct/all-frames/%06d.png
```

Repeat for reverse/occlusion. Frame `000000.png` is normalized index zero. Inspect
all crossing/occlusion windows one frame at a time, not just thumbnails. For source
inspection use the actual application's source-frame link and mapping metadata;
source time and normalized time are different coordinates.

## Evaluation and result review

Use the normal browser upload/selection flow in **local_cv** mode for a free
baseline, with local compiler and both paid gates disabled. Select objects/region
on that upload's immutable normalized frame zero using compiled IDs. Never inject
human event times or reuse selections against a different normalization hash.
Local HSV color tracking is not SAM. A local result is not full live Meta acceptance.

Export each completed job JSON and its exact normalized video, saved evidence
frames, timing map and masks before playback expiry. After replacing `SEAL` with
the independently retained freeze digest:

```powershell
uv run python -m scripts.controlled_recordings --import-result recordings/controlled/correct-job.json --frozen recordings/controlled/frozen-expectations.json --seal SEAL --case correct --normalized recordings/controlled/correct-video.mp4 --output recordings/controlled/correct-import.json
```

Repeat with reverse and occlusion names. The importer independently reruns the
deterministic evaluator, validates IDs, hashes, instruction and provider provenance,
then compares actual versus frozen expected verdict. It keeps acceptance pending:
an untrusted export cannot establish that its claimed live provenance is genuine.
Keep all mismatches. Human review must inspect masks, geometry, identity continuity,
sampling gaps, final clip coverage and each decisive evidence/time/source mapping.
Record reviewer/date, original and normalized hashes, freeze seal, run IDs, compiler,
tracker and observer separately. Never turn UNKNOWN into PASS to satisfy coverage.

The stronger Wonder→SAM→optional Spark live workflow remains gated and is not run
here. Any future paid evaluation needs current official contract/cost checks and
bounded ledger reservation; a vendor credit balance is not a reason to bypass caps.

## Existing reproducible evidence

```powershell
uv run python -m scripts.replay_milestone5
```

This checks historical response hashes and deterministic results without network
or model calls. It does not create new real-camera evidence. Follow the preserved
[judge walkthrough](../submission-final/judge-reproduction.md) for the generated
demo; no controlled camera file is needed to submit that honestly labeled work.
