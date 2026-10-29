# Synthetic trio delivery and validation — October 29, 2026

Three separate generated clips were uploaded and initialized through the **real loopback HTTP API**, processed by the actual local OpenCV pipeline, and then inspected in the real Chrome application. This is synthetic regression validation, not physical-camera acceptance, SAM inference or a fixture verdict.

| Clip | Actual result | Supporting observations |
|---|---|---|
| `correct.mp4` | PASS | Block `cv_object1_region1_50_54_0`, 4.000–4.667 s; cup `cv_object2_region1_108_111_0`, 8.833–9.417 s |
| `reverse.mp4` | FAIL | Cup `cv_object2_region1_48_51_0`, 3.833–4.417 s; block `cv_object1_region1_110_114_0`, 9.000–9.667 s. Both entries pass individually; positive disjoint observations prove the opposite order. |
| `occlusion.mp4` | UNKNOWN | No decisive event evidence. Both identities become invalid at normalized frame 66 / 2.750 s through the clip end. |

These are supporting intervals, not interchangeable with narrower predicate-transition bounds. See the exact observations and bounds in [the machine-readable audit](synthetic-validation.json).

The occluder triggers the coarse scene-motion heuristic. It can invalidate an unobstructed object too, cannot distinguish an occluder from camera motion, and cannot verify camera immobility. This result demonstrates conservative invalidation; it does not establish robust occlusion recognition or identity recovery. Region entry remains image geometry, not physical containment.

## Browser scope and limitation

Verified in Chrome: all three actual job results and explanations; reliable identity overlays on the unoccluded cases; absent overlays after occlusion invalidation; evidence-link seeking; saved supporting-frame links; source-frame inspection; reversed-clip and occlusion playback. Correct-order video playback was subsequently checked separately. The correct clip was re-evaluated through the UI with an independently typed reversed requirement (FAIL), then added sterility (UNKNOWN). Both reused the same fingerprint without inference. Full original job JSON and the original evaluation were compared before/after; both remained identical. Earlier revisions remained present.

The original procedure was also re-evaluated through the UI on each clip, confirming
PASS / FAIL / UNKNOWN independently of merely displaying the API-created originals.
These are new evaluations over compatible saved perception, not new uploads/tracking.
All three exact Downloads MP4 copies played in Chrome via a loopback-only file server:
15 seconds, 1280×720, no media errors. [Playback observations](downloads-playback.json).

**Full browser-upload/selection coverage is incomplete.** The ChatGPT Chrome extension's chooser refused local files because “Allow access to file URLs” is disabled. No extension permission was changed. A native fallback failed with `coordinate input geometry is unavailable`; its screenshot did not match the targeted Chrome window, so native input stopped. Uploads and frame-zero initialization used the real HTTP API instead. Do not describe this as three successful UI uploads. This environment limitation does not invalidate the retained API results or browser inspection.

Direct range `fill` did not seek in this browser-control path. Keyboard arrows and the returned mapping confirmed the actual seek; no application code or thresholds were changed. One full-page screenshot timed out; viewport captures succeeded. Source decoding completes asynchronously, so the definitive mapping is the returned source inspector text/API audit, not a screenshot taken before its image updated.

Source checks: correct normalized frame 96 → original frame 120 / 4.000 s; reverse 92 → 115 / 3.833333 s and 216 → 270 / 9.000 s; occlusion 66 → 83 / 2.766667 s. Normalized and original times intentionally differ at some frame rates. Every source SHA-256 matches the actual uploaded file.

[Source inspection](synthetic-screenshots/correct-source.jpg) · [preserved PASS and revised UNKNOWN](synthetic-screenshots/correct-unknown.jpg) · [reverse source](synthetic-screenshots/reverse-source.jpg) · [occlusion source](synthetic-screenshots/occlusion-boundary.jpg). Images show only generated pixels/application UI.

## Delivered Windows files

All files are in `<submission-folder>`:

- `correct.mp4`, `reverse.mp4`, `occlusion.mp4`
- `Reality-Compiler-Synthetic-Videos.zip` — exactly the three MP4s, `manifest.json` and `READ-ME.txt`
- `manifest.json`, `READ-ME.txt` — provenance, expected results, procedure and frame-zero boxes

Each MP4 is 15 seconds, 1280×720, 30 fps, H.264, silent. Full FFmpeg decoding and 450-frame OpenCV decoding passed. ZIP CRC, extraction and every extracted-file hash passed. Copied Downloads files match. [Integrity manifest](synthetic-delivery-manifest.json).

```powershell
$delivery = '<submission-folder>'
explorer.exe $delivery
Start-Process (Join-Path $delivery 'correct.mp4')
Start-Process (Join-Path $delivery 'reverse.mp4')
Start-Process (Join-Path $delivery 'occlusion.mp4')
Start-Process (Join-Path $delivery 'Reality-Compiler-Synthetic-Videos.zip')
```

The originals remain under `recordings/synthetic/`; they are ignored local files, not files hosted by GitHub.

## Reproduce

From the repository root, with locked dependencies installed and both paid gates false:

```powershell
$env:UV_CACHE_DIR = Join-Path (Get-Location) '.uv-cache'
uv run python -m scripts.generate_synthetic_trio
uv run python -m scripts.evaluate_synthetic_trio
```

This generates and verifies real uploads, exact media hashes, 24 fps normalization, 12 Hz samples including endpoints, actual verdicts, evidence availability, zero Meta dispatch and an unchanged existing ledger in a fresh isolated store. Reports are written below ignored `output/synthetic-trio/`. It is an API harness, not a browser test.

For UI reproduction, start a single paid-disabled local server using the judge instructions, upload each generated video with **Generated demonstration** and **Local OpenCV**, keep the exact procedure from the manifest, draw its frame-zero boxes, and inspect the results. The delivered archive also includes these inputs under `docs/submission-final/synthetic-videos/`; copying to ignored `recordings/synthetic/` or regenerating enables the API harness.

The fresh inspection server's isolated store is `output/submission-readiness/browser-data`; the URLs/IDs in the JSON work only with that local store. Restarting it requires `DATA_DIR` pointing there, `PROVIDER_MODE=local_cv`, `META_COMPILER=local_rules`, both paid gates false and `uv run uvicorn backend.app.main:app --host 127.0.0.1 --port 8010`. The store is excluded from public delivery. Public judges create new IDs.
