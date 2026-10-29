# Publication and hosting instructions — approval required

All preparation is local. Do not execute the publication steps until the entrant explicitly approves the destination and release. PR #2 and PR #3 stay unmerged and the original repository stays private.

## Separate public repository

The reviewed source ZIP and an extracted `public-source` folder are delivered in `<submission-folder>`. The package has no Git history, credentials, environment file, database, dependencies, private camera pixels or original recordings. Generated inputs and sanitized historical capture contracts needed for offline reproduction are included. See `source-package-manifest.json` for hashes, exclusions and scan scope. Publication readiness does not grant a new license; the entrant must confirm authorship, rights and applicable dependency licenses.

After approval, use the authenticated GitHub account to create an **empty public repository**, suggested name `reality-compiler-hackathon-2026`. Do not import or fork the private repository; do not initialize the new remote with a README. If the suggested name is unavailable, choose another name and change the remote URL below. GitHub connector access works; the local `gh` session is not established, so no `gh` authentication is assumed.

Run these only inside the already extracted `public-source` folder:

```powershell
Set-Location '<submission-folder>\public-source'
if (Test-Path -LiteralPath .git) { throw 'Stop: this folder must have no prior Git history.' }
git init -b main
git add .
git diff --cached --stat
git commit -m 'Reality Compiler hackathon submission'
git remote add origin https://github.com/mattwatson7/reality-compiler-hackathon-2026.git
git push -u origin main
```

These commands create one new root commit and transmit only reviewed package contents. Use the user's existing Git authentication when prompted; do not place tokens in commands. Open the public repository in a signed-out/private browser, verify README, judge instructions, capture assets and the synthetic inputs, then copy its **root URL** into **Public GitHub Repository**. The private source URL and PRs are not substitutes. Do not add the lifetime database or `.env` to reproduce the demonstration.

## Unlisted YouTube demo

After the entrant approves upload to their chosen YouTube channel:

1. Open [YouTube Studio](https://studio.youtube.com/), select Create → Upload videos, and choose `<submission-folder>\reality-compiler-demo.mp4`.
2. Title: **Reality Compiler — Describe. Show. Prove. | Meta AI Developer Hackathon 2026**.
3. Description: copy the text below. Add the approved public repository root URL. Upload `captions.srt` as timed subtitles if Studio offers the subtitle workflow; captions are already burned into the film.
4. Answer audience, altered-content, rights and other questionnaires accurately. The narration is locally synthesized; footage is generated/application capture, not physical-camera evidence. Do not misstate these facts to bypass platform checks. Let checks and HD processing finish.
5. Select **Unlisted**, then save only after release approval. Unlisted links can be reshared. Avoid Private, a scheduled release or an age restriction that would prevent judges viewing; if a restriction is required, resolve judge access before submission.
6. Open the final watch URL signed out/private browsing. Verify playback, readable captions, sound, 1080p availability and seeking through the end without a login or access request. Copy that URL into **3-Minute Demo Video**. A local path is not a hosting link.

Copy-ready description:

```text
Describe what should happen. Show what happened. Prove whether they match.

Reality Compiler compiles written procedures into typed requirements, links decisive checks to timestamped evidence, and preserves PASS, FAIL and UNKNOWN with inspectable reasons. Compatible procedure revisions reuse visual evidence while keeping the original evaluation immutable.

This edited real-application walkthrough uses generated input and actual previously captured Muse Wonder / SAM 3.1 evidence, reviewed offline. New revisions compile locally. Spark's separate bounded final-state contribution is documented but is not used in this ordering comparison. The source-frame chapter uses a separate local OpenCV upload, with no SAM. One selection scene is an explicitly labeled historical still. Narration is locally synthesized. No new paid inference or physical-camera acceptance is claimed.

0:00 Problem and product
0:12 Written procedure compilation
0:26 Frame-zero identities
0:35 Captured SAM tracking
0:48 Timestamped proof
1:02 Original source-frame inspection
1:16 Independently revised requirements
1:29 PASS versus FAIL on the same evidence
1:44 Unsupported conditions remain UNKNOWN
1:59 Model provenance and boundaries
2:13 Reusable evidence
```

The synthetic trio is supplementary reproducible local-CV evidence, described in the public repository. It is not silently spliced into the Meta capture film.

## Final form

Open [Submit Project](https://cerebralvalley.ai/e/meta-ai-developer-hackathon/hackathon/submit). Use [complete copy-ready field answers](submission-copy.md). Team name suggestion: Reality Compiler. Confirm every member and representative authority, one eligibility-appropriate track (Indie recommended only if eligible), and **Push the Frontier**. The viral X field is optional; leave it blank if not entering that bonus. Enter the approved public repository and hosted video URLs. Personally review the rules and publication/promotion permission before accepting it, then separately authorize or perform Submit. Neither acceptance nor submission was performed during preparation.

Current deadline: **November 5, 2026, 09:00 Bangkok** (November 4, 21:00 US Eastern), rechecked October 29 on the [official event page](https://dev.meta.ai/events/global-hackathon). Finish processing and signed-out access checks beforehand. Official eligibility/rights requirements and the actual form were read in authenticated Chrome on October 29; reading them does not attest to eligibility or accept terms.
