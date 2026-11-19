# ai-blender-animations (shorts3d)

An automated pipeline for vertical **3D "how it works" explainer Shorts**. Each one is a stylised, cel-shaded miniature world with slow camera moves, labels that follow objects, bold captions, narration and sound effects.

```
episode JSON ──► voice (Kokoro / ElevenLabs / system) ──► timeline
     │                                                     │
     └──► Blender (headless, Eevee) builds + animates the scene from Python ──► PNG frames + label tracking
                                                           │
                    overlays (titles, labels, captions, counters, cards) + audio mix ──► ffmpeg ──► MP4
```

Claude Code drives it from one sentence (`/make-episode how smart meters work`). It stops twice for your approval: once after the script for the facts, and once after the preview stills.

## Quick start

1. Install Git, Python 3.11, **Blender 4.5 LTS** and ffmpeg. Full steps for Windows and macOS are in **[docs/SETUP.md](docs/SETUP.md)**.
2. Clone the repo and run setup:
   ```powershell
   git clone https://github.com/moiz-i-am/ai-blender-animations.git
   cd ai-blender-animations
   powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1     # macOS: bash scripts/setup_mac.sh
   ```
3. Make the first episode:
   ```powershell
   .venv\Scripts\python make_episode.py check
   .venv\Scripts\python make_episode.py preview traffic_camera     # look at output/traffic_camera/preview/contact_sheet.png
   .venv\Scripts\python make_episode.py all traffic_camera         # -> output/traffic_camera/traffic_camera.mp4
   ```

## Commands

| Command | What it does |
|---------|--------------|
| `check` | verify Python packages, Blender, ffmpeg, fonts and keys |
| `new <id> --scene <name>` | scaffold `episodes/<id>.json` and `blender/scenes/<name>.py` |
| `validate <ep>` | check the episode JSON and print the shot timeline |
| `voice <ep> [--backend kokoro]` | narration clips. Shots stretch to fit them |
| `preview <ep> [--shots all] [--no-blender]` | final-look stills and a contact sheet |
| `render <ep> [--frames 1-120] [--resume]` | render all frames |
| `assemble <ep> [--draft] [--placeholder]` | overlays and audio, giving an MP4 |
| `all <ep>` | voice, then render, then assemble |
| `blend <ep>` | save `scene.blend` to inspect in Blender or with MCP |
| `clean <ep>` | delete `output/<ep>` |

Add `--engine workbench` to preview, render or blend for a fast fallback that doesn't need a GPU.

## Layout

```
make_episode.py          CLI entry point
pipeline/                voice, captions, overlays, audio mix, ffmpeg, Blender runner
blender/build_scene.py   runs inside Blender: build → animate → track → render
blender/lib/             shapes, cel materials + ink outlines, camera rig, actions, tracking
blender/scenes/          one module per episode + reusable sets (street.py)
episodes/                one JSON per episode (traffic_camera.json, _template.json)
config/settings.json     defaults (override in config/local.json, secrets in .env)
assets/                  fonts, sfx overrides, models, music
.claude/commands/        /make-episode and /preview for Claude Code
.mcp.json                Blender MCP server for Claude Code
docs/                    SETUP, BLENDER_MCP, EPISODE_FORMAT, SCENES
```

## Docs
- [docs/SETUP.md](docs/SETUP.md): installation, first run and troubleshooting
- [docs/EPISODE_FORMAT.md](docs/EPISODE_FORMAT.md): every field in an episode JSON
- [docs/SCENES.md](docs/SCENES.md): writing 3D scenes in Python, and where assets come from
- [docs/BLENDER_MCP.md](docs/BLENDER_MCP.md): letting Claude drive a live Blender window
- [docs/ROADMAP_CHARACTERS.md](docs/ROADMAP_CHARACTERS.md): plan for character cartoons (phase 2)

## Status
- Episode 1 (traffic cameras) is scripted and has a scene. The narration is a placeholder until it's fact-checked.
- The pipeline outside Blender (timeline, captions, overlays, audio mix) has been tested. The Blender scripts haven't been run yet. The first real run on the PC will probably need small fixes to camera framing and the look.
- Next: Episode 2 (smart meters) on the same street.
