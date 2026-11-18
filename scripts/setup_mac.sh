#!/usr/bin/env bash
# shorts3d setup for macOS. Run from the repo root:
#   bash scripts/setup_mac.sh            # Python venv + core packages
#   bash scripts/setup_mac.sh --tools    # also brew install Blender, ffmpeg, uv, python@3.11
#   bash scripts/setup_mac.sh --voice    # also Kokoro + faster-whisper
set -euo pipefail
cd "$(dirname "$0")/.."

TOOLS=0; VOICE=0
for a in "$@"; do
  case "$a" in --tools) TOOLS=1 ;; --voice) VOICE=1 ;; esac
done
step() { printf "\n==> %s\n" "$1"; }

if [ "$TOOLS" = 1 ]; then
  step "Installing tools with Homebrew"
  brew install python@3.11 ffmpeg uv espeak-ng
  # Blender 4.5 LTS: the 'blender@lts' cask if available, otherwise download from blender.org
  brew install --cask blender@lts || echo "Install Blender 4.5 LTS from https://www.blender.org/download/lts/4-5/"
fi

step "Creating virtual environment (.venv)"
PY=$(command -v python3.11 || command -v python3)
[ -d .venv ] || "$PY" -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt

if [ "$VOICE" = 1 ]; then
  step "Installing Kokoro + faster-whisper"
  .venv/bin/python -m pip install torch
  .venv/bin/python -m pip install -r requirements-voice.txt
fi

[ -f config/local.json ] || { echo '{}' > config/local.json; echo "Created config/local.json (empty overrides)"; }
[ -f .env ] || cp .env.example .env

step "Checking environment"
.venv/bin/python make_episode.py check || true
