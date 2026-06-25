# Enable repo git hooks (strips Cursor commit attribution). Run once per clone.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
git config core.hooksPath .githooks
Write-Host "Git hooks installed (core.hooksPath=.githooks)" -ForegroundColor Green
