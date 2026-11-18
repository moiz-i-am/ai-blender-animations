"""TEMPLATE scene module - copied by `python make_episode.py new <id> --scene <name>`.

Rename objects/anchors to match what your episode JSON references
(camera targets, label anchors, event params).
"""
from lib import actions as A
from lib import shapes as S
from lib import toon
from scenes import street


def build(ctx):
    # Reuse the shared neighbourhood set (road, houses, trees). Remove if not needed.
    street.build(ctx)

    # Hero prop: a simple box on a post. Replace with your topic's objects,
    # or import a model:  from lib.assets import import_model
    #                     import_model(ctx, "hero", "assets/models/thing.glb", loc=(3, 0, 0))
    S.cylinder(ctx, "hero_post", radius=0.1, depth=1.2, loc=(5, 0, 0), mat="pole")
    S.box(ctx, "hero", size=(0.8, 0.5, 0.6), loc=(5, 0, 1.2), mat="camera_body", bevel=0.03)
    led = toon.glow("hero_led", (0.2, 1.0, 0.4), strength=0.5)
    S.sphere(ctx, "hero_led", radius=0.05, loc=(5, -0.26, 1.6), mat=led, outline=False)


def led_blink(ctx, f0, f1, p):
    A.blink(ctx, f0, f1, {"material": "hero_led", "period": p.get("period", 0.5)})


ACTIONS = {"led_blink": led_blink}
