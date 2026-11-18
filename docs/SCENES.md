# Writing scene modules (`blender/scenes/*.py`)

A scene module builds the 3D world for one episode. It runs inside Blender. You don't need to open the Blender UI.

```python
from lib import shapes as S, toon, actions as A
from scenes import street

def build(ctx):
    street.build(ctx)                                   # reuse the shared neighbourhood
    S.cylinder(ctx, "meter_post", radius=0.05, depth=1.0, loc=(-7.4, 1.5, 0.6), mat="pole")
    S.box(ctx, "smart_meter", size=(0.4, 0.15, 0.55), loc=(-7.35, 1.5, 1.2), mat="camera_body", bevel=0.02)
    screen = toon.glow("meter_screen", (0.3, 1.0, 0.6), strength=0.8)
    S.box(ctx, "meter_screen", size=(0.25, 0.02, 0.12), loc=(-7.27, 1.5, 1.5), mat=screen, outline=False)

def pulse(ctx, f0, f1, p):
    A.blink(ctx, f0, f1, {"material": "meter_screen", "period": 0.4})

ACTIONS = {"pulse": pulse}
```

## Rules
- **Register every name** the episode references, whether it's a camera target, a label anchor or an object in an event. Every helper registers by default. Pass `register=False` for small details.
- Use **metres**, with **+Z up**. Sizes are baked into the mesh, so keep the object scale at 1.
- The origin defaults to the **bottom centre**, so `loc=(x, y, 0)` sits on the ground.
- Use `S.empty(ctx, "name", loc)` for invisible anchor points, such as a spot on a wall for a label.
- Parent parts to an empty to move them as a group, as the `car` does in `traffic_camera.py`. Child positions are then relative to that empty.

## Helpers (`blender/lib`)

| Helper | Use |
|--------|-----|
| `shapes.box / cylinder / cone / sphere / roof / empty / point_light / aim` | primitives |
| `toon.toon(name, color)` | cel material (two-tone) |
| `toon.glow(name, color, strength, alpha)` | lamps, screens, beams. Keyframe them with the `blink`, `flash` and `glow` actions |
| `toon.PALETTE` | shared colours. Use these names so every episode looks consistent |
| `assets.import_model(ctx, name, "assets/models/x.glb", loc, rot, scale)` | external model, converted to cel style |
| `ctx.hide_at_start(name)` | start hidden, then reveal with the `show` action |

## Shared sets
- `scenes/street.py` holds the road along Y, houses at x = ±11, trees and street lights. The anchors `house_main` and `house_main_front` are on the left house at y = 0, which is meant for the smart-meter episode.
- When something is reusable, such as a house interior or a power pole, put it in its own module (`scenes/house_interior.py`) with a `build(ctx, ...)` function, and import it from episode scenes.

## Where objects come from (cheapest first)
1. **Code primitives**: free, instant and always on-style. This covers most props.
2. **Model libraries** like Poly Haven (CC0) or Sketchfab (check each licence). Use `.glb`.
3. **AI 3D generators**: Meshy or Tripo (hosted), or TRELLIS 2 or Hunyuan3D (local, on the RTX 3060). Export `.glb`, put it in `assets/models/`, and import it with `import_model`. Expect to clean up geometry sometimes.

Record the source and licence of every external model in `assets/models/README.md`.
