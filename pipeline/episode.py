"""Load / validate episode JSON and compute the shot timeline."""
from __future__ import annotations

import json
from pathlib import Path

from .config import BLENDER_DIR, EPISODES_DIR, OUTPUT_DIR

OVERLAY_TYPES = {"title", "caption", "label", "counter", "card", "flash", "image"}
DEFAULT_VOICE_DELAY = 0.15
DEFAULT_VOICE_PAD = 0.35


class EpisodeError(ValueError):
    pass


def resolve(ref: str) -> Path:
    p = Path(ref)
    if p.suffix == ".json" and p.exists():
        return p.resolve()
    cand = EPISODES_DIR / f"{ref}.json"
    if cand.exists():
        return cand
    raise EpisodeError(f"Episode '{ref}' not found (looked for {p} and {cand})")


def load(ref: str) -> dict:
    path = resolve(ref)
    try:
        ep = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise EpisodeError(f"{path}: invalid JSON: {e}") from None
    validate(ep, path)
    ep["_path"] = str(path)
    return ep


def validate(ep: dict, path: Path | str = "<episode>") -> None:
    errs = []
    for k in ("id", "scene", "shots"):
        if k not in ep:
            errs.append(f"missing '{k}'")
    if errs:
        raise EpisodeError(f"{path}: " + "; ".join(errs))
    if not (BLENDER_DIR / "scenes" / f"{ep['scene']}.py").exists():
        errs.append(f"scene module blender/scenes/{ep['scene']}.py does not exist")
    if not ep["shots"]:
        errs.append("no shots")
    seen = set()
    for i, s in enumerate(ep["shots"]):
        where = f"shot[{i}]({s.get('id', '?')})"
        if "id" not in s:
            errs.append(f"{where}: missing id")
        elif s["id"] in seen:
            errs.append(f"{where}: duplicate id")
        seen.add(s.get("id"))
        try:
            if float(s.get("duration", 0)) <= 0:
                errs.append(f"{where}: duration must be > 0")
        except (TypeError, ValueError):
            errs.append(f"{where}: duration must be a number")
        if i == 0 and "orbit" not in (s.get("camera") or {}) and not (s.get("camera") or {}).get("from"):
            errs.append(f"{where}: first shot needs camera.from or camera.orbit")
        for j, ov in enumerate(s.get("overlays", [])):
            t = ov.get("type")
            if t not in OVERLAY_TYPES:
                errs.append(f"{where}.overlays[{j}]: unknown type '{t}' (use {sorted(OVERLAY_TYPES)})")
            if t == "label" and not ov.get("anchor") and not ov.get("pos"):
                errs.append(f"{where}.overlays[{j}]: label needs 'anchor' (3D object) or 'pos'")
        for j, ev in enumerate(s.get("events", [])):
            if "action" not in ev:
                errs.append(f"{where}.events[{j}]: missing 'action'")
    if errs:
        raise EpisodeError(f"{path}:\n  - " + "\n  - ".join(errs))


def out_dir(ep: dict) -> Path:
    d = OUTPUT_DIR / ep["id"]
    d.mkdir(parents=True, exist_ok=True)
    return d


def compute_timing(ep: dict, voice: dict | None = None) -> dict:
    """Shot start/end in seconds and 1-based inclusive frames.

    A shot is stretched if its narration audio (plus delay + pad) is longer than
    its declared duration, so the voice never gets cut off.
    """
    fps = int(ep.get("fps", 30))
    voice = voice or {}
    t = 0.0
    shots = []
    for s in ep["shots"]:
        d = float(s["duration"])
        v = voice.get(s["id"])
        if v and v.get("duration"):
            need = (float(s.get("voice_delay", DEFAULT_VOICE_DELAY)) + v["duration"]
                    + float(s.get("voice_pad", DEFAULT_VOICE_PAD)))
            d = max(d, need)
        start_frame = int(round(t * fps)) + 1
        end = t + d
        end_frame = max(start_frame, int(round(end * fps)))
        shots.append({"id": s["id"], "start": round(t, 4), "end": round(end, 4),
                      "duration": round(d, 4), "start_frame": start_frame, "end_frame": end_frame})
        t = end
    total = shots[-1]["end_frame"]
    return {"fps": fps, "total_frames": total, "duration": round(total / fps, 4), "shots": shots}


def write_timing(ep: dict, voice: dict | None = None) -> tuple[Path, dict]:
    timing = compute_timing(ep, voice)
    path = out_dir(ep) / "timing.json"
    path.write_text(json.dumps(timing, indent=2), encoding="utf-8")
    return path, timing


def read_timing(ep: dict) -> dict:
    path = out_dir(ep) / "timing.json"
    if not path.exists():
        raise EpisodeError(f"{path} missing - run the voice/preview/render step first")
    return json.loads(path.read_text(encoding="utf-8"))
