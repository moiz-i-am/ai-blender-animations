"""Generic timeline actions usable from any episode's "events".

Each action has the signature  fn(ctx, f0, f1, params)
  f0 = start frame, f1 = end frame (start + duration), params = dict from the JSON.

Scene modules can add their own actions in an ACTIONS dict; those override these.
"""
from mathutils import Vector

from . import toon
from .anim import ease_mode, key


def _obj(ctx, params, key_name="object"):
    try:
        return ctx.get(params[key_name])
    except KeyError as e:
        raise KeyError(f"Action needs params.{key_name}: {e}") from None


def move(ctx, f0, f1, p):
    """{"object": name, "to": [x,y,z] | "by": [dx,dy,dz], "from": [..] optional, "ease": "linear"}"""
    obj = _obj(ctx, p)
    interp = ease_mode(p.get("ease", "linear"))
    ctx.goto(f0)
    if "from" in p:
        obj.location = p["from"]
    start = Vector(obj.location)
    key(obj, "location", f0, interp=interp)
    obj.location = p["to"] if "to" in p else start + Vector(p.get("by", (0, 0, 0)))
    key(obj, "location", f1, interp=interp)


def rotate(ctx, f0, f1, p):
    """{"object": name, "by": [dx,dy,dz] degrees, "ease": "ease_in_out"}"""
    import math
    obj = _obj(ctx, p)
    interp = ease_mode(p.get("ease", "ease_in_out"))
    ctx.goto(f0)
    start = Vector(obj.rotation_euler)
    key(obj, "rotation_euler", f0, interp=interp)
    obj.rotation_euler = start + Vector([math.radians(a) for a in p.get("by", (0, 0, 90))])
    key(obj, "rotation_euler", f1, interp=interp)


def show(ctx, f0, f1, p):
    """Pop an object in (scale 0 -> full with a small overshoot). {"object": name, "frames": 8}"""
    obj = _obj(ctx, p)
    full = Vector(ctx.base_scale.get(p["object"], (1, 1, 1)))
    n = int(p.get("frames", 8))
    key(obj, "scale", f0, value=(0, 0, 0))
    key(obj, "scale", f0 + int(n * 0.7), value=full * 1.12)
    key(obj, "scale", f0 + n, value=full)


def hide(ctx, f0, f1, p):
    """Shrink an object away. {"object": name, "frames": 6}"""
    obj = _obj(ctx, p)
    n = int(p.get("frames", 6))
    ctx.goto(f0)
    key(obj, "scale", f0)
    key(obj, "scale", f0 + n, value=(0, 0, 0))


def blink(ctx, f0, f1, p):
    """Blink a glow material on/off between f0 and f1.
    {"material": name, "period": 0.6 (s), "on": 4.0, "off": 0.0}"""
    mat = p["material"]
    period = max(2, int(round(float(p.get("period", 0.6)) * ctx.fps)))
    on, off = float(p.get("on", 4.0)), float(p.get("off", 0.0))
    from .anim import interpolation
    with interpolation("CONSTANT"):
        f, state = f0, True
        while f < f1:
            toon.set_glow(mat, on if state else off, frame=f)
            f += period // 2
            state = not state
        toon.set_glow(mat, off, frame=f1)


def flash(ctx, f0, f1, p):
    """Camera-flash burst: light energy spike and/or glow material spike.
    {"light": name, "energy": 3000, "material": name, "glow": 30}"""
    if p.get("light"):
        light = ctx.get(p["light"]).data
        peak = float(p.get("energy", 3000))
        key(light, "energy", f0 - 1, value=0.0)
        key(light, "energy", f0, value=peak)
        key(light, "energy", f0 + 2, value=peak)
        key(light, "energy", f0 + 7, value=0.0)
    if p.get("material"):
        mat = p["material"]
        base = float(p.get("base_glow", 0.3))
        peak = float(p.get("glow", 30.0))
        toon.set_glow(mat, base, frame=f0 - 1)
        toon.set_glow(mat, peak, frame=f0)
        toon.set_glow(mat, peak, frame=f0 + 2)
        toon.set_glow(mat, base, frame=f0 + 7)


def glow(ctx, f0, f1, p):
    """Fade a glow material's strength. {"material": name, "to": 5.0, "from": optional}"""
    mat = p["material"]
    node = __import__("bpy").data.materials[mat].node_tree.nodes[toon.GLOW_NODE]
    ctx.goto(f0)
    start = float(p.get("from", node.inputs["Strength"].default_value))
    toon.set_glow(mat, start, frame=f0)
    toon.set_glow(mat, float(p["to"]), frame=f1)


ACTIONS = {
    "move": move,
    "rotate": rotate,
    "show": show,
    "hide": hide,
    "blink": blink,
    "flash": flash,
    "glow": glow,
}
