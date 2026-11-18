"""Export screen-space positions of anchors so 2D labels can follow 3D objects."""
import json

from bpy_extras.object_utils import world_to_camera_view


def export(ctx, names, path, frames=None):
    """Write {"fps", "frames": [..], "anchors": {name: [[x, y, visible], ...]}}.

    x, y are 0-1 from the top-left of the frame. One entry per frame in `frames`
    (default: every frame of the scene).
    """
    scene = ctx.scene
    cam = scene.camera
    if frames is None:
        frames = list(range(scene.frame_start, scene.frame_end + 1))
    data = {"fps": ctx.fps, "frames": frames, "anchors": {n: [] for n in names}}
    for f in frames:
        scene.frame_set(f)
        for n in names:
            co = world_to_camera_view(scene, cam, ctx.world_point(n))
            x, y = float(co.x), 1.0 - float(co.y)
            vis = co.z > 0 and -0.05 <= x <= 1.05 and -0.05 <= y <= 1.05
            data["anchors"][n].append([round(x, 4), round(y, 4), bool(vis)])
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh)
    return path
