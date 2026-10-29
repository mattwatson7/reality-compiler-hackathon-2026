# Reality Compiler delivery — October 29, 2026

Everything for review is in **<submission-folder>**.

| File/folder in that directory | Purpose |
|---|---|
| `correct.mp4`, `reverse.mp4`, `occlusion.mp4` | Three actual generated 15-second inputs; Chrome playback and full decoding verified |
| `Reality-Compiler-Synthetic-Videos.zip` | Verified five-entry ZIP: the three MP4s, manifest and explanation |
| `reality-compiler-demo.mp4` | Selected unchanged narrated film; 145.621 s / 1920×1080 / H.264 + AAC |
| `captions.srt` | Timed captions; film also has burned-in captions |
| `reality-compiler-source.zip` | Sanitized source and generated reproduction assets, no private Git history or runtime database |
| `public-source` | Fresh extraction of exactly the source ZIP contents, ready for an approved new public repository |
| `submission-copy.md` | Complete prepared narrative answers and exact portal field mapping |
| `publishing-instructions.md` | Exact separate-repository and unlisted-YouTube steps, requiring release approval |
| `source-package-manifest.json`, `video-manifest.json`, `synthetic-delivery-manifest.json` | Integrity and exclusion records |

```powershell
$delivery = '<submission-folder>'
explorer.exe $delivery
Start-Process (Join-Path $delivery 'correct.mp4')
Start-Process (Join-Path $delivery 'reverse.mp4')
Start-Process (Join-Path $delivery 'occlusion.mp4')
Start-Process (Join-Path $delivery 'reality-compiler-demo.mp4')
Start-Process (Join-Path $delivery 'Reality-Compiler-Synthetic-Videos.zip')
Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $delivery 'reality-compiler-demo.mp4')
```

Demo SHA-256: `d83ed0ade7c63427dff898d297a5e86465d8265ce0c2a8c8b75ac8e139a69e5b`.
The film remains unchanged because it clearly demonstrates actual captured Wonder/SAM
contributions and same-evidence revisions; the separate trio provides supplementary
local-CV regression evidence without confusing the model provenance.

The real HTTP pipeline produced correct-order PASS, reverse-order FAIL supported by
cup-first evidence, and occlusion UNKNOWN. Chrome inspected each result, source mappings,
diagnostics and timestamps, and re-evaluated all three through the UI. Original jobs and
evaluations remained immutable. Full UI upload/selection is **not verified**: extension
file access was disabled and native input geometry failed; no permission was changed.
Occlusion triggers coarse scene-motion invalidation from 2.750 s; this cannot prove
camera movement or robust occlusion classification. See `synthetic-validation.md` and
the matching JSON in `public-source/docs/submission-final/` for the full audit.

357 backend tests, 23 frontend tests, lint/format/types/build, offline replay and npm
audit passed. Hosted baseline CI `cafb74c` passed, including Docker build/container smoke;
the subsequent local documentation delivery is not claimed to have its own hosted run.
The extracted source reproduced the trio using the existing dependency environment.
GitHub and authenticated Chrome materially contributed; official Meta event information
was checked. No fresh Meta inference or account-entitlement verification occurred.

Use the answers at [Submit Project](https://cerebralvalley.ai/e/meta-ai-developer-hackathon/hackathon/submit).
The remaining required entrant actions are: approve publication of the sanitized source
to a separate public repository; approve demo hosting on the chosen channel; confirm team,
eligible track and rights; personally review the rules/publication permission and authorize
or perform final submission. The actual public repository and watch URLs do not exist yet.
No further footage, packaging or development is required for this truthful submission.

Deadline rechecked October 29: **November 5, 2026, 09:00 Bangkok**, according to the
[official Meta event page](https://dev.meta.ai/events/global-hackathon).
Paid gates remain false; lifetime exposure remains **[private historical cost]**, all 63 reservations
preserved. PR #2 and PR #3 remain unmerged. Nothing was published, uploaded externally,
deployed, accepted or submitted. All ignored originals and existing contributor work remain.
