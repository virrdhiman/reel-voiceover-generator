"""Generate timed 20s voiceover for Productive IT CRM Reel."""

import asyncio
import subprocess
import tempfile
from pathlib import Path

import edge_tts
import imageio_ffmpeg

OUTPUT_DIR = Path(__file__).resolve().parent / "output"
SEGMENTS_DIR = OUTPUT_DIR / "segments"
TOTAL_MS = 20_000
VOICE = "en-US-GuyNeural"
RATE = "+5%"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

SEGMENTS = [
    {"start_ms": 0, "end_ms": 3000, "text": "You bought a CRM... but nobody uses it."},
    {"start_ms": 3000, "end_ms": 6000, "text": "Technology alone doesn't create success."},
    {"start_ms": 6000, "end_ms": 10000, "text": "True success comes from adoption."},
    {
        "start_ms": 10000,
        "end_ms": 15000,
        "text": (
            "When you have consistent usage, accurate data, automated workflows, "
            "and leadership support, everything changes."
        ),
    },
    {"start_ms": 15000, "end_ms": 17000, "text": "Turn your CRM into a growth engine today..."},
    {"start_ms": 17000, "end_ms": 20000, "text": "...with Productive IT."},
]


def run_ffmpeg(args: list[str]) -> None:
    result = subprocess.run([FFMPEG, *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout)


def get_duration_ms(path: Path) -> int:
    probe = subprocess.run(
        [FFMPEG, "-i", str(path), "-f", "null", "-"],
        capture_output=True,
        text=True,
    )
    for line in probe.stderr.splitlines():
        if "Duration:" in line:
            time_part = line.split("Duration:")[1].split(",")[0].strip()
            hours, minutes, seconds = time_part.split(":")
            total_seconds = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
            return int(total_seconds * 1000)
    raise RuntimeError(f"Could not read duration for {path}")


def fit_segment(input_path: Path, output_path: Path, slot_ms: int) -> None:
    duration_ms = get_duration_ms(input_path)
    if duration_ms <= slot_ms:
        run_ffmpeg(["-y", "-i", str(input_path), "-c", "copy", str(output_path)])
        return

    speed = duration_ms / slot_ms
    run_ffmpeg(
        [
            "-y",
            "-i",
            str(input_path),
            "-filter:a",
            f"atempo={min(speed, 2.0):.4f}" + (f",atempo={speed / 2.0:.4f}" if speed > 2.0 else ""),
            "-t",
            f"{slot_ms / 1000:.3f}",
            str(output_path),
        ]
    )


def build_timeline(segment_files: list[tuple[int, Path, int]]) -> Path:
    output_path = OUTPUT_DIR / "productive-it-crm-reel-voiceover.mp3"
    wav_path = OUTPUT_DIR / "productive-it-crm-reel-voiceover.wav"

    with tempfile.TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)
        base_silence = temp / "base.mp3"
        run_ffmpeg(["-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", "20", "-q:a", "9", str(base_silence)])

        inputs: list[str] = ["-y", "-i", str(base_silence)]
        filter_parts: list[str] = []
        mix_inputs: list[str] = ["[0:a]"]

        for index, (start_ms, segment_path, slot_ms) in enumerate(segment_files, start=1):
            padded = temp / f"padded_{index:02d}.mp3"
            delay_ms = start_ms + max(0, (slot_ms - get_duration_ms(segment_path)) // 2)
            run_ffmpeg(
                [
                    "-y",
                    "-i",
                    str(segment_path),
                    "-af",
                    f"adelay={delay_ms}|{delay_ms}",
                    str(padded),
                ]
            )
            inputs.extend(["-i", str(padded)])
            mix_inputs.append(f"[{index}:a]")

        filter_parts.append("".join(mix_inputs) + f"amix=inputs={len(mix_inputs)}:duration=first:dropout_transition=0[aout]")
        filter_script = ";".join(filter_parts)

        run_ffmpeg(
            [
                *inputs,
                "-filter_complex",
                filter_script,
                "-map",
                "[aout]",
                "-t",
                "20",
                "-c:a",
                "libmp3lame",
                "-b:a",
                "192k",
                str(output_path),
            ]
        )

        run_ffmpeg(["-y", "-i", str(output_path), str(wav_path)])

    return output_path


async def synthesize_segment(index: int, text: str, output_path: Path) -> None:
    communicate = edge_tts.Communicate(text, VOICE, rate=RATE)
    await communicate.save(str(output_path))


async def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SEGMENTS_DIR.mkdir(parents=True, exist_ok=True)

    raw_paths: list[Path] = []
    for index, segment in enumerate(SEGMENTS):
        raw_path = SEGMENTS_DIR / f"segment_{index:02d}_raw.mp3"
        raw_paths.append(raw_path)
        await synthesize_segment(index, segment["text"], raw_path)

    fitted_files: list[tuple[int, Path, int]] = []
    for index, (segment, raw_path) in enumerate(zip(SEGMENTS, raw_paths)):
        slot_ms = segment["end_ms"] - segment["start_ms"]
        fitted_path = SEGMENTS_DIR / f"segment_{index:02d}.mp3"
        fit_segment(raw_path, fitted_path, slot_ms)
        fitted_files.append((segment["start_ms"], fitted_path, slot_ms))

    voiceover_path = build_timeline(fitted_files)

    script_path = OUTPUT_DIR / "voiceover-script.txt"
    script_path.write_text(
        "\n\n".join(
            f"{segment['start_ms'] // 1000:02d}s–{segment['end_ms'] // 1000:02d}s\n{segment['text']}"
            for segment in SEGMENTS
        ),
        encoding="utf-8",
    )

    print(f"Voiceover MP3: {voiceover_path}")
    print(f"Voiceover WAV: {OUTPUT_DIR / 'productive-it-crm-reel-voiceover.wav'}")


if __name__ == "__main__":
    asyncio.run(main())
