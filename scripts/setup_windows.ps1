# shorts3d setup for Windows (PowerShell).
# Run from the repo root:
#   powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1            # Python venv + core packages
#   powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1 -Tools     # also install Blender/ffmpeg/uv via winget
#   powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1 -Voice     # also Kokoro + faster-whisper (CUDA torch)
param(
    [switch]$Tools,
    [switch]$Voice
)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

function Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }

if ($Tools) {
    Step "Installing tools with winget (skip any you already have)"
    winget install -e --id Git.Git
    winget install -e --id Python.Python.3.11
    winget install -e --id Gyan.FFmpeg
    winget install -e --id astral-sh.uv
    # Blender 4.5 LTS. If this ID is not found, run:  winget search Blender
    # or download it from https://www.blender.org/download/lts/4-5/
    winget install -e --id BlenderFoundation.Blender.LTS.4.5
    Write-Host "Close and reopen PowerShell so PATH changes apply, then run this script again without -Tools." -ForegroundColor Yellow
}

Step "Creating virtual environment (.venv) with Python 3.11"
if (-not (Test-Path .venv)) {
    py -3.11 -m venv .venv
    if ($LASTEXITCODE -ne 0) { python -m venv .venv }
}
$py = ".\.venv\Scripts\python.exe"
& $py -m pip install --upgrade pip
& $py -m pip install -r requirements.txt

if ($Voice) {
    Step "Installing CUDA PyTorch + Kokoro + faster-whisper"
    # Pick the CUDA build that matches your driver at https://pytorch.org/get-started/locally/
    & $py -m pip install torch --index-url https://download.pytorch.org/whl/cu124
    & $py -m pip install -r requirements-voice.txt
}

if (-not (Test-Path config\local.json)) {
    Copy-Item config\local.example.json config\local.json
    Write-Host "Created config\local.json - edit blender_path if Blender is not auto-detected." -ForegroundColor Yellow
}
if (-not (Test-Path .env)) { Copy-Item .env.example .env }

Step "Checking environment"
& $py make_episode.py check
