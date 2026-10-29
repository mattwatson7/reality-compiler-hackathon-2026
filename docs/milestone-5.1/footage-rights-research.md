# Footage provenance and public-demo decisions

Checked October 28, 2026. This research resolves exact source attribution for all four supplied camera files. It does **not** establish video-specific redistribution permission for the OmniReset assets. All four camera originals and their extracted images remain local and untracked; the public demo uses existing project-generated media only.

## Bigenlight: exact take identified

The [authoritative dataset card](https://huggingface.co/datasets/Bigenlight/cube_in_cup_raw) declares Apache-2.0. The [repository metadata](https://huggingface.co/api/datasets/Bigenlight/cube_in_cup_raw) identified revision `e0a6957536ea3c3b2ab063376103378428c34a8e`. Its [pinned tree metadata](https://huggingface.co/api/datasets/Bigenlight/cube_in_cup_raw/tree/e0a6957536ea3c3b2ab063376103378428c34a8e?recursive=true&expand=false) contains the matching Git LFS object for [take_03_20260720_205457/cam1.mp4](https://huggingface.co/datasets/Bigenlight/cube_in_cup_raw/blob/e0a6957536ea3c3b2ab063376103378428c34a8e/take_03_20260720_205457/cam1.mp4).

Local SHA-256 and size both match the published LFS object: `26a4f40bcecbb23bf7f92c5d106ca013155283e9672e94f9efe3807c9f783f56`, 4,493,342 bytes. No remote copy of this video was needed. This supersedes milestone 5's unresolved exact-take attribution. Attribute Bigenlight, the dataset and the exact take; before any future distribution, preserve the applicable license and notices and identify changes. This milestone does not distribute the recording or its frames.

## OmniReset: byte identity verified, media permission unresolved

The [project page](https://weirdlabuw.github.io/omnireset/) links the paper and code and identifies the authors. The [website HTML at revision 1525e9f1185c1620c9de5a5dc4ca908fd5432471](https://github.com/WEIRDLabUW/WEIRDLabUW.github.io/blob/1525e9f1185c1620c9de5a5dc4ca908fd5432471/omnireset/index.html) references each exact media URL below. The authenticated GitHub connector successfully retrieved the website source; direct official repository metadata pinned its revision.

Each authoritative media response was streamed through SHA-256 in memory and compared with the existing local original and HTTP byte length. No downloaded duplicate was saved, no video/frame was published, and no author was contacted.

| Local original | Authoritative website asset | Bytes | Result |
|---|---|---:|---|
| `3_16_peg_eval_continual_success.mp4` | [peg continuous evaluation](https://omnireset-website.s3.us-west-004.backblazeb2.com/real_eval_videos/peg/3_16_peg_eval_continual_success.mp4) | 7,997,369 | Exact SHA-256 and length match |
| `real_nonprehensile.mp4` | [non-prehensile clip](https://omnireset-website.s3.us-west-004.backblazeb2.com/cherry_pick/real_nonprehensile.mp4) | 2,621,543 | Exact SHA-256 and length match |
| `real_perturb.mp4` | [perturbation clip](https://f004.backblazeb2.com/file/omnireset-website/cherry_pick/real_perturb.mp4) | 7,270,171 | Exact SHA-256 and length match |

The [code repository](https://github.com/UW-Lab/UWLab) reports BSD-3-Clause in [repository metadata](https://api.github.com/repos/UW-Lab/UWLab). This concerns code and is insufficient to establish the license of separately hosted website videos. The inspected website source/page and website repository root did not provide an explicit permission covering these video assets. A public URL, source attribution, project copyright notice, or code license is not taken as permission to redistribute the footage or extracted images.

Attribution: Patrick Yin, Tyler Westenbroek and collaborators, *Emergent Dexterity via Diverse Resets and Large-Scale Reinforcement Learning*, ICLR 2026; University of Washington, NVIDIA and Microsoft Research. The [paper](https://arxiv.org/abs/2603.15789) is an attribution reference; it is not treated as a license grant for website videos. Explicit video permission or an authoritative media license is still needed before any public use of these pixels.

## Public assets

The generated source/normalized videos under `docs/live-validation/live-api-v6-correct` and the generated-input product screenshots under `docs/milestone-5` are the approved selects for this package. They use the project's synthetic drawing and UI, not third-party camera pixels. The generator is `synthetic_clip` in `scripts/meta_smoke.py`; invoking that script's live inference workflow is unnecessary and not authorized. Existing screenshots depict an earlier live-inference UI state, so any still used in the offline demo must carry an external “prior captured run on generated input” caption and must not imply fresh dispatch.

All exact hashes, source URLs, match methods and distribution decisions are recorded in [provenance-permissions.json](provenance-permissions.json). Asset decisions apply to this package; no legal assurance beyond the verified declarations and explicit unresolved permissions is claimed.
