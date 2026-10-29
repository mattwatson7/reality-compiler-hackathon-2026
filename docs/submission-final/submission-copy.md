# Copy-ready submission

## Team/project name

Reality Compiler

## Short description

Describe what should happen. Show what happened. Prove whether they match. Reality Compiler checks physical procedures against reusable, timestamped visual evidence and explains PASS, FAIL or UNKNOWN.

## One-sentence differentiator

Change the expected procedure and independently re-evaluate the same compatible visual evidence, without repeating perception.

## Project Description — form answer

Ordinary video AI describes what appears to happen. Reality Compiler asks a different question: does the evidence establish what the procedure requires?

Written physical instructions become an inspectable verification program: identified objects, typed actions, visible regions, explicit ordering and unsupported conditions. Video observations link each decisive check to evidence IDs, time intervals and supporting frames. A deterministic evaluator returns PASS, FAIL or UNKNOWN with reasons.

Our working demonstration shows a blue block entering a marked region before a cup. The original requirement passes. Enter a new requirement—cup before block—and it fails against the same preserved evidence. Add “ensure the cup is sterile” and the result becomes UNKNOWN: the visible order holds, but the evidence cannot establish sterility. Each revision compiles independently and must pass a semantic compatibility check before reusing perception. Matching fingerprints make that reuse inspectable; the original evaluation is preserved.

Muse Wonder compiled the original requirements, with independent source-grounding and semantic validation. SAM 3.1 supplied actual captured masks and tracks. Deterministic geometry produced region-entry observations; deterministic logic judged their order. Muse Spark supports bounded visible final-state interpretation in separate captured runs, not this order comparison. New demo revisions compile with explicitly labeled local rules. Offline capture review needs no Meta credentials and makes no new inference requests.

The initial opportunity is evidence review for robotics experiments, simple workstation procedures and training demonstrations: reviewers can inspect a requirement, its proof and what remains unknown. Compatible revisions avoid repeating expensive visual analysis. These are potential applications, not claims of validated customer demand, production accuracy or cost savings.

The public demonstration uses generated input and actual previously captured Meta evidence. It is not physical-camera acceptance. Historical camera findings establish only narrow final visibility or uncertainty; three controlled camera cases remain pending. Image-region entry does not prove physical insertion or containment, and hidden conditions remain unsupported. The prototype runs locally with explicit provenance, immutable audit history, source-frame inspection for new uploads, expiry and conservative uncertainty handling.

As supplementary reproducibility evidence, three separate 15-second generated videos also passed through the actual upload/initialization API and local OpenCV pipeline: correct order PASS, observed cup-first order FAIL, and occlusion UNKNOWN. Their results, timestamps, source frames and new revisions were inspected in Chrome. End-to-end UI uploads were blocked by the browser extension's local-file permission and are not claimed. The occluder triggers a coarse scene-motion guard that invalidates both identities; this is conservative uncertainty handling, not proof of camera movement or a robust occlusion classifier. These runs use no SAM or new Meta inference.

Reality Compiler turns a video summary into an independently inspectable argument about whether evidence matches a procedure.

## Describe your use of Meta products — form answer

Muse Wonder (muse-wonder-1.0) translates physical instructions into provider-neutral TaskGraph v2 requirements. Independent validation checks exact source grounding and observable semantics; character offsets alone do not prove interpretation. Manual frame-zero selections bind graph identities to video. SAM 3.1 (sam-3.1) supplies masks/tracks associated with sampled frames; identity, visibility, geometry and sampling checks determine whether observations can support a decisive event. Muse Spark (muse-spark-1.3) supports bounded observable final-state claims where needed, separated from the deterministic verdict.

The retained evidence includes 17 previously authorized captured inference responses: nine Wonder, five SAM and three Spark. The generated order comparison uses Wonder and SAM; Spark did not contribute to it. The film reviews those real captured outputs offline. Newly entered revisions use the local compiler, reuse compatible observations and make no new model calls. Model IDs, usage, independent compiler/tracker/observer provenance and evidence fingerprints remain inspectable. Paid inference remains disabled for this submission preparation.

## Why are Meta's models important? — form answer

The product needs both semantic interpretation and grounded perception. Wonder turns intent into structured requirements that can be independently checked. SAM turns selected visual identities into masks and frame-associated tracks, enabling geometric observations rather than a free-form guess about order. Spark broadens supported review to bounded visible final states in appropriate runs. Keeping these model roles separate from deterministic judgment lets the product explain missing proof, preserve uncertainty and recheck compatible procedures without repeating visual inference. That separation is the core capability demonstrated here.

## Meta product feedback — form answer

This prototype highlighted the importance of strict structured-output validation, source grounding, bounded mask decoding and frame-associated provenance. Useful confidence scores still need independent identity/visibility checks before they can support an ordering claim. We retained uncertain usage reservations instead of assuming failed or incomplete usage was free. Clear model contracts, documented full-context cost ceilings and verifiable actual usage are essential for a bounded-budget workflow. The adapters preserve offline replay so results can be inspected without keys or fresh paid requests.

## Partner technology feedback — form answer

We did not use Fireworks, Modal or Baseten in this prototype and cannot provide first-hand feedback on those services. The application uses a local FastAPI/React stack, OpenCV/FFmpeg and SQLite, with direct Meta adapters and captured offline replay.

## Demo video description

A real application walkthrough on generated input: inspect Wonder's independently validated program, review captured SAM tracks and supporting frames, reproduce PASS, enter a reversed requirement for FAIL, then add unsupported sterility for UNKNOWN. Matching perception fingerprints show reuse without new inference. A separate local-CV upload demonstrates exact source-frame inspection; the older captured Meta run remains explicitly unmapped. The edit includes labeled historical selection imagery and local synthetic narration. Controlled physical-camera validation is pending.

## Repository and judge instructions

Repository: https://github.com/mattwatson7/reality-compiler — **currently private; publication/access resolution requires approval before filling the public repository field**. Working branch: `milestone-4-meta-integration`, PR #3. Start with [the final landing document](README.md) and [judge reproduction](judge-reproduction.md). The isolated workflow verifies existing capture hashes, launches the real local application without Meta keys, and supports independently entered revisions. A local source bundle is prepared as supplementary delivery; organizer acceptance as a substitute for public GitHub has not been established.

## Exact field placement and remaining values

Enter the paragraphs under each “form answer” heading into the matching field at
[Submit Project](https://cerebralvalley.ai/e/meta-ai-developer-hackathon/hackathon/submit).
Team Name: **Reality Compiler** (entrant confirms). Team Members: confirm the full roster
and representative authority. Track: **Indie Developer Track** if eligible, otherwise the
one eligible track. Problem statement: **Push the Frontier**. Leave the optional viral
X-link field blank unless entering that bonus. **Public GitHub Repository** and
**3-Minute Demo Video** must receive the actual approved public repository root URL and
hosted watch URL after [publication/hosting](publishing-instructions.md); they cannot
truthfully be completed with local files or the current private PR. All narrative
text fields are fully drafted above. Review/accept the publication permission personally
and separately authorize final submission. No form fields or consent were changed.
