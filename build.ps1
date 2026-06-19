# Build the Windows executable for Reel Voiceover Generator

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "Installing dependencies..."
python -m pip install -r requirements.txt

Write-Host "Building executable..."
python -m PyInstaller `
    --onefile `
    --console `
    --name ReelVoiceoverGenerator `
    --collect-all imageio_ffmpeg `
    --hidden-import edge_tts `
    voiceover_generator.py

Write-Host ""
Write-Host "Build complete."
Write-Host "Executable: $PSScriptRoot\dist\ReelVoiceoverGenerator.exe"
