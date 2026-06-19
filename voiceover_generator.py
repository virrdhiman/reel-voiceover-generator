"""Interactive timed voiceover generator for social media reels."""

from __future__ import annotations

import asyncio
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

import edge_tts
import imageio_ffmpeg

DEFAULT_VOICE = "en-US-GuyNeural"
DEFAULT_RATE = "+5%"
DEFAULT_DURATION_SEC = 20
DEFAULT_OUTPUT_NAME = "voiceover"

VOICE_OPTIONS = {
    "1": ("en-US-GuyNeural", "US English - Guy (professional male)"),
    "2": ("en-US-JennyNeural", "US English - Jenny (professional female)"),
    "3": ("en-US-AriaNeural", "US English - Aria (expressive female)"),
    "4": ("en-GB-RyanNeural", "British English - Ryan (male)"),
    "5": ("en-GB-SoniaNeural", "British English - Sonia (female)"),
    "6": ("en-IN-NeerjaNeural", "Indian English - Neerja (female)"),
    "7": ("en-IN-PrabhatNeural", "Indian English - Prabhat (male)"),
}

PRODUCTIVE_IT_PRESET = [
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


@dataclass
class Segment:
    start_ms: int
    end_ms: int
    text: str


@dataclass
class VoiceoverConfig:
    output_dir: Path
    output_name: str
    total_ms: int
    voice: str
    rate: str
    segments: list[Segment]


def get_execution_dir() -> Path:
    """Return the folder where output files should be written."""
    return Path.cwd()


def get_ffmpeg_path() -> str:
    return imageio_ffmpeg.get_ffmpeg_exe()


def pause_before_exit() -> None:
    if getattr(sys, "frozen", False):
        input("\nPress Enter to exit...")


def prompt_text(message: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    while True:
        value = input(f"{message}{suffix}: ").strip()
        if value:
            return value
        if default is not None:
            return default
        print("Input cannot be empty.")


def prompt_int(message: str, default: int, minimum: int = 1) -> int:
    while True:
        raw = input(f"{message} [{default}]: ").strip()
        if not raw:
            return default
        try:
            value = int(raw)
        except ValueError:
            print("Enter a whole number.")
            continue
        if value < minimum:
            print(f"Value must be at least {minimum}.")
            continue
        return value


def prompt_float(message: str, default: float, minimum: float = 0.1) -> float:
    while True:
        raw = input(f"{message} [{default}]: ").strip()
        if not raw:
            return default
        try:
            value = float(raw)
        except ValueError:
            print("Enter a valid number.")
            continue
        if value < minimum:
            print(f"Value must be at least {minimum}.")
            continue
        return value


def choose_voice() -> str:
    print("\nAvailable voices:")
    for key, (_, label) in VOICE_OPTIONS.items():
        print(f"  {key}. {label}")

    choice = prompt_text("Select voice number", "1")
    if choice in VOICE_OPTIONS:
        return VOICE_OPTIONS[choice][0]

    print("Unknown choice. Using default voice.")
    return DEFAULT_VOICE


def choose_rate() -> str:
    print("\nSpeech rate examples: -10% (slower), +0% (normal), +10% (faster)")
    raw = prompt_text("Enter rate adjustment", DEFAULT_RATE)
    if raw.endswith("%") or raw.startswith("+") or raw.startswith("-"):
        return raw
    return f"+{raw}%" if raw.lstrip("+-").isdigit() else DEFAULT_RATE


def collect_custom_segments(total_ms: int) -> list[Segment]:
    count = prompt_int("\nHow many voiceover segments?", 1)
    segments: list[Segment] = []

    print("\nEnter each segment. Times are in seconds from the start of the reel.")
    for index in range(count):
        print(f"\n--- Segment {index + 1} of {count} ---")
        start_sec = prompt_float("Start time (seconds)", 0.0, minimum=0.0)
        end_sec = prompt_float("End time (seconds)", min(total_ms / 1000, start_sec + 3), minimum=start_sec + 0.5)
        text = prompt_text("Spoken text")
        segments.append(
            Segment(
                start_ms=int(start_sec * 1000),
                end_ms=int(end_sec * 1000),
                text=text,
            )
        )

    return segments


def collect_segments(total_ms: int) -> list[Segment]:
    print("\nScript mode:")
    print("  1. Use Productive IT CRM preset (20s)")
    print("  2. Enter custom segments manually")
    mode = prompt_text("Choose mode", "1")

    if mode == "1":
        preset = [Segment(**segment) for segment in PRODUCTIVE_IT_PRESET]
        if total_ms != 20000:
            scale = total_ms / 20000
            scaled: list[Segment] = []
            for segment in preset:
                scaled.append(
                    Segment(
                        start_ms=int(segment.start_ms * scale),
                        end_ms=int(segment.end_ms * scale),
                        text=segment.text,
                    )
                )
            return scaled
        return preset

    return collect_custom_segments(total_ms)


def build_config() -> VoiceoverConfig:
    print("=" * 60)
    print("  REEL VOICEOVER GENERATOR")
    print("  Output is saved in the folder where you run this program.")
    print("=" * 60)

    output_dir = get_execution_dir()
    print(f"\nOutput folder: {output_dir}")

    output_name = prompt_text("\nOutput file name (without extension)", DEFAULT_OUTPUT_NAME)
    total_sec = prompt_int("Total reel duration (seconds)", DEFAULT_DURATION_SEC, minimum=5)
    voice = choose_voice()
    rate = choose_rate()
    segments = collect_segments(total_sec * 1000)

    return VoiceoverConfig(
        output_dir=output_dir,
        output_name=output_name,
        total_ms=total_sec * 1000,
        voice=voice,
        rate=rate,
        segments=segments,
    )


def run_ffmpeg(args: list[str]) -> None:
    result = subprocess.run([get_ffmpeg_path(), *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout)


def get_duration_ms(path: Path) -> int:
    probe = subprocess.run(
        [get_ffmpeg_path(), "-i", str(path), "-f", "null", "-"],
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


def build_atempo_filter(speed: float) -> str:
    filters: list[str] = []
    remaining = speed
    while remaining > 2.0:
        filters.append("atempo=2.0")
        remaining /= 2.0
    while remaining < 0.5:
        filters.append("atempo=0.5")
        remaining /= 0.5
    filters.append(f"atempo={remaining:.4f}")
    return ",".join(filters)


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
            build_atempo_filter(speed),
            "-t",
            f"{slot_ms / 1000:.3f}",
            str(output_path),
        ]
    )


async def synthesize_segment(text: str, voice: str, rate: str, output_path: Path) -> None:
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(str(output_path))


def build_timeline(
    segment_files: list[tuple[int, Path, int]],
    output_dir: Path,
    output_name: str,
    total_ms: int,
) -> tuple[Path, Path]:
    mp3_path = output_dir / f"{output_name}.mp3"
    wav_path = output_dir / f"{output_name}.wav"

    with tempfile.TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)
        base_silence = temp / "base.mp3"
        total_sec = total_ms / 1000
        run_ffmpeg(
            [
                "-y",
                "-f",
                "lavfi",
                "-i",
                "anullsrc=r=44100:cl=mono",
                "-t",
                f"{total_sec:.3f}",
                "-q:a",
                "9",
                str(base_silence),
            ]
        )

        inputs: list[str] = ["-y", "-i", str(base_silence)]
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

        filter_script = (
            "".join(mix_inputs)
            + f"amix=inputs={len(mix_inputs)}:duration=first:dropout_transition=0[aout]"
        )

        run_ffmpeg(
            [
                *inputs,
                "-filter_complex",
                filter_script,
                "-map",
                "[aout]",
                "-t",
                f"{total_sec:.3f}",
                "-c:a",
                "libmp3lame",
                "-b:a",
                "192k",
                str(mp3_path),
            ]
        )
        run_ffmpeg(["-y", "-i", str(mp3_path), str(wav_path)])

    return mp3_path, wav_path


def write_script_file(output_dir: Path, output_name: str, segments: list[Segment]) -> Path:
    script_path = output_dir / f"{output_name}-script.txt"
    script_path.write_text(
        "\n\n".join(
            f"{segment.start_ms // 1000:02d}s–{segment.end_ms // 1000:02d}s\n{segment.text}"
            for segment in segments
        ),
        encoding="utf-8",
    )
    return script_path


async def generate_voiceover(config: VoiceoverConfig) -> tuple[Path, Path, Path]:
    segments_dir = config.output_dir / f"{config.output_name}_segments"
    segments_dir.mkdir(parents=True, exist_ok=True)

    raw_paths: list[Path] = []
    for index, segment in enumerate(config.segments):
        raw_path = segments_dir / f"segment_{index:02d}_raw.mp3"
        raw_paths.append(raw_path)
        print(f"Synthesizing segment {index + 1}/{len(config.segments)}...")
        await synthesize_segment(segment.text, config.voice, config.rate, raw_path)

    fitted_files: list[tuple[int, Path, int]] = []
    for index, (segment, raw_path) in enumerate(zip(config.segments, raw_paths)):
        slot_ms = segment.end_ms - segment.start_ms
        fitted_path = segments_dir / f"segment_{index:02d}.mp3"
        print(f"Timing segment {index + 1}/{len(config.segments)}...")
        fit_segment(raw_path, fitted_path, slot_ms)
        fitted_files.append((segment.start_ms, fitted_path, slot_ms))

    print("Mixing final timeline...")
    mp3_path, wav_path = build_timeline(
        fitted_files,
        config.output_dir,
        config.output_name,
        config.total_ms,
    )
    script_path = write_script_file(config.output_dir, config.output_name, config.segments)
    return mp3_path, wav_path, script_path


async def run_app() -> int:
    try:
        config = build_config()
        print("\nGenerating voiceover. This requires an internet connection.\n")
        mp3_path, wav_path, script_path = await generate_voiceover(config)

        print("\nDone!")
        print(f"MP3:    {mp3_path}")
        print(f"WAV:    {wav_path}")
        print(f"Script: {script_path}")
        return 0
    except KeyboardInterrupt:
        print("\nCancelled.")
        return 1
    except Exception as error:
        print(f"\nError: {error}")
        return 1


def main() -> None:
    exit_code = asyncio.run(run_app())
    pause_before_exit()
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
