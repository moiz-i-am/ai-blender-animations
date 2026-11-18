---
description: Render preview stills for an episode, review them, and fix problems
argument-hint: <episode id>
---

1. Run `make_episode.py preview $ARGUMENTS --shots all` with the venv Python.
2. Read `output/$ARGUMENTS/preview/contact_sheet.png`, then any `final_*.png` that looks wrong.
3. List the visual problems you find: framing, labels off their objects, overlapping text, objects hidden or clipped, wrong colours.
4. Propose concrete fixes, giving camera pos/target/lens values or scene code changes. Apply them only if the user agrees.
