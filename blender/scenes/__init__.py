"""Scene modules.

An episode's "scene" field names a module in this package (e.g. "traffic_camera"
-> blender/scenes/traffic_camera.py). A scene module must define:

    def build(ctx):          # create all objects, register names used by the episode
        ...

and may define:

    ACTIONS = {"name": fn}   # extra timeline actions, fn(ctx, f0, f1, params)
    LIGHTING = {...}         # overrides for lib.render.lighting()

Reusable sets (street.py, ...) expose their own build(ctx, ...) so episode
scenes can stack on top of them. See docs/SCENES.md.
"""
