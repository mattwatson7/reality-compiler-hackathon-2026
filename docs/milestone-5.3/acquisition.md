# Exact acquisition decision — October 29, 2026

## A. DOWNLOAD THESE FILES

**No new download is recommended for controlled acceptance.** No matching online
trio was verified in this research. This is a bounded search finding, not a claim
that no such recordings exist anywhere. Downloading three successful robot takes
cannot establish reversed order or occlusion under one frozen instruction.
Third-party data can support supplementary real-camera evaluation; it cannot be
described as independently captured controlled originals for this protocol.

The best rights-documented exact file is already present:

- Original title: **cube_in_cup_raw — raw HDF5 + MP4 teleop logs (UR7e,
  "put the cube in the cup")**, Bigenlight, take `take_03_20260720_205457`, camera 1.
- [Direct pinned download](https://huggingface.co/datasets/Bigenlight/cube_in_cup_raw/resolve/e0a6957536ea3c3b2ab063376103378428c34a8e/take_03_20260720_205457/cam1.mp4?download=true).
- Save filename `cam1.mp4`; destination `recordings/external/` (repository-relative).
  **Keep the existing file; do not overwrite or download a duplicate.**
- Verified local metadata: MP4, 1280×720, 30 fps, 323 frames, 10.766667 s;
  4,493,342 bytes; SHA-256
  `26a4f40bcecbb23bf7f92c5d106ca013155283e9672e94f9efe3807c9f783f56`.
- Prior full-decode/visual inspection: purple cube, green cup, gripper descends
  around 3–5 s, lifts/moves toward cup around 5–7 s; final interaction obscured.
  The dataset task title does not prove insertion. Under the controlled blue-block
  then yellow-cup instruction it has no valid PASS/FAIL applicability. Under a
  separately frozen cube/cup visibility study, occluded identity/final placement
  can warrant UNKNOWN; actual output remains independent.
- [Publisher dataset card](https://huggingface.co/datasets/Bigenlight/cube_in_cup_raw)
  declares Apache-2.0, confirmed through the Hugging Face connector today. Preserve
  license, applicable notices, attribution and modification notices before public
  reuse; the card is a declaration, not independent verification of all rights.
- Suitable for **supplementary real-camera testing only**. Keep pixels out of the
  current generated-only submission package unless separately approved.

The other three exact downloads are also already present and are **not acquisition
recommendations**. These authoritative links allow recovery if an original is lost:

| Source / exact filename in `recordings/external/` | Download | Verified native metadata | Visible content / applicability |
|---|---|---|---|
| OmniReset, `3_16_peg_eval_continual_success.mp4` | [Exact asset](https://omnireset-website.s3.us-west-004.backblazeb2.com/real_eval_videos/peg/3_16_peg_eval_continual_success.mp4) | MP4, 1280×576, 30 fps, 1845 frames, 61.5 s | Peg/base, repeated attempts, human resets, multiple camera insets; exceeds 30 s bound; no controlled order labels |
| OmniReset, `real_nonprehensile.mp4` | [Exact asset](https://omnireset-website.s3.us-west-004.backblazeb2.com/cherry_pick/real_nonprehensile.mp4) | MP4, 1280×720, 30000/1001 fps, 638 frames, 21.287933 s | Peg reorientation, human intervention ~8.5–10 s, edit ~10 s; no controlled order labels |
| OmniReset, `real_perturb.mp4` | [Exact asset](https://f004.backblazeb2.com/file/omnireset-website/cherry_pick/real_perturb.mp4) | MP4, 1280×720, 25 fps, 1228 frames, 49.12 s | Gripper/peg perturbations and later view change ~21 s; exceeds 30 s bound; no controlled order labels |

These are website asset identifiers, not independently titled dataset episodes.
Attribution: Patrick Yin, Tyler Westenbroek and collaborators, *Emergent Dexterity
via Diverse Resets and Large-Scale Reinforcement Learning*, ICLR 2026;
UW/NVIDIA/Microsoft Research. [Official project](https://weirdlabuw.github.io/omnireset/).
Video-specific reuse/publication permission remains unverified; the code's BSD
license is insufficient. Do not include video or frames in the public package.
Historical prefix evaluations remain supplementary and cannot establish hidden
insertion or this protocol's PASS/FAIL/UNKNOWN coverage. Exact byte-match provenance
and hashes: [existing rights inventory](../milestone-5.1/provenance-permissions.json).

## Search decisions

- Bigenlight: original raw camera MP4s and explicit dataset license; one exact
  existing take has verified bytes and prior visual inspection. Other takes were
  not inspected; no success/failure/occlusion labels are invented for them.
- [BridgeData V2 publisher](https://bridgedata-v2.github.io/): real robot
  demonstrations, but displayed evaluation videos are explicitly 2× speed.
  Those displays do not satisfy untouched normal-speed controlled capture.
- [RoboVQA publisher](https://robovqa.github.io/): long-horizon, multiple embodiments
  and intervention-dependent tasks; the page explicitly cautions that displayed
  intervention labeling is imperfect. No exact three-file controlled match or
  per-file metadata was verified, so no bulk dataset download is requested.
- Simulation datasets (including the search result for NVIDIA PhysicalAI
  Manipulation SingleArm) do not fill a real-camera evidence gap.

## Minimal original-recording alternative

Use the [full fixed protocol](../milestone-5.1/recording-guide.md). Setup once:
fixed overhead phone, 720p landscape/30 fps MP4 H.264, locked exposure/focus,
dark matte table, saturated blue block and yellow cup, white target rectangle
at image x=.55, y=.25, width=.35, height=.50. Both objects start separately to
its left and remain recognizable. Capture three continuous **15-second** originals:

| Save under `recordings/controlled/` | Actions | Human expectation, conditional on review |
|---|---|---|
| `correct.mp4` | Still 0–3 s; blue enters 3–5 s; pause; yellow enters 8–10 s; hands away to 15 s | PASS if both entries and order are actually observable |
| `reverse.mp4` | Same timing; yellow first, blue second | FAIL if reversed order is actually observable |
| `occlusion.mp4` | Both visible 0–3 s; gray card fully hides blue/path before entry; move blue behind it 3–7 s; uncover at 8 s; yellow enters 10–12 s | UNKNOWN if blue identity/entry cannot be established and no independent decisive failure exists |

Use exactly: **Move the blue block into the visible image region target, then
move the yellow cup into the visible image region target.** Keep untouched camera
files and device names privately; record actual operator, timezone capture date,
ownership/consent and publication permission. Retain failed takes. Do not trim,
retime, recompress or relabel online videos as these originals. No verdict is
promised until evidence is evaluated and reviewed.

## B. HUMAN ACTIONS REQUIRED

1. For stronger camera claims, record the three files above. No dataset browsing
   is needed. This is optional for the truthful generated-input submission.
2. Independently inspect every original and annotate actual visible entry,
   ambiguity and occlusion windows **before inference**; complete the manifest,
   retain its freeze hash independently and review frame-zero selections, masks,
   identity continuity, source mapping and every decisive interval afterward.
   [Exact offline commands](evaluation.md). Software cannot attest authenticity,
   rights, reviewer independence or visible ground truth.
3. Review the preserved [film](../submission-final/reality-compiler-demo.mp4) and
   [source package](../submission-final/reality-compiler-source.zip). Authorize
   public source delivery (prefer a sanitized repository if private history must
   remain private) and video hosting/access. Neither has been published.
4. Confirm team name/roster, authorized representative and eligible track; review
   official rules and publication/promotion consent, then authorize or perform
   final submission with public repository/video URLs and
   [prepared answers](../submission-final/submission-copy.md).
5. Finish before **November 5, 2026, 09:00 Bangkok**. Do not delay the existing
   generated-input submission for optional camera work. No deployment is required
   by the previously inspected form. No merge is authorized.

The request to use available Muse credits does not require spending to research
URLs. No useful verified Muse browsing integration was found. The explicit task
also preserves paid gates and forbids paid inference: both remain unchanged.
Lifetime exposure stays [private historical cost] of the internal $100 ceiling; reported vendor
credit does not change that ceiling ([private historical cost] internal headroom).
