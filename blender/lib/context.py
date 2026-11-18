"""SceneContext: the object every scene module and action receives."""
import bpy
from mathutils import Vector


class SceneContext:
    def __init__(self, episode, timing, args=None):
        self.ep = episode
        self.timing = timing
        self.args = args
        self.fps = int(episode.get("fps", 30))
        self.scene = bpy.context.scene
        self.collection = self.scene.collection
        self.objects = {}
        self.base_scale = {}
        self.outline = float(episode.get("style", {}).get("outline", 0.025))
        self.camera = None
        self.cam_target = None
        self._timing_by_id = {t["id"]: t for t in timing["shots"]}

    # ---- registry -------------------------------------------------------
    def register(self, name, obj):
        if name in self.objects:
            raise ValueError(f"Object name '{name}' registered twice")
        self.objects[name] = obj
        return obj

    def has(self, name):
        return name in self.objects

    def get(self, name):
        try:
            return self.objects[name]
        except KeyError:
            raise KeyError(f"Unknown object/anchor '{name}'. Known: {sorted(self.objects)}") from None

    def hide_at_start(self, name):
        """Start an object at scale 0 so a later `show` action pops it in."""
        obj = self.get(name)
        self.base_scale[name] = tuple(obj.scale)
        obj.scale = (0.0, 0.0, 0.0)

    # ---- time -----------------------------------------------------------
    def frame(self, seconds):
        """Absolute seconds -> 1-based frame number."""
        return int(round(seconds * self.fps)) + 1

    def goto(self, frame):
        self.scene.frame_set(int(frame))

    def shots(self):
        """Yield (shot_dict, timing_dict) pairs in order."""
        for shot in self.ep["shots"]:
            yield shot, self._timing_by_id[shot["id"]]

    # ---- points ---------------------------------------------------------
    def world_point(self, name, frame=None):
        """World position of a registered object: top-centre of its bounding box
        (meshes) or its origin (empties/lights)."""
        if frame is not None:
            self.goto(frame)
        obj = self.get(name)
        if obj.type == "MESH" and len(obj.data.vertices):
            bb = [Vector(c) for c in obj.bound_box]
            top = Vector((sum(c.x for c in bb) / 8, sum(c.y for c in bb) / 8, max(c.z for c in bb)))
            return obj.matrix_world @ top
        return obj.matrix_world.translation.copy()

    def point(self, spec, frame=None):
        """Resolve a point spec:
           [x, y, z]                               -> literal world point
           "name"                                  -> registered object's point
           {"anchor": "name", "offset": [x,y,z]}   -> object's point + offset
        """
        if isinstance(spec, str):
            return self.world_point(spec, frame)
        if isinstance(spec, dict):
            base = self.world_point(spec["anchor"], frame)
            return base + Vector(spec.get("offset", (0, 0, 0)))
        return Vector(spec)
