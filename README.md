# Reel Voiceover Generator

Generate timed voiceover audio for Instagram Reels, Facebook Reels, and LinkedIn vertical videos. The program uses Microsoft Edge neural text-to-speech and FFmpeg to produce MP3 and WAV files in the folder where you run it.

## Quick Start (Executable)

1. Download or build `ReelVoiceoverGenerator.exe` from the `dist` folder.
2. Place the EXE in any folder where you want output files saved.
3. Double-click the EXE.
4. Follow the on-screen prompts.
5. Generated files appear in the same folder:
   - `your-name.mp3`
   - `your-name.wav`
   - `your-name-script.txt`
   - `your-name_segments/` (individual segment files)

Internet access is required because speech synthesis uses the Edge TTS online service.

## Quick Start (Python)

```powershell
cd productive-it-reel
python -m pip install -r requirements.txt
python voiceover_generator.py
```

## Build the EXE Yourself

```powershell
cd productive-it-reel
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

Output: `dist\ReelVoiceoverGenerator.exe`

## Interactive Prompts

When you run the program, it asks for:

| Prompt | Purpose | Default |
|--------|---------|---------|
| Output file name | Base name for MP3/WAV/script | `voiceover` |
| Total reel duration | Final timeline length in seconds | `20` |
| Voice selection | Neural TTS voice | `en-US-GuyNeural` |
| Speech rate | Speed adjustment | `+5%` |
| Script mode | Preset or custom segments | Productive IT preset |

### Custom Segment Mode

For each segment you provide:

- Start time in seconds
- End time in seconds
- Spoken text

The program fits each spoken clip into its time slot and mixes all segments onto one timeline.

## Project Files

| File | Purpose |
|------|---------|
| `voiceover_generator.py` | Main interactive application |
| `generate_voiceover.py` | Original non-interactive script |
| `build.ps1` | Builds the Windows EXE with PyInstaller |
| `requirements.txt` | Python dependencies |
| `DOCUMENTATION.md` | Detailed technical documentation |
| `dist/ReelVoiceoverGenerator.exe` | Built executable (also copied to `release/`) |
| `release/ReelVoiceoverGenerator.exe` | Ready-to-run Windows executable |

## Requirements

- Windows 10/11
- Internet connection
- Python 3.11+ (for source usage or building the EXE)

## License

MIT
