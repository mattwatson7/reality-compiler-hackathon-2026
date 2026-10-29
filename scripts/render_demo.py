"""Edit genuine local browser recordings with local narration; no external service.

Run after narrate_demo.ps1 and record_demo.cjs. Original recordings remain in
output/demo-production; the final generated-only MP4 is explicitly public-review
material, never automatically uploaded. All text is editorial, outside the UI.
"""

import argparse
import hashlib
import json
import re
import subprocess
import textwrap
import wave
from pathlib import Path
from typing import Any

import imageio_ffmpeg

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "output/demo-production"
FINAL = ROOT / "docs/submission-final"


def timestamp(seconds: float, *, ass: bool = True) -> str:
    hours, remainder = divmod(seconds, 3600)
    minutes, sec = divmod(remainder, 60)
    if ass:
        return f"{int(hours)}:{int(minutes):02}:{sec:05.2f}"
    return f"{int(hours):02}:{int(minutes):02}:{sec:06.3f}".replace(".", ",")


def run(arguments: list[str]) -> None:
    result = subprocess.run(arguments, cwd=ROOT, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr[-6000:])


def render() -> None:
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    scenes: list[dict[str, Any]] = json.loads((FINAL / "narration.json").read_text())
    recording = json.loads((WORK / "recording.json").read_text())
    times = json.loads((WORK / "durations.json").read_text())
    subtitle_index = 0
    total = 0.0
    subtitles: list[str] = []
    metadata: list[dict[str, Any]] = []
    for scene in scenes:
        identifier = scene["id"]
        segment = next(e for e in recording["events"] if e["id"] == identifier)
        duration = float(times[identifier])
        with wave.open(str(WORK / f"{identifier}.wav")) as speech:
            spoken = speech.getnframes() / speech.getframerate()
        label = "Generated input · Captured Meta evidence · Local revisions · No new inference"
        if identifier == "selection":
            label = "Historical application still · Generated input · Earlier selection flow"
        if identifier == "source":
            label = (
                "Separate generated-input upload · Local OpenCV · No SAM · "
                "Actual source-frame inspection"
            )
        header = (ROOT / "scripts/demo-subtitles.ass").read_text(encoding="utf-8")
        lines = [header]
        for style, text in (("Title", scene["title"]), ("Label", label)):
            lines.append(f"Dialogue: 0,0:00:00.00,{timestamp(duration)},{style},,0,0,0,,{text}\n")
        phrases = re.split(r"(?<=[.!?])\s+", scene["text"])
        length = sum(len(p) for p in phrases)
        position = 0.25
        for phrase in phrases:
            end = min(duration - 0.2, position + spoken * len(phrase) / length)
            wrapped = r"\N".join(textwrap.wrap(phrase, width=110))
            lines.append(
                f"Dialogue: 0,{timestamp(position)},{timestamp(end)},Caption,,0,0,0,,{wrapped}\n"
            )
            subtitle_index += 1
            subtitles.append(
                f"{subtitle_index}\n{timestamp(total + position, ass=False)} --> "
                f"{timestamp(total + end, ass=False)}\n{phrase}\n\n"
            )
            position = end
        (WORK / f"{identifier}.ass").write_text("".join(lines), encoding="utf-8")
        arguments = [ffmpeg, "-y", "-v", "error"]
        if identifier == "selection":
            arguments += ["-loop", "1", "-i", str(ROOT / "docs/milestone-5/browser-selection.jpg")]
        else:
            arguments += ["-ss", str(segment["start"]), "-i", recording["video"]]
        arguments += ["-i", str(WORK / f"{identifier}.wav"), "-t", str(duration)]
        video_filter = (
            "scale=1600:900:force_original_aspect_ratio=decrease,"
            "pad=1600:900:(ow-iw)/2:(oh-ih)/2:color=0x101818,"
            "pad=1920:1080:160:72:color=0x101818,"
            f"ass=output/demo-production/{identifier}.ass"
        )
        arguments += [
            "-vf",
            video_filter,
            "-af",
            "apad,loudnorm=I=-16:TP=-1.5:LRA=11",
            "-r",
            "30",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            "-ar",
            "48000",
            "-movflags",
            "+faststart",
            str(WORK / f"{identifier}.mp4"),
        ]
        run(arguments)
        metadata.append(
            {"id": identifier, "start_s": total, "duration_s": duration, "label": label}
        )
        total += duration
        print(f"Rendered {identifier}", flush=True)
    (WORK / "concat.txt").write_text(
        "".join(f"file '{s['id']}.mp4'\n" for s in scenes), encoding="utf-8"
    )
    target = FINAL / "reality-compiler-demo.mp4"
    run(
        [
            ffmpeg,
            "-y",
            "-v",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(WORK / "concat.txt"),
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "20",
            "-r",
            "30",
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            "-af",
            "aresample=async=1:first_pts=0",
            "-movflags",
            "+faststart",
            str(target),
        ]
    )
    # Decode the whole audio and video, not just the container header.
    run([ffmpeg, "-v", "error", "-i", str(target), "-f", "null", "-"])
    (FINAL / "captions.srt").write_text("".join(subtitles).rstrip() + "\n", encoding="utf-8")
    with target.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    (FINAL / "video-manifest.json").write_text(
        json.dumps(
            {
                "path": target.relative_to(ROOT).as_posix(),
                "sha256": digest,
                "bytes": target.stat().st_size,
                "planned_duration_s": total,
                "resolution": [1920, 1080],
                "fps": 30,
                "video_codec": "h264",
                "audio_codec": "aac",
                "full_audio_video_decode": "passed",
                "narration": "local Microsoft Zira synthetic voice",
                "editing": (
                    "Real application recordings with cuts; selection chapter is a labeled "
                    "historical still. Editorial captions outside UI. "
                    "No fabricated results or model activity."
                ),
                "scenes": metadata,
            },
            indent=2,
        )
        + "\n"
    )
    print(f"Exported {target}: {total:.2f}s, SHA-256 {digest}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare", action="store_true", help="Measure narration before recording")
    if parser.parse_args().prepare:
        timing = {}
        for scene in json.loads((FINAL / "narration.json").read_text()):
            with wave.open(str(WORK / f"{scene['id']}.wav")) as speech:
                timing[scene["id"]] = max(
                    scene["seconds"], round(speech.getnframes() / speech.getframerate() + 1.2, 2)
                )
        (WORK / "durations.json").write_text(json.dumps(timing))
        print(f"Prepared {sum(timing.values()):.2f} seconds")
    else:
        render()
