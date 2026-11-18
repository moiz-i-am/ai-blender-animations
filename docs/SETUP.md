# Setup

The main machine is the **Windows PC** (RTX 3060 12 GB). The **MacBook (M1 Pro, 16 GB)** works too, for prototyping and light renders.
Each step below gives the Windows command first, then the macOS one.

## What you need

| Tool | Version | Why | Required? |
|------|---------|-----|-----------|
| Git | any | clone and pull the repo | yes |
| Python | 3.11 (3.10-3.12 also work) | pipeline scripts | yes |
| Blender | **4.5 LTS** | builds and renders the 3D scenes | yes |
| ffmpeg | any recent | audio conversion and MP4 encoding | yes |
| Claude Code | latest | runs the pipeline from one sentence | recommended |
| uv (`uvx`) | latest | runs the Blender MCP server | only for MCP |
| PyTorch + Kokoro | see below | free local narration | optional |
| faster-whisper | see below | word-accurate caption timing | optional |
| ElevenLabs API key | - | paid, best-quality narration | optional |

---

## 1. Install the tools

### Windows (PowerShell)

```powershell
winget install -e --id Git.Git
winget install -e --id Python.Python.3.11
winget install -e --id Gyan.FFmpeg
winget install -e --id astral-sh.uv            # only needed for Blender MCP
winget install -e --id BlenderFoundation.Blender.LTS.4.5
```

If winget can't find the Blender ID, run `winget search Blender` and pick the 4.5 LTS entry, or install it from <https://www.blender.org/download/lts/4-5/>.
After installing, **close and reopen PowerShell** so the PATH changes apply.

### macOS

```bash
brew install python@3.11 ffmpeg uv espeak-ng
brew install --cask blender@lts      # or download 4.5 LTS from blender.org
```

## 2. Get the code

```powershell
git clone https://github.com/moiz-i-am/ai-blender-animations.git
cd ai-blender-animations
```

To update later, run `git pull`.

## 3. Python environment

The setup script creates `.venv`, installs the packages, creates `config/local.json` and `.env`, and runs the environment check.

```powershell
# Windows
powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1
```

```bash
# macOS
bash scripts/setup_mac.sh
```

If you'd rather do it by hand:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt     # mac: .venv/bin/python ...
```

From here on, `py` in these docs means the venv's Python: `.venv\Scripts\python` on Windows or `.venv/bin/python` on macOS.
You can also activate the venv first (`.venv\Scripts\Activate.ps1`, or `source .venv/bin/activate` on macOS) and then just type `python`.

## 4. Configure (only if auto-detect fails)

`config/local.json` overrides `config/settings.json` on this machine only, and it's git-ignored:

```json
{
  "blender_path": "C:/Program Files/Blender Foundation/Blender 4.5/blender.exe",
  "ffmpeg_path": null,
  "voice": { "backend": "kokoro" }
}
```

Secrets go in `.env`, for example `ELEVENLABS_API_KEY=...`.

## 5. Check

```powershell
py make_episode.py check
```

Every line marked as required must show `OK`. `WARN` lines are optional extras.

## 6. First run (traffic-camera episode)

```powershell
py make_episode.py validate traffic_camera        # timeline printout
py make_episode.py preview traffic_camera         # ~1-3 min: 4 stills -> output/traffic_camera/preview/
py make_episode.py render traffic_camera          # full render, about 975 frames (can take a while)
py make_episode.py assemble traffic_camera        # -> output/traffic_camera/traffic_camera.mp4
```

Or run it all in one go: `py make_episode.py all traffic_camera`.

Open `output/traffic_camera/preview/contact_sheet.png` after the preview, and only start the full render once it looks right.

To check timing without rendering anything, run `py make_episode.py preview traffic_camera --no-blender`, then `py make_episode.py assemble traffic_camera --placeholder --draft`.

## 7. Narration (optional)

The default is `"backend": "none"`, so there's no voice. You can switch backends per run with `--backend`, or set one in `config/local.json` or the episode file.

| Backend | Setup | Notes |
|---------|-------|-------|
| `system` | nothing | Windows SAPI or macOS `say`. Robotic, but handy for checking timing |
| `kokoro` | see below | free, local, good quality |
| `elevenlabs` | `ELEVENLABS_API_KEY` in `.env`, plus `voice.elevenlabs_voice` set to a voice ID | paid, best quality |

**Kokoro on Windows + NVIDIA:** install the CUDA build of PyTorch first. Pick the command for your driver at <https://pytorch.org/get-started/locally/>. Then:

```powershell
.venv\Scripts\python -m pip install torch --index-url https://download.pytorch.org/whl/cu124
.venv\Scripts\python -m pip install -r requirements-voice.txt
```

The setup script does this for you if you pass `-Voice`. Kokoro may also want `espeak-ng` for some words. On Windows, install it from <https://github.com/espeak-ng/espeak-ng/releases>.

Shots are stretched automatically when a narration line is longer than the shot's duration.

**Caption timing:** with faster-whisper installed, set `"captions": {"word_timing": true}` in `config/local.json` so captions follow the actual speech word by word.

## 8. Claude Code

1. Install Claude Code, either the desktop app's **Code** tab or the CLI (<https://claude.com/claude-code>).
2. Open this folder in it. In a terminal, `cd ai-blender-animations` and then run `claude`.
3. Claude reads `CLAUDE.md` automatically. Try one of these:
   - `/make-episode how smart meters work`
   - `/preview traffic_camera`
   - or just ask: "render a preview of traffic_camera and tell me what looks wrong".
4. Optional: set up Blender MCP so Claude can drive a live Blender window. See [BLENDER_MCP.md](BLENDER_MCP.md).

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Blender not found` | Set `blender_path` in `config/local.json` |
| `ffmpeg not found` | Reopen the terminal after installing, or set `ffmpeg_path` |
| Blender error during preview/render | Read `output/<id>/logs/blender_<mode>.log`, the full log |
| Eevee renders black or crashes (no GPU or old driver) | Add `--engine workbench` (fast, simpler look) and update your GPU driver |
| Labels in the wrong place | Labels follow tracking data from the last Blender run. Re-run `preview` or `render` after changing the scene |
| Video timing wrong after changing the voice | Re-run `render`, because frames depend on the timeline |
