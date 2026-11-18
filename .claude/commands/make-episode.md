---
description: Make a 3D explainer Short end to end (script -> scene -> preview -> render -> MP4) with two approval stops
argument-hint: <topic or episode id>, e.g. "how smart meters work"
---

Make an episode for: **$ARGUMENTS**

Follow CLAUDE.md. Use the project venv's Python (`.venv\Scripts\python` on Windows, `.venv/bin/python` on macOS) for every `make_episode.py` command.

## 1. Script (approval stop 1)
- Pick a snake_case id. If `episodes/<id>.json` already exists, skip to step 2.
- Research the topic on the web. Use reliable sources and put their URLs in `"sources"`.
- Write `episodes/<id>.json` following docs/EPISODE_FORMAT.md:
  - 7-10 shots, 30-60 s total, a hook in the first 3 s, one fact per shot, and a teaser for the next episode at the end.
  - Narration should be short and spoken, at most about 20 words per shot. Wrap 1-2 key words per shot in `*asterisks*`.
  - Every label anchor, camera target and event must name something the scene module registers.
  - Keep `"fact_checked": false`.
- Run `make_episode.py validate <id>`.
- **STOP.** Show the user a table of the shots (narration plus what's on screen) and the sources. Wait for their approval or edits. Set `fact_checked: true` only after they confirm the facts.

## 2. Scene
- If `blender/scenes/<scene>.py` doesn't exist, write it. Follow docs/SCENES.md: reuse `scenes.street` and the `lib.shapes` primitives, and keep the cel style.
  You can explore layouts interactively with the Blender MCP server (docs/BLENDER_MCP.md), but the final result must be code in the scene module.
- Prefer code primitives. Only if an object really needs detail, import a model with `lib.assets.import_model`, and note its licence in assets/models/README.md.

## 3. Voice + preview (approval stop 2)
- Run `make_episode.py voice <id>`. Use the backend from config, or `--backend system` for a quick timing check.
- Run `make_episode.py preview <id> --shots all`.
- Open `output/<id>/preview/contact_sheet.png` and each `final_*.png` with the Read tool and critique them yourself. Check that labels sit on their objects, nothing is cut off or hidden, the camera frames the subject, and text doesn't overlap.
  Fix the episode JSON or the scene module and re-run the preview until it looks right. Don't go past 3 self-fix rounds without asking.
- **STOP.** Show the user the contact sheet and ask for approval before the full render.

## 4. Render + assemble
- Run `make_episode.py render <id>`. It's long, so run it in the background and report progress. If it fails, read `output/<id>/logs/blender_full.log`.
- Run `make_episode.py assemble <id>`.
- Report the MP4 path, its duration, and anything you weren't sure about. Never upload anywhere.
