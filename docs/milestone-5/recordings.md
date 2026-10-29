# Recording inspection — October 28, 2026

All four user-supplied files decode fully; exact hashes, native rates, dimensions,
frame counts and byte sizes are in [recording-inventory.json](recording-inventory.json).
The four requested descriptive filenames were absent. Actual files were inspected
independently before associating them with the requested categories.

| Actual file | Native video | Independently inspected sequence | Selected source interval |
|---|---|---|---|
| cam1.mp4 | 1280×720, 30fps, 10.767s | Purple cube on wood table, green cup, robot gripper lowers around cube at about 3–5s, lifts/moves toward cup about 5–7s, final interaction obscured | Entire recording |
| 3_16_peg_eval_continual_success.mp4 | 1280×576, 30fps, 61.5s | Hollow green base and separate green rectangular peg, robot fingers, human resets and repeated attempts; three inset views are distinct cameras | First 6s, before human reset/repeated attempts |
| real_nonprehensile.mp4 | 1280×720, 29.970fps, 21.288s | Peg/base manipulation, orientation changes, human intervention around 8.5–10s; edit around 10s and further reorientation | First 8s, before human intervention/edit |
| real_perturb.mp4 | 1280×720, 25fps, 49.12s | Robot holds peg near hollow base, human pushes/manipulates gripper, repeated motions; later view change around 21s; overhead/table view thereafter | First 8s, before view change |

Sixteen evenly distributed frames per recording and every decoded frame were
used for the inventory. Contact sheets are local under `output/m5-inspection`.
Selected prefixes were fixed in [predeclared-procedures.json](predeclared-procedures.json)
before inference. Both providers received the same selected media and boxes.

The camera footage supports image visibility, movement, projected region overlap,
and visible orientation changes. It does not independently establish hidden
containment, contact forces, successful insertion or stable identity under full
occlusion. SAM is appropriate for selected shape masks; Spark for bounded visible
final-state interpretation. These muted, same-color objects violate local CV's
distinct saturated-color assumptions. OpenCV UNKNOWN results are expected
limitations, not a general benchmark of either provider's accuracy.

## Time bases

Original files remain unchanged under `recordings/external`. Prefix extraction
used ffmpeg `-i ORIGINAL -t SECONDS -an -c:v libx264 -crf 18 SEGMENT` with no speed
change or crop. The backend then autorotates, fits 1280×720, converts to 24fps and
removes audio. Every evidence timestamp refers to its hashed **normalized** clip,
with frame time exactly `index / 24`. Original clip offsets are zero here.

The existing encoder's `-r 24` conversion duplicates terminal frames: the six-second
peg input produced 146 normalized frames (6.083s); the eight-second inputs produced
194 frames (8.083s). These terminal timestamps are not extra source action.
`segment_start + normalized_time` is an approximate original-media seek, clamped
to the selected original interval; a frame-exact original-PTS mapping is **not
established** by this milestone. The predeclared mapping's one-frame tolerance
was optimistic and is superseded by this observed limitation. Re-evaluation
never transforms timestamps or mixes normalized clips, so this does not change
within-clip ordering. A frame-exact source mapping remains a delivery limitation.

## Attribution and redistribution

The `cam1.mp4` scene matches [Bigenlight's cube-in-cup dataset](https://huggingface.co/datasets/Bigenlight/cube_in_cup_raw),
whose dataset card declares Apache-2.0. Its exact take within 24 recordings was
not established from the generic filename. Attribute Bigenlight and preserve the
dataset's license/notice when distributing a verified take.

The three peg filenames occur in the [OmniReset project](https://weirdlabuw.github.io/omnireset/)
and its [website source](https://github.com/WEIRDLabUW/WEIRDLabUW.github.io/blob/main/omnireset/index.html).
Attribution: Patrick Yin, Tyler Westenbroek and collaborators, “Emergent Dexterity
via Diverse Resets and Large-Scale Reinforcement Learning,” ICLR 2026, University
of Washington/NVIDIA/Microsoft Research. The project describes a separate main
visualization camera and three policy-input views. Filenames/site/scene support
attribution, but source bytes were not independently downloaded and hash-matched.
No explicit license for these website video assets was found. Their source
videos, extracted frames and real-camera browser screenshots stay local rather
than being redistributed in the PR or submitted to the hackathon. Resolve asset
permission before using them in a public demo video. Sanitized model geometry,
hashes and evaluation metadata are retained for reproducibility.

These are external evaluations, not the original three controlled held-out
`correct`, `reverse`, and `occlusion` camera recordings. Those remain unavailable.
