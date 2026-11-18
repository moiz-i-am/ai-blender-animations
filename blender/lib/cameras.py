"""Camera rig + per-shot camera animation.

Each shot's "camera" in the episode JSON is one of:

  {"from": POSE, "to": POSE, "ease": "ease_in_out"}    # glide between two poses
  {"to": POSE}                                         # continue from the previous shot's end pose
  {"orbit": {"center": POINT, "radius": 20, "height": 12,
             "start": -100, "end": -70, "lens": 30}}  # arc around a point (degrees, 0 = +X axis)

POSE  = {"pos": POINT, "target": POINT, "lens": 35}
POINT = [x, y, z] | "object_name" | {"anchor": "object_name", "offset": [x, y, z]}

Lens is in mm on the frame's long (vertical) side; 25-30 = wide, 50+ = tight.
"""
import math

import bpy
from mathutils import Vector

from .anim import ease_mode, key


def setup(ctx):
    data = bpy.data.cameras.new("ShotCam")
    data.lens = 35
    data.sensor_fit = "AUTO"
    data.clip_start = 0.1
    data.clip_end = 1000
    cam = bpy.data.objects.new("ShotCam", data)
    ctx.collection.objects.link(cam)
    ctx.scene.camera = cam

    target = bpy.data.objects.new("ShotCamTarget", None)
    ctx.collection.objects.link(target)
    con = cam.constraints.new("TRACK_TO")
    con.target = target
    con.track_axis = "TRACK_NEGATIVE_Z"
    con.up_axis = "UP_Y"

    ctx.camera, ctx.cam_target = cam, target
    return cam


def _key_pose(ctx, pose, frame, interp):
    pos = ctx.point(pose["pos"], frame)
    tgt = ctx.point(pose.get("target", [0, 0, 0]), frame)
    key(ctx.camera, "location", frame, value=pos, interp=interp)
    key(ctx.cam_target, "location", frame, value=tgt, interp=interp)
    key(ctx.camera.data, "lens", frame, value=float(pose.get("lens", 35)), interp=interp)


def _smooth(x):
    return x * x * (3 - 2 * x)


def _orbit(ctx, cfg, f0, f1):
    center = ctx.point(cfg.get("center", [0, 0, 0]), f0)
    r = float(cfg.get("radius", 20))
    h = float(cfg.get("height", 10))
    a0, a1 = math.radians(cfg.get("start", 0)), math.radians(cfg.get("end", 30))
    lens = float(cfg.get("lens", 35))
    step = 3
    frames = list(range(f0, f1, step)) + [f1]
    for f in frames:
        u = _smooth((f - f0) / max(1, f1 - f0))
        a = a0 + (a1 - a0) * u
        pos = center + Vector((r * math.cos(a), r * math.sin(a), h))
        key(ctx.camera, "location", f, value=pos, interp="LINEAR")
        key(ctx.cam_target, "location", f, value=center, interp="LINEAR")
        key(ctx.camera.data, "lens", f, value=lens, interp="LINEAR")
    end = center + Vector((r * math.cos(a1), r * math.sin(a1), h))
    return {"pos": list(end), "target": list(center), "lens": lens}


def animate(ctx):
    prev = None
    for shot, t in ctx.shots():
        cfg = shot.get("camera") or {}
        f0, f1 = t["start_frame"], t["end_frame"]
        if "orbit" in cfg:
            prev = _orbit(ctx, cfg["orbit"], f0, f1)
            continue
        interp = ease_mode(cfg.get("ease", "ease_in_out"))
        a = cfg.get("from") or prev
        if a is None:
            raise ValueError(f"Shot '{shot['id']}' needs camera.from (it is the first shot)")
        b = cfg.get("to") or a
        _key_pose(ctx, a, f0, interp)
        _key_pose(ctx, b, f1, interp)
        prev = b
