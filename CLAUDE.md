# ai-blender-animations: 3D explainer Shorts pipeline

## Goal
Make vertical (1080x1920, 30 fps) "how it works" explainer Shorts of 30-75 s each, in a bru3D-like style: a stylised cel-shaded 3D miniature world, slow camera moves, floating labels, bold captions and a voiceover. There are no talking characters for now; a mascot may come later.
The user gives one instruction in Claude Code (`/make-episode <topic>`) and the pipeline runs, stopping at the two approval points.

## Series plan
- Ep 1 `traffic_camera`: the reveal is that not every box on a pole is a camera. Radar measures speed, loops in the road sense cars, the camera and flash take the photo, and the plate is read by software and checked by a person. **The narration is a placeholder: `fact_checked` is false.**
- Ep 2 smart meters: same street set. Use the `house_main` / `house_main_front` anchors in `scenes/street.py`.
- Later topics: inside famous places, everyday tech secrets, a Pakistan/South Asia angle, hidden city systems.

## Machines
- Windows PC with an RTX 3060 12 GB is the main machine for renders and local AI 3D generation.
- MacBook Pro M1 Pro 16 GB is for prototyping. Use hosted Meshy or Tripo for AI 3D there.
- The user installs the tools themselves. **Don't install system software without asking.**

## How to run
Use the venv Python: `.venv\Scripts\python` on Windows, `.venv/bin/python` on macOS.

```
py make_episode.py check | validate <ep> | voice <ep> | preview <ep> [--shots all] | render <ep> | assemble <ep> | all <ep> | blend <ep>
```

- Outputs go to `output/<id>/`: `timing.json`, `voice/`, `preview/contact_sheet.png`, `frames/`, `tracking.json`, `logs/`, and `<id>.mp4`.
- Blender logs are in `output/<id>/logs/blender_<mode>.log`. Read them when Blender fails.
- You can check overlays and timing without Blender: `preview <ep> --no-blender`, then `assemble <ep> --placeholder --draft`. The assemble step needs ffmpeg.

## Architecture
- `episodes/<id>.json` is the single source of truth: shots, camera poses, events, overlays and sfx. The format is in docs/EPISODE_FORMAT.md.
- `blender/build_scene.py` runs inside Blender. It resets the scene, calls `scenes.<scene>.build(ctx)`, sets up the camera, applies events, animates the camera, exports label tracking, then renders. Scenes are **Python, not .blend files**, so the PC and the Mac stay identical.
- `blender/lib/` holds the bmesh primitives (`shapes`), cel material + inverted-hull outline (`toon`), the camera rig (`cameras`), timeline actions (`actions`), screen-space tracking (`tracking`) and model import (`assets`).
- Renders come out with a transparent film. The pipeline compositor (`pipeline/overlays.py`) paints the sky gradient, the 3D frame and the 2D overlays, then pipes raw frames into ffmpeg.
- The timeline (`pipeline/episode.compute_timing`) stretches shots to fit the narration. If the voice changes, the frames must be re-rendered.

## Rules
- Always preview, and look at the contact sheet yourself with Read, before a full render. Fix it yourself for up to 3 rounds, then ask.
- Approval points: (1) the script and sources, before the scene work; (2) the preview stills, before the full render.
- No automatic YouTube upload. The pipeline stops at the MP4.
- Keep the look consistent: use `toon.PALETTE` colours and the shared sets, and keep new props in the same flat, toy-like style.
- Final scene changes go into code (scene module or episode JSON), even if you explored them through Blender MCP.
- Target Blender 4.5 LTS. The code handles both Eevee Legacy and Eevee Next property names.
- Record the licence of every external model in `assets/models/README.md`.

## Status (2026-11-18)
- Boilerplate is complete. The non-Blender parts were tested on macOS with Python 3.12: validate, timeline, captions, overlay rendering and the audio mix.
- **Not yet tested:** any Blender run (the scene build, Eevee render, tracking), the ffmpeg encode, and the voice backends. Expect small fixes to API details and camera framing on the first PC run.
- Open decisions: the voice backend (Kokoro or ElevenLabs), and checking YouTube's policy on repetitive or mass-produced content before publishing at volume.
