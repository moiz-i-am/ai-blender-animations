"""Build, animate and render one episode inside Blender.

Normally called by the pipeline (python make_episode.py preview|render|blend <episode>), which runs:

  blender -b --factory-startup -noaudio --python-exit-code 1 -P blender/build_scene.py -- \
      --episode episodes/traffic_camera.json --timing output/traffic_camera/timing.json \
      --out output/traffic_camera --mode preview

Modes
  preview  render a few stills at shot midpoints -> <out>/preview/raw_*.png (+ index.json)
  full     render every frame                    -> <out>/frames/frame_0001.png ...
  blend    only save <out>/scene.blend (open it in Blender to inspect or tweak via MCP)
  stills   render the frames given by --frames  -> <out>/stills/

Also works with a Python that has the `bpy` module: python blender/build_scene.py -- ...
"""
import argparse
import importlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import bpy  # noqa: E402

from lib import actions as generic_actions  # noqa: E402
from lib import cameras, render, tracking  # noqa: E402
from lib.context import SceneContext  # noqa: E402

TAG = "[shorts3d]"


def log(*a):
    print(TAG, *a, flush=True)


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else argv[1:]
    p = argparse.ArgumentParser()
    p.add_argument("--episode", required=True)
    p.add_argument("--timing", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--mode", default="preview", choices=["preview", "full", "blend", "stills"])
    p.add_argument("--engine", default="eevee", choices=["eevee", "workbench"])
    p.add_argument("--scale", type=int, default=None, help="resolution percentage")
    p.add_argument("--samples", type=int, default=None)
    p.add_argument("--frames", default=None, help="full: '1-120'; stills: '10,45,90'")
    p.add_argument("--preview-shots", default="4", help="number of shots to preview, or 'all'")
    p.add_argument("--resume", action="store_true", help="full: keep already-rendered frames")
    p.add_argument("--save-blend", action="store_true")
    return p.parse_args(argv)


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def apply_events(ctx, scene_mod):
    actions = dict(generic_actions.ACTIONS)
    actions.update(getattr(scene_mod, "ACTIONS", {}))
    queue = []
    for shot, t in ctx.shots():
        for ev in shot.get("events", []):
            f0 = t["start_frame"] + int(round(float(ev.get("t", 0)) * ctx.fps))
            f1 = f0 + max(1, int(round(float(ev.get("duration", 1.0)) * ctx.fps)))
            queue.append((f0, f1, ev, shot["id"]))
    queue.sort(key=lambda q: q[0])
    for f0, f1, ev, sid in queue:
        name = ev["action"]
        if name not in actions:
            raise KeyError(f"Shot '{sid}': unknown action '{name}'. Available: {sorted(actions)}")
        actions[name](ctx, f0, f1, ev.get("params", {}))


def anchors_used(ep):
    names = set()
    for shot in ep["shots"]:
        for ov in shot.get("overlays", []):
            if ov.get("anchor"):
                names.add(ov["anchor"])
    return sorted(names)


def preview_frames(ctx, how_many):
    pairs = list(ctx.shots())
    if how_many != "all":
        n = max(1, int(how_many))
        if n < len(pairs):
            step = (len(pairs) - 1) / (n - 1) if n > 1 else 0
            pairs = [pairs[round(i * step)] for i in range(n)]
    out = []
    for shot, t in pairs:
        mid = (t["start_frame"] + t["end_frame"]) // 2
        # bias towards the moment overlays/events usually happen
        out.append((shot["id"], mid))
    return out


def render_still(scene, frame, path):
    scene.frame_set(frame)
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


def main():
    t_start = time.time()
    a = parse_args()
    with open(a.episode, encoding="utf-8") as fh:
        ep = json.load(fh)
    with open(a.timing, encoding="utf-8") as fh:
        timing = json.load(fh)
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)

    reset_scene()
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = int(timing["total_frames"])

    ctx = SceneContext(ep, timing, a)
    scale = a.scale or (50 if a.mode == "preview" else 100)
    samples = a.samples or (8 if a.mode == "preview" else 16)
    engine_id = render.configure(scene, ep, engine=a.engine, scale=scale, samples=samples)
    log(f"Blender {bpy.app.version_string} | engine {engine_id} | {scale}% | mode {a.mode}")

    scene_mod = importlib.import_module(f"scenes.{ep['scene']}")
    light_cfg = dict(getattr(scene_mod, "LIGHTING", {}))
    light_cfg.update(ep.get("lighting", {}))
    render.lighting(ctx, **light_cfg)

    scene_mod.build(ctx)
    log(f"built scene '{ep['scene']}' with {len(ctx.objects)} named objects")
    cameras.setup(ctx)
    apply_events(ctx, scene_mod)
    cameras.animate(ctx)

    anchors = anchors_used(ep)
    missing = [n for n in anchors if not ctx.has(n)]
    if missing:
        raise KeyError(f"Overlay anchors not found in scene: {missing}. Known: {sorted(ctx.objects)}")

    if a.save_blend or a.mode == "blend":
        path = os.path.join(out, "scene.blend")
        bpy.ops.wm.save_as_mainfile(filepath=path)
        log(f"saved {path}")

    if a.mode == "preview":
        prev_dir = os.path.join(out, "preview")
        os.makedirs(prev_dir, exist_ok=True)
        frames = preview_frames(ctx, a.preview_shots)
        tracking.export(ctx, anchors, os.path.join(prev_dir, "tracking.json"), [f for _, f in frames])
        index = []
        for i, (sid, f) in enumerate(frames):
            path = os.path.join(prev_dir, f"raw_{i:02d}_{sid}.png")
            render_still(scene, f, path)
            index.append({"shot": sid, "frame": f, "raw": path})
            log(f"preview {i + 1}/{len(frames)}: shot {sid} frame {f}")
        with open(os.path.join(prev_dir, "index.json"), "w", encoding="utf-8") as fh:
            json.dump({"scale": scale, "frames": index}, fh, indent=2)

    elif a.mode == "stills":
        st_dir = os.path.join(out, "stills")
        os.makedirs(st_dir, exist_ok=True)
        for f in [int(x) for x in (a.frames or "1").split(",")]:
            render_still(scene, f, os.path.join(st_dir, f"still_{f:04d}.png"))
            log(f"still frame {f}")

    elif a.mode == "full":
        tracking.export(ctx, anchors, os.path.join(out, "tracking.json"))
        frames_dir = os.path.join(out, "frames")
        os.makedirs(frames_dir, exist_ok=True)
        if a.frames:
            s, e = a.frames.split("-")
            scene.frame_start, scene.frame_end = int(s), int(e)
        scene.render.filepath = os.path.join(frames_dir, "frame_")
        scene.render.use_overwrite = not a.resume
        scene.render.use_placeholder = False
        log(f"rendering frames {scene.frame_start}-{scene.frame_end} -> {frames_dir}")
        bpy.ops.render.render(animation=True)

    log(f"done in {time.time() - t_start:.1f}s")


if __name__ == "__main__":
    main()
