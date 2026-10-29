# Finished demo production

The local [MP4](reality-compiler-demo.mp4) was exported with installed Playwright/Chromium, bundled FFmpeg and Windows Microsoft Zira speech. No dependency was installed for recording, and no external generation, speech, editing or hosting service was invoked.

It is an edited real-application recording. Source input is generated. Original Wonder and SAM outputs are preserved captures reviewed offline; newly entered procedures compile locally. The selection chapter is an explicitly labeled historical application still from the earlier generated-input flow. There is no fabricated UI, verdict, model activity, waiting animation or physical-camera validation. Editorial titles, provenance labels and captions occupy margins outside the recorded UI.

The source-frame chapter uses a **separate new local-CV upload** and says No SAM. It does not claim historical Meta source mapping. The provider provenance retains an observer module identifier containing Spark; narration and the application explicitly explain that Spark did not contribute to this ordering comparison. Its bounded final-state results exist in other captured runs.

## Artifacts

- Final film and exact SHA-256/size: [video-manifest.json](video-manifest.json).
- Spoken script, chapter titles and pacing: [narration.json](narration.json).
- External and burned-in captions: [captions.srt](captions.srt).
- Fresh application screenshots: [screenshots](screenshots/opening.jpg).
- Raw browser recordings, local WAV narration, scene timings and ASS files: `output/demo-production/` in the original workspace, untracked and not in the source bundle. Earlier recording takes are preserved.

## Reproduction tools

1. Follow judge setup, import a **fresh** review, and keep both gates false. Prepare a separate generated local-CV run through real upload and frame-zero selections if reproducing the source-inspection chapter.
2. Run [narrate_demo.ps1](../../scripts/narrate_demo.ps1) on Windows with the installed Microsoft Zira voice. `uv run python -m scripts.render_demo --prepare` measures narration and prepares scene durations. Speech is local synthetic narration, not a human recording. Respect the local script execution policy; do not change persistent policy for this project.
3. Use an already installed `playwright` module and Chromium. Set process `NODE_PATH`, `PLAYWRIGHT_BROWSERS_PATH`, `DEMO_CHROMIUM`, `DEMO_URL`, `DEMO_RUN` and `DEMO_CV_RUN` to existing runtime paths and the isolated loopback runs. Then run `node scripts/record_demo.cjs`. The script installs nothing, rejects non-loopback origins, blocks external browser requests and asserts actual verdicts, empty new usage, unchanged ledger/fingerprints and mobile layout. It appends two local revisions; use a new import for a new filming session.
4. `uv run python -m scripts.render_demo` edits actual recorded scenes, inserts the labeled historical still, burns captions, adds normalized local narration and exports H.264/AAC. It decodes the entire export before recording a hash. Existing source media/captures are never rewritten.

The optional recording tooling requires a preinstalled browser/Playwright and Windows voice. These are not new app dependencies or requirements for judge reproduction. When unavailable, judges can still run the normal application and replay. Final film hosting requires separate approval.

## October 29 editorial review

Preserve the existing **145.621-second** export unchanged. Its hash still matches,
full audio/video decoding passed again, and eleven chapter samples were freshly
extracted and inspected alongside the complete narration/captions. Chrome also
reported 1920×1080 playback with no media error.

The new trio adds useful *supplementary* evidence: a changed video with observed
reverse order, plus conservative invalidation by an occluder. It does not add Meta
model use. Inserting three local-CV clips and their necessary caveats into this film
would split its concise same-evidence revision story and reduce time spent showing
actual captured Wonder/SAM contributions. The existing film already demonstrates
compilation, tracking, timestamped proof, source inspection, compatible reuse and
explicit UNKNOWN. The stronger submission is the unchanged film plus the downloadable
trio and [audited findings](synthetic-validation.md). The new clips are not depicted
as being in the existing film; no re-recording or new footage is required.
