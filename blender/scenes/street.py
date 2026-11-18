"""Reusable neighbourhood set: a straight road along +Y, sidewalks, houses, trees, street lights.

Coordinates (metres):
  road centre line  x = 0, running along Y from -80 to +80
  traffic lane      right lane centre x = +1.75 (cars drive towards +Y)
  sidewalks         x = +/-4.7
  houses            x = +/-11, fronts face the road
  "house_main"      the left-side house at y = 0 (used by the smart-meter episode)

Registered anchors: street_center, house_main, house_main_front (point on its front wall)
"""
import random

from lib import shapes as S
from lib import toon

ROAD_W = 7.0
LENGTH = 160.0


def build(ctx, seed=7, house_ys=(-54, -36, -18, 0, 18, 36), trees=True, lights=True):
    rnd = random.Random(seed)
    half = LENGTH / 2

    S.box(ctx, "ground", size=(140, LENGTH + 20, 0.2), loc=(0, 0, -0.2), mat="ground", outline=False)
    S.box(ctx, "road", size=(ROAD_W, LENGTH, 0.02), loc=(0, 0, 0), mat="asphalt", outline=False)

    # lane markings
    y = -half + 2
    i = 0
    while y < half:
        S.box(ctx, f"dash_{i}", size=(0.15, 1.8, 0.012), loc=(0, y, 0.02), mat="lane",
              outline=False, register=False)
        y += 4.0
        i += 1
    for side in (-1, 1):
        S.box(ctx, f"edge_line_{side}", size=(0.12, LENGTH, 0.012), loc=(side * 3.2, 0, 0.02),
              mat="lane", outline=False, register=False)
        S.box(ctx, f"sidewalk_{side}", size=(2.4, LENGTH, 0.15), loc=(side * 4.7, 0, 0),
              mat="sidewalk", outline=0.015, register=False)
        S.box(ctx, f"curb_{side}", size=(0.2, LENGTH, 0.17), loc=(side * 3.55, 0, 0),
              mat="curb", outline=False, register=False)

    walls = ["wall_a", "wall_b", "wall_c", "wall_d"]
    roofs = ["roof", "roof_b"]
    for side in (-1, 1):
        for j, hy in enumerate(house_ys):
            name = f"house_{'L' if side < 0 else 'R'}{j}"
            _house(ctx, name, x=side * 11.0, y=hy, facing=-side,
                   wall=rnd.choice(walls), roof=rnd.choice(roofs),
                   height=rnd.choice((4.0, 4.5, 5.5)))
            if trees:
                _tree(ctx, f"{name}_tree", x=side * 7.3, y=hy + 9 + rnd.uniform(-1, 1),
                      size=rnd.uniform(0.85, 1.2))

    if lights:
        for k, ly in enumerate(range(-60, 61, 24)):
            _street_light(ctx, f"streetlight_{k}", x=-4.6, y=ly)

    S.empty(ctx, "street_center", loc=(0, 0, 0))
    S.empty(ctx, "house_main_front", loc=(-7.5, 0, 2.0))
    ctx.objects["house_main"] = ctx.get("house_L3")


def _house(ctx, name, x, y, facing, wall, roof, height=4.5, width=7.0, depth=8.0):
    """facing = +1 -> front wall faces +X, -1 -> faces -X."""
    root = S.empty(ctx, name, loc=(x, y, 0))
    S.box(ctx, f"{name}_body", size=(width, depth, height), mat=wall, parent=root, bevel=0.04)
    S.roof(ctx, f"{name}_roof", width=width + 0.6, depth=depth + 0.6, height=2.2,
           loc=(0, 0, height), mat=roof, parent=root)
    fx = facing * (width / 2 + 0.04)
    S.box(ctx, f"{name}_door", size=(0.1, 1.2, 2.1), loc=(fx, 0, 0), mat="door", parent=root,
          outline=0.015, register=False)
    for k, wy in enumerate((-2.4, 2.4)):
        S.box(ctx, f"{name}_win{k}", size=(0.1, 1.4, 1.1), loc=(fx, wy, height * 0.45),
              mat="window", parent=root, outline=0.015, register=False)
    return root


def _tree(ctx, name, x, y, size=1.0):
    root = S.empty(ctx, name, loc=(x, y, 0), register=False)
    S.cylinder(ctx, f"{name}_trunk", radius=0.18 * size, depth=1.5 * size, segments=8,
               mat="trunk", parent=root, register=False)
    S.sphere(ctx, f"{name}_crown", radius=1.3 * size, segments=8, rings=6,
             loc=(0, 0, 2.4 * size), mat="leaf", parent=root, register=False)


def _street_light(ctx, name, x, y):
    root = S.empty(ctx, name, loc=(x, y, 0), register=False)
    S.cylinder(ctx, f"{name}_pole", radius=0.08, depth=5.0, segments=10, mat="pole",
               parent=root, register=False)
    S.box(ctx, f"{name}_arm", size=(1.4, 0.1, 0.1), loc=(0.7, 0, 4.9), mat="pole",
          parent=root, register=False)
    lamp = toon.glow("streetlamp_glow", (1.0, 0.95, 0.75), strength=1.0)
    S.box(ctx, f"{name}_lamp", size=(0.5, 0.25, 0.12), loc=(1.3, 0, 4.78), mat=lamp,
          parent=root, outline=0.015, register=False)
