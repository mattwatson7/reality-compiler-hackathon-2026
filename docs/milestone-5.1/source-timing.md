# Source-frame attribution for new runs

Checked October 28, 2026 against the [official FFmpeg encoder-statistics contract](https://www.ffmpeg.org/ffmpeg.html). `-stats_enc_pre` records each frame immediately before encoding; `{ni}`, `{ptsi}`, and `{tbi}` identify the corresponding input decoder frame and its presentation timestamp/time base. An unavailable input identity is not approximated from the average frame rate.

The previous normalization used encoder-level `-r 24`. Six-second prefixes could produce 146 frames, including extra terminal duplicates. Historical verdicts remain valid only on their exact hashed normalized clips. Their source attribution cannot be recovered merely by adding a segment offset. Historical jobs, captures, hashes, evidence seals and evaluation histories are unchanged.

New normalization explicitly selects `0:v:0`, preserves input timestamps with `-copyts`, inventories decoded PTS with `showinfo@source`, rebases presentation time, optionally trims by explicit start/end, rebases the selected interval, and uses `fps=24:round=near:eof_action=round` followed by scale/autorotation and H.264 encoding. Output uses passthrough synchronization so the encoder does not independently duplicate frames. It retains audio removal and the existing size/duration bounds. Trimming uses an end timestamp rather than a duration measured from the first retained VFR frame.

`video.timing.json` and the job's sealed `media_metadata.source_timing` contain:

- Exact upload and normalized SHA-256; FFmpeg version and filter chain.
- Source stream time base, decoded presentation-order indices/PTS, first decoded PTS time, selected segment offset/duration, and normalized `1/24` time base.
- Each normalized frame's exact decoder index, integer source PTS, rational time base and display time. Duplicates retain the same original index; dropped frames remain in the decoded inventory without an output association.
- An explicit unknown parent-source offset. A file externally cut before upload is a distinct immutable source; ancestry is not invented.

Mapping construction rejects absent input identity, inconsistent time bases/PTS, nonmonotonic source PTS, noncontiguous output indices, disagreement with the 24 fps timeline, or encoded/map frame-count mismatch. It fails normalization rather than inventing precision. The current bundled FFmpeg 7.1 supports the statistics contract. An older override lacking it fails closed; use the bundled binary or a compatible FFmpeg.

The evaluator still uses normalized intervals exclusively. Source mapping is an attribution channel, never a transformation of observations or ordering constraints. Compatibility fingerprints include the map as part of media metadata. Adding a map to an old completed job would change its seal, so no automatic migration is performed. Offline imports retain their original unmapped status and label.

The browser seeks normalized evidence with its overlays intact. **Inspect original source frame** resolves the playhead through the map and requests `/api/jobs/{internal-id}/source-frames/{normalized-index}`. The server checks media hashes and the completed evidence seal, explicitly decodes the same first video stream, and returns the exact selected source frame as PNG. It accepts no source path or event time. Source images expire with the job directory; audit metadata/history remain. Browser microsecond rounding has a one-microsecond boundary tolerance for choosing a displayed frame, without changing evaluation timestamps.

Regression coverage uses actual FFmpeg decoding: 25, 29.97, 30 and 12 fps, dropped/duplicated frames, a one-frame clip, genuinely variable frame intervals, nonzero initial PTS, explicit trimming, multitrack stream selection, tampered media/map rejection, legacy refusal and expiry. Browser checks exercise a new generated upload and source frame 50 at `25600 × 1/12288 = 2.083333…s`. These are timing/correctness tests, not physical-camera acceptance.
