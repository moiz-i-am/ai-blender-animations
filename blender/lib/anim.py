"""Keyframe helpers."""
from contextlib import contextmanager

import bpy

EASE = {
    "linear": "LINEAR",
    "ease": "BEZIER",
    "ease_in_out": "BEZIER",
    "smooth": "BEZIER",
    "constant": "CONSTANT",
    "step": "CONSTANT",
}


def ease_mode(name):
    try:
        return EASE[name or "ease_in_out"]
    except KeyError:
        raise KeyError(f"Unknown ease '{name}'. Use one of {sorted(EASE)}")


@contextmanager
def interpolation(kind="BEZIER"):
    """New keyframes inserted inside this block use `kind` interpolation."""
    prefs = bpy.context.preferences.edit
    old = prefs.keyframe_new_interpolation_type
    prefs.keyframe_new_interpolation_type = kind
    try:
        yield
    finally:
        prefs.keyframe_new_interpolation_type = old


def key(target, path, frame, value=None, interp="BEZIER", index=-1):
    """Set target.<path> = value (if given) and insert a keyframe at `frame`."""
    if value is not None:
        setattr(target, path, value)
    with interpolation(interp):
        target.keyframe_insert(data_path=path, frame=frame, index=index)
