@echo off
setlocal
title Build EXE - Voiceover Generator
cd /d "%~dp0"

echo.
echo ========================================
echo   Building EXE: VoiceoverGenerator
echo   Project     : Voiceover Generator
echo ========================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\..\tools\BuildExe\Build-One.ps1" -RepoFolder "%CD%" -EntryScript "generate_voiceover.py" -ExeName "VoiceoverGenerator" -Console 
set ERR=%ERRORLEVEL%

echo.
if %ERR% NEQ 0 (
  echo BUILD FAILED
  pause
  exit /b %ERR%
)

echo.
echo EXE is in: "%CD%\dist\VoiceoverGenerator.exe"
explorer "%CD%\dist"
pause
endlocal
