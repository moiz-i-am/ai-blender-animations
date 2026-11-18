#!/usr/bin/env python3
"""shorts3d - one command line for the whole episode pipeline.

  python make_episode.py check                         verify installs
  python make_episode.py new smart_meter --scene smart_meter   scaffold an episode (+ scene module)
  python make_episode.py validate traffic_camera       check the episode JSON, print the timeline
  python make_episode.py voice traffic_camera          narration clips (stretches shots to fit)
  python make_episode.py preview traffic_camera        4 final-look stills (approval point)
  python make_episode.py render traffic_camera         render all frames (long)
  python make_episode.py assemble traffic_camera       overlays + audio -> MP4
  python make_episode.py all traffic_camera            voice -> render -> assemble
  python make_episode.py blend traffic_camera          save scene.blend to open in Blender
  python make_episode.py clean traffic_camera          delete output/<id>

Episode = name in episodes/ (traffic_camera) or a path to a .json file.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time

from pipeline import assemble as asm
from pipeline import blender_runner, voice
from pipeline.config import BLENDER_DIR, EPISODES_DIR, load_settings
from pipeline.episode import EpisodeError, load, out_dir, write_timing


def _timeline(ep, timing):
    print(f"\n  {ep['id']}: {len(timing['shots'])} shots, {timing['duration']:.1f}s, "
          f"{timing['total_frames']} frames @ {timing['fps']} fps")
    for s in timing["shots"]:
        print(f"    {s['id']:<16} {s['start']:6.2f}s - {s['end']:6.2f}s  "
              f"(frames {s['start_frame']}-{s['end_frame']})")
    print()


def _ensure_timing(ep):
    path, timing = write_timing(ep, voice.load_cached(ep))
    return timing


def cmd_check(a, s):
    from pipeline.check_env import main
    return main()


def cmd_new(a, s):
    dst = EPISODES_DIR / f"{a.id}.json"
    if dst.exists():
        print(f"{dst} already exists")
        return 1
    scene = a.scene or a.id
    tpl = json.loads((EPISODES_DIR / "_template.json").read_text(encoding="utf-8"))
    tpl["id"], tpl["scene"] = a.id, scene
    if a.title:
        tpl["title"] = a.title
    dst.write_text(json.dumps(tpl, indent=2), encoding="utf-8")
    print(f"created {dst}")
    scene_py = BLENDER_DIR / "scenes" / f"{scene}.py"
    if not scene_py.exists():
        shutil.copy(BLENDER_DIR / "scenes" / "_template.py", scene_py)
        print(f"created {scene_py}")
    return 0


def cmd_validate(a, s):
    ep = load(a.episode)
    _timeline(ep, _ensure_timing(ep))
    print("  episode OK")
    if not ep.get("fact_checked"):
        print("  NOTE: fact_checked is false - verify the narration before publishing.")
    return 0


def cmd_voice(a, s):
    ep = load(a.episode)
    v = voice.run(ep, s, backend=a.backend, force=a.force)
    print(f"  {len(v)} narration clips")
    _timeline(ep, _ensure_timing(ep))
    return 0


def cmd_preview(a, s):
    ep = load(a.episode)
    _timeline(ep, _ensure_timing(ep))
    if a.no_blender:
        asm.placeholder_preview(ep, s)
        return 0
    blender_runner.run(ep, s, "preview", engine=a.engine, scale=a.scale,
                       preview_shots=a.shots, verbose=a.verbose)
    asm.composite_preview(ep, s)
    return 0


def cmd_render(a, s):
    ep = load(a.episode)
    timing = _ensure_timing(ep)
    _timeline(ep, timing)
    frames_dir = out_dir(ep) / "frames"
    if frames_dir.exists() and not a.resume and not a.frames:
        shutil.rmtree(frames_dir)
    t0 = time.time()
    blender_runner.run(ep, s, "full", engine=a.engine, scale=a.scale, frames=a.frames,
                       resume=a.resume or bool(a.frames), verbose=a.verbose)
    frames_dir.mkdir(parents=True, exist_ok=True)
    (frames_dir / ".timing.json").write_text(json.dumps(timing), encoding="utf-8")
    print(f"  render finished in {(time.time() - t0) / 60:.1f} min")
    return 0


def cmd_assemble(a, s):
    ep = load(a.episode)
    if a.placeholder:
        _ensure_timing(ep)
    asm.assemble(ep, s, placeholder=a.placeholder, draft=a.draft)
    return 0


def cmd_all(a, s):
    ep = load(a.episode)
    if not a.skip_voice:
        voice.run(ep, s, backend=a.backend)
    a.resume, a.frames, a.scale = False, None, None
    cmd_render(a, s)
    asm.assemble(ep, s, draft=a.draft)
    return 0


def cmd_blend(a, s):
    ep = load(a.episode)
    _ensure_timing(ep)
    blender_runner.run(ep, s, "blend", engine=a.engine, verbose=a.verbose)
    print(f"  open {out_dir(ep) / 'scene.blend'} in Blender to inspect")
    return 0


def cmd_clean(a, s):
    ep = load(a.episode)
    d = out_dir(ep)
    shutil.rmtree(d)
    print(f"  removed {d}")
    return 0


def build_parser():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def ep_cmd(name, fn, help_):
        sp = sub.add_parser(name, help=help_)
        sp.add_argument("episode")
        sp.add_argument("--verbose", action="store_true", help="show full Blender output")
        sp.set_defaults(fn=fn)
        return sp

    sp = sub.add_parser("check", help="verify installs")
    sp.set_defaults(fn=cmd_check)

    sp = sub.add_parser("new", help="scaffold a new episode")
    sp.add_argument("id")
    sp.add_argument("--scene", help="scene module name (default = id)")
    sp.add_argument("--title")
    sp.set_defaults(fn=cmd_new)

    ep_cmd("validate", cmd_validate, "validate episode JSON and print timeline")

    sp = ep_cmd("voice", cmd_voice, "generate narration")
    sp.add_argument("--backend", choices=voice.BACKENDS)
    sp.add_argument("--force", action="store_true")

    sp = ep_cmd("preview", cmd_preview, "render preview stills")
    sp.add_argument("--engine", choices=["eevee", "workbench"])
    sp.add_argument("--scale", type=int, help="resolution %% (default 50)")
    sp.add_argument("--shots", default="4", help="how many shots to preview, or 'all'")
    sp.add_argument("--no-blender", action="store_true", help="overlay-only placeholder stills")

    sp = ep_cmd("render", cmd_render, "render all frames")
    sp.add_argument("--engine", choices=["eevee", "workbench"])
    sp.add_argument("--scale", type=int, help="resolution %% (default 100)")
    sp.add_argument("--frames", help="only render a range, e.g. 1-120 (keeps other frames)")
    sp.add_argument("--resume", action="store_true", help="skip frames that already exist")

    sp = ep_cmd("assemble", cmd_assemble, "overlays + audio -> MP4")
    sp.add_argument("--placeholder", action="store_true", help="no frames needed (sky + overlays only)")
    sp.add_argument("--draft", action="store_true", help="fast, lower-quality encode")

    sp = ep_cmd("all", cmd_all, "voice -> render -> assemble")
    sp.add_argument("--backend", choices=voice.BACKENDS)
    sp.add_argument("--engine", choices=["eevee", "workbench"])
    sp.add_argument("--skip-voice", action="store_true")
    sp.add_argument("--draft", action="store_true")

    sp = ep_cmd("blend", cmd_blend, "save scene.blend for inspection")
    sp.add_argument("--engine", choices=["eevee", "workbench"])

    ep_cmd("clean", cmd_clean, "delete output/<episode>")
    return p


def main(argv=None):
    a = build_parser().parse_args(argv)
    settings = load_settings()
    try:
        return a.fn(a, settings) or 0
    except (EpisodeError, RuntimeError, KeyError, FileNotFoundError) as e:
        print(f"\nERROR: {e}\n", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
