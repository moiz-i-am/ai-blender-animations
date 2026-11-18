"""Episode 1: how traffic cameras work.

Street set + an enforcement pole on the right sidewalk at y = 0:
  pole, pole_arm, radar_unit (over the right lane), camera_unit (+ lens, hood, rec_light),
  flash_unit, flash_light, radar_cone (hidden until "radar_on"), road loop sensors,
  a car that drives along the right lane towards +Y.

Registered anchors for labels / camera targets:
  pole_top, radar_unit, camera_unit, flash_unit, road_sensor, car, car_plate
"""
from mathutils import Vector

from lib import actions as A
from lib import shapes as S
from lib import toon
from scenes import street

PX, PY = 4.3, 0.0           # pole position
LANE_X = 1.75               # right lane centre
CAR_START = (LANE_X, -40.0, 0.0)
CAR_END = (LANE_X, 8.0, 0.0)


def build(ctx):
    street.build(ctx)
    _pole(ctx)
    _sensors(ctx)
    _car(ctx)


def _pole(ctx):
    S.cylinder(ctx, "pole", radius=0.13, depth=6.2, segments=16, loc=(PX, PY, 0), mat="pole")
    S.box(ctx, "pole_arm", size=(2.8, 0.18, 0.18), loc=(PX - 1.4, PY, 5.9), mat="pole")

    # Radar hangs under the arm above the lane, facing oncoming traffic (-Y)
    rx = PX - 2.4
    S.box(ctx, "radar_unit", size=(0.7, 0.45, 0.5), loc=(rx, PY, 5.3), mat="camera_body", bevel=0.03)
    S.box(ctx, "radar_face", size=(0.56, 0.04, 0.36), loc=(rx, PY - 0.245, 5.37),
          mat="metal_dark", outline=False)

    # Camera housing on the pole
    cx = PX - 0.4
    S.box(ctx, "camera_unit", size=(0.5, 1.1, 0.5), loc=(cx, PY, 4.6), mat="camera_body", bevel=0.03)
    S.box(ctx, "camera_hood", size=(0.62, 0.55, 0.06), loc=(cx, PY - 0.42, 5.1), mat="camera_body",
          register=False)
    S.cylinder(ctx, "camera_lens", radius=0.16, depth=0.12, loc=(cx, PY - 0.6, 4.85),
               rot=(90, 0, 0), mat="glass", origin="center")
    rec = toon.glow("rec_glow", (1.0, 0.12, 0.12), strength=0.3)
    S.sphere(ctx, "rec_light", radius=0.05, loc=(cx + 0.17, PY - 0.56, 5.0), mat=rec, outline=False)

    # Flash unit below the camera
    S.box(ctx, "flash_unit", size=(0.45, 0.3, 0.35), loc=(cx, PY, 3.85), mat="camera_body", bevel=0.02)
    fg = toon.glow("flash_glass", (1.0, 0.98, 0.9), strength=0.3)
    S.box(ctx, "flash_face", size=(0.36, 0.03, 0.26), loc=(cx, PY - 0.16, 3.9), mat=fg, outline=False,
          register=False)
    S.point_light(ctx, "flash_light", loc=(cx, PY - 1.0, 4.0), energy=0.0, color=(1, 1, 1), radius=0.3)

    # Radar beam: cone with its tip at the radar face, opening towards the road
    beam = toon.glow("radar_beam", (1.0, 0.3, 0.25), strength=1.2, alpha=0.28)
    apex = Vector((rx, PY - 0.27, 5.37))
    aim_at = Vector((LANE_X, PY - 13.0, 0.0))
    length = (aim_at - apex).length
    cone = S.cone(ctx, "radar_cone", radius1=2.2, radius2=0.0, depth=length, segments=24,
                  loc=apex, mat=beam, outline=False, origin="top")
    # cone axis is local +Z (tip at origin, base at -Z): point local -Z at the road
    S.aim(cone, aim_at)
    ctx.hide_at_start("radar_cone")

    S.empty(ctx, "pole_top", loc=(PX, PY, 6.2))


def _sensors(ctx):
    """Inductive loop sensors cut into the lane (two rectangles)."""
    for k, sy in enumerate((-10.0, -6.5)):
        w, d, t = 2.2, 1.6, 0.08
        for j, (sx, sz, ox, oy) in enumerate(((w, t, 0, d / 2), (w, t, 0, -d / 2),
                                              (t, d, w / 2, 0), (t, d, -w / 2, 0))):
            S.box(ctx, f"loop{k}_{j}", size=(sx, sz, 0.01), loc=(LANE_X + ox, sy + oy, 0.025),
                  mat="sensor", outline=False, register=False)
    S.empty(ctx, "road_sensor", loc=(LANE_X, -8.25, 0.05))


def _car(ctx):
    car = S.empty(ctx, "car", loc=CAR_START)
    S.box(ctx, "car_body", size=(1.8, 4.2, 0.75), loc=(0, 0, 0.32), mat="car", parent=car, bevel=0.08)
    S.box(ctx, "car_cabin", size=(1.6, 2.2, 0.62), loc=(0, -0.25, 1.07), mat="window", parent=car,
          bevel=0.06)
    for k, (wx, wy) in enumerate(((0.86, 1.35), (-0.86, 1.35), (0.86, -1.35), (-0.86, -1.35))):
        S.cylinder(ctx, f"car_wheel{k}", radius=0.36, depth=0.3, segments=16, loc=(wx, wy, 0.36),
                   rot=(0, 90, 0), mat="tire", parent=car, origin="center", register=False)
    head = toon.glow("headlight_glow", (1.0, 0.96, 0.8), strength=1.5)
    for k, hx in enumerate((0.6, -0.6)):
        S.box(ctx, f"car_headlight{k}", size=(0.35, 0.05, 0.15), loc=(hx, 2.11, 0.75), mat=head,
              parent=car, outline=False, register=False)
    S.box(ctx, "car_plate", size=(0.6, 0.04, 0.16), loc=(0, 2.12, 0.42), mat="plate", parent=car,
          outline=0.01)


# ---- episode-specific actions --------------------------------------------

def car_drive(ctx, f0, f1, p):
    A.move(ctx, f0, f1, {"object": "car", "from": p.get("from", list(CAR_START)),
                         "to": p.get("to", list(CAR_END)), "ease": p.get("ease", "linear")})


def radar_on(ctx, f0, f1, p):
    A.show(ctx, f0, f1, {"object": "radar_cone", "frames": p.get("frames", 8)})


def radar_off(ctx, f0, f1, p):
    A.hide(ctx, f0, f1, {"object": "radar_cone", "frames": p.get("frames", 6)})


def camera_flash(ctx, f0, f1, p):
    A.flash(ctx, f0, f1, {"light": "flash_light", "energy": p.get("energy", 3000),
                          "material": "flash_glass", "glow": p.get("glow", 40)})


def rec_blink(ctx, f0, f1, p):
    A.blink(ctx, f0, f1, {"material": "rec_glow", "period": p.get("period", 0.6), "on": 6.0, "off": 0.3})


ACTIONS = {
    "car_drive": car_drive,
    "radar_on": radar_on,
    "radar_off": radar_off,
    "camera_flash": camera_flash,
    "rec_blink": rec_blink,
}
