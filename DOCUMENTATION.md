# Reel Voiceover Generator: Technical Documentation

This document explains how the project works, which functions are used, why they exist, and the syntax behind each major part of the code.

---

## 1. Project Overview

### Purpose

The application converts a timed reel script into a finished voiceover audio file. It is designed for vertical social media videos (9:16) where each sentence must start and end at specific timestamps.

### High-Level Pipeline

```text
User input prompts
        |
        v
Edge TTS (online speech synthesis)
        |
        v
Per-segment timing adjustment (FFmpeg atempo)
        |
        v
Timeline mixing with silence + delays (FFmpeg amix/adelay)
        |
        v
Final MP3 + WAV + script text file
```

### Why this architecture?

1. **Edge TTS** provides free, high-quality neural voices without API keys.
2. **FFmpeg** handles precise audio timing, speed correction, and mixing.
3. **Interactive prompts** make the EXE usable without editing source code.
4. **Output in current working directory** makes the EXE portable: users can copy it anywhere.

---

## 2. Dependencies

### `edge-tts`

Microsoft Edge's online text-to-speech engine exposed as a Python library.

```python
communicate = edge_tts.Communicate(text, voice, rate=rate)
await communicate.save(str(output_path))
```

- `text`: spoken content
- `voice`: neural voice ID, e.g. `"en-US-GuyNeural"`
- `rate`: speed modifier, e.g. `"+5%"`, `"-10%"`
- `save()`: writes an MP3 file

Why async? The library performs network I/O. Using `asyncio` avoids blocking the event loop while multiple segments could be generated in future versions.

### `imageio-ffmpeg`

Bundles a standalone FFmpeg binary so users do not need to install FFmpeg manually.

```python
ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
```

Why needed? FFmpeg is used for:

- reading audio duration
- speeding up clips with `atempo`
- delaying clips with `adelay`
- mixing tracks with `amix`
- exporting WAV from MP3

### `pyinstaller`

Packages Python code and dependencies into a single Windows executable.

---

## 3. Data Structures

### `Segment`

```python
@dataclass
class Segment:
    start_ms: int
    end_ms: int
    text: str
```

Represents one spoken block.

- `start_ms`: when the line should begin on the final timeline
- `end_ms`: when the slot ends
- `text`: words to speak

Example:

```python
Segment(start_ms=0, end_ms=3000, text="You bought a CRM... but nobody uses it.")
```

This means the line belongs in the first 3 seconds.

### `VoiceoverConfig`

```python
@dataclass
class VoiceoverConfig:
    output_dir: Path
    output_name: str
    total_ms: int
    voice: str
    rate: str
    segments: list[Segment]
```

Stores all runtime settings after prompts are collected.

Why a dataclass? It groups related values into one object and makes function signatures cleaner.

---

## 4. Function Reference

### `get_execution_dir() -> Path`

```python
def get_execution_dir() -> Path:
    return Path.cwd()
```

Returns the current working directory.

Why `Path.cwd()` instead of the EXE location?

When a user double-clicks an EXE in Windows Explorer, the working directory is usually the folder containing the EXE. That means output files are created beside the executable, which matches the requested behavior.

Syntax note:

- `Path` comes from `pathlib`
- `cwd()` means "current working directory"

---

### `get_ffmpeg_path() -> str`

```python
def get_ffmpeg_path() -> str:
    return imageio_ffmpeg.get_ffmpeg_exe()
```

Returns the bundled FFmpeg executable path.

Why wrapped in a function? Keeps FFmpeg lookup in one place if packaging changes later.

---

### `pause_before_exit() -> None`

```python
def pause_before_exit() -> None:
    if getattr(sys, "frozen", False):
        input("\nPress Enter to exit...")
```

Keeps the console window open after the EXE finishes.

Why needed? Without this, double-clicking a console EXE closes immediately and users cannot read success/error messages.

Syntax:

- `sys.frozen` is set by PyInstaller
- `getattr(sys, "frozen", False)` safely checks whether the app is running as a bundled EXE

---

### Prompt Helpers

#### `prompt_text(message, default=None) -> str`

Reads a text answer from the user.

```python
value = input(f"{message}{suffix}: ").strip()
```

Why `.strip()`? Removes accidental leading/trailing spaces.

#### `prompt_int(message, default, minimum=1) -> int`

Reads and validates an integer.

Why validation loop? Prevents crashes from bad input like `"abc"`.

#### `prompt_float(message, default, minimum=0.1) -> float`

Reads and validates a decimal number for segment timestamps.

---

### `choose_voice() -> str`

Displays a numbered menu of supported voices and returns the selected voice ID.

Why a menu instead of free text? Voice IDs are long and easy to mistype. A menu improves usability.

Example return value:

```python
"en-US-GuyNeural"
```

---

### `choose_rate() -> str`

Collects speech rate adjustment.

Valid examples:

- `+5%`
- `-10%`
- `+0%`

Why percentage strings? That is the format expected by Edge TTS.

---

### `collect_custom_segments(total_ms) -> list[Segment]`

Builds a custom script by asking the user for each segment's:

- start time in seconds
- end time in seconds
- spoken text

Conversion to milliseconds:

```python
start_ms = int(start_sec * 1000)
end_ms = int(end_sec * 1000)
```

Why milliseconds internally? FFmpeg delay filters and audio timing math are easier at millisecond precision.

---

### `collect_segments(total_ms) -> list[Segment]`

Chooses between:

1. Productive IT preset
2. Custom manual entry

Preset scaling logic:

```python
scale = total_ms / 20000
start_ms = int(segment.start_ms * scale)
```

Why scaling? If the user changes total duration from 20 seconds, the preset timings scale proportionally.

---

### `build_config() -> VoiceoverConfig`

Main prompt flow. Calls all prompt functions and returns a complete configuration object.

This is the function that makes the EXE interactive.

---

## 5. Audio Processing Functions

### `run_ffmpeg(args: list[str]) -> None`

Runs FFmpeg with argument list semantics.

```python
subprocess.run([get_ffmpeg_path(), *args], capture_output=True, text=True)
```

Why list unpacking with `*args`? Keeps command construction readable.

Why raise on failure? FFmpeg errors must stop the process instead of producing broken audio.

---

### `get_duration_ms(path: Path) -> int`

Reads an audio file's duration by parsing FFmpeg stderr output.

Example FFmpeg stderr line:

```text
Duration: 00:00:03.12, start: 0.000000, bitrate: 128 kb/s
```

Parsing steps:

1. Find `"Duration:"`
2. Split hours, minutes, seconds
3. Convert to milliseconds

Why parse stderr? FFmpeg prints metadata to stderr, not stdout.

---

### `build_atempo_filter(speed: float) -> str`

Creates one or more FFmpeg `atempo` filters.

Important FFmpeg rule:

- Each `atempo` filter only supports values between `0.5` and `2.0`

So for large speed changes, filters are chained:

```python
"atempo=2.0,atempo=1.5"
```

Why needed? Some generated speech is longer than its assigned slot. Speeding it up makes it fit without cutting words off abruptly.

---

### `fit_segment(input_path, output_path, slot_ms) -> None`

Ensures a spoken clip fits its assigned time slot.

Two cases:

1. Clip is already short enough → copy unchanged
2. Clip is too long → apply `atempo` speed-up and trim with `-t`

Example FFmpeg args:

```python
[
    "-y",
    "-i", str(input_path),
    "-filter:a", build_atempo_filter(speed),
    "-t", f"{slot_ms / 1000:.3f}",
    str(output_path),
]
```

Flag meanings:

- `-y`: overwrite output
- `-i`: input file
- `-filter:a`: audio filter chain
- `-t`: maximum output duration

---

### `async def synthesize_segment(...) -> None`

Generates one raw speech clip using Edge TTS.

```python
communicate = edge_tts.Communicate(text, voice, rate=rate)
await communicate.save(str(output_path))
```

Why one function per segment? Easier debugging and future parallel generation.

---

### `build_timeline(...) -> tuple[Path, Path]`

Builds the final mixed audio file.

Steps:

1. Create a silent base track for the full reel duration
2. Delay each segment to its start position
3. Mix all tracks together
4. Export MP3 and WAV

#### Silent base track

```python
"-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono"
```

Meaning:

- `lavfi`: libavfilter input
- `anullsrc`: generate silence
- `r=44100`: sample rate
- `cl=mono`: one channel

Why mono? Voiceovers do not require stereo for social media reels.

#### Delay filter

```python
f"adelay={delay_ms}|{delay_ms}"
```

Places a segment later in the timeline.

#### Mix filter

```python
"[0:a][1:a][2:a]amix=inputs=3:duration=first:dropout_transition=0[aout]"
```

Meaning:

- `[0:a]`, `[1:a]`: input audio streams
- `amix`: combine them
- `duration=first`: keep full length of the base silent track
- `[aout]`: named output stream

Why this approach? It preserves exact timeline length while overlaying spoken lines at precise timestamps.

---

### `write_script_file(...) -> Path`

Writes a human-readable transcript:

```text
00s–03s
You bought a CRM... but nobody uses it.

03s–06s
Technology alone doesn't create success.
```

Why generated automatically? Editors can use it for captions and review.

---

### `async def generate_voiceover(config) -> tuple[Path, Path, Path]`

Orchestrates the full generation process:

1. Create segment folder
2. Synthesize raw speech for each segment
3. Fit each segment to its slot
4. Mix final timeline
5. Save script file

Return values:

- MP3 path
- WAV path
- script path

---

### `async def run_app() -> int`

Top-level application controller.

Responsibilities:

- collect config
- generate audio
- print output paths
- handle errors gracefully

Return codes:

- `0` = success
- `1` = failure or cancellation

---

### `main()`

```python
exit_code = asyncio.run(run_app())
pause_before_exit()
raise SystemExit(exit_code)
```

Why `asyncio.run()`? Required entry point for async code in Python 3.7+.

Why `SystemExit`? Ensures the process exits with the correct status code.

---

## 6. PyInstaller Packaging

Build command:

```powershell
python -m PyInstaller `
    --onefile `
    --console `
    --name ReelVoiceoverGenerator `
    --collect-all imageio_ffmpeg `
    --hidden-import edge_tts `
    voiceover_generator.py
```

Option meanings:

| Option | Why |
|--------|-----|
| `--onefile` | Single EXE for easy distribution |
| `--console` | Keeps terminal prompts visible |
| `--name` | Output executable name |
| `--collect-all imageio_ffmpeg` | Bundles FFmpeg binary |
| `--hidden-import edge_tts` | Ensures TTS module is included |

---

## 7. Example Session

```text
Output file name (without extension) [voiceover]: productive-it-crm
Total reel duration (seconds) [20]: 20
Select voice number [1]: 1
Enter rate adjustment [+5%]: +5%
Choose mode [1]: 1
```

Generated files in the same folder:

```text
productive-it-crm.mp3
productive-it-crm.wav
productive-it-crm-script.txt
productive-it-crm_segments/
```

---

## 8. Common Errors

### `Error: Could not read duration`

Cause: FFmpeg failed to inspect a generated segment.

Fix:

- rerun generation
- verify internet connection
- ensure antivirus is not blocking temp files

### Network-related Edge TTS failures

Cause: no internet or blocked Microsoft TTS endpoint.

Fix: connect to the internet and retry.

### Speech sounds too fast

Cause: spoken text is too long for the assigned time slot.

Fix:

- increase segment duration
- shorten text
- reduce speech rate

---

## 9. Extension Ideas

Possible future improvements:

- generate `.srt` subtitle files automatically
- preview voices before generation
- save/load script presets as JSON
- parallel segment synthesis for faster output
- optional background music mixing

---

## 10. Syntax Cheat Sheet

### Path handling

```python
from pathlib import Path
output_dir = Path.cwd()
file_path = output_dir / "voiceover.mp3"
```

The `/` operator joins paths in a cross-platform way.

### Async function definition

```python
async def synthesize_segment(...):
    await communicate.save(...)
```

`async def` defines a coroutine. It must be awaited from another async function or started with `asyncio.run()`.

### Dataclass definition

```python
@dataclass
class Segment:
    start_ms: int
```

Automatically creates `__init__`, making object creation concise.

### Subprocess command execution

```python
subprocess.run([program, arg1, arg2], capture_output=True, text=True)
```

Runs an external program and captures output.

---

## 11. Original Script

`generate_voiceover.py` is the first non-interactive version of this project. It uses hardcoded Productive IT reel content and writes output to an `output/` subfolder. The new interactive app replaces it for normal use, but the original script remains useful as a reference implementation.
