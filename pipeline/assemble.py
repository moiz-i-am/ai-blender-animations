"""Composite frames + overlays, mix audio and encode the final MP4 with ffmpeg."""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

from PIL import Image

from . import audio, captions, voice
from .episode import out_dir, read_timing
from .overlays import Compositor, contact_sheet


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def make_compositor(ep, settings, timing, tracking):
    vc = voice.load_cached(ep)
    caps = captions.build(ep, timing, vc, settings)
    return Compositor(ep, timing, settings, tracking=tracking, captions=caps)


def composite_preview(ep: dict, settings: dict) -> list[Path]:
    """Turn Blender's raw preview stills into final-look stills + a contact sheet."""
    od = out_dir(ep)
    pdir = od / "preview"
    index = _load_json(pdir / "index.json")
    if not index:
        raise RuntimeError(f"{pdir / 'index.json'} missing - Blender preview did not run")
    timing = read_timing(ep)
    comp = make_compositor(ep, settings, timing, _load_json(pdir / "tracking.json"))
    outs = []
    for i, fr in enumerate(index["frames"]):
        raw = Image.open(fr["raw"])
        img = comp.render(fr["frame"], raw)
        p = pdir / f"final_{i:02d}_{fr['shot']}.png"
        img.save(p)
        outs.append(p)
    sheet = contact_sheet(outs, pdir / "contact_sheet.png")
    print(f"  preview stills: {pdir}")
    print(f"  contact sheet:  {sheet}")
    return outs


def placeholder_preview(ep: dict, settings: dict, n: int = 4) -> list[Path]:
    """Overlay-only stills (no Blender) to check captions, titles and timing."""
    od = out_dir(ep)
    pdir = od / "preview"
    pdir.mkdir(exist_ok=True)
    timing = read_timing(ep)
    comp = make_compositor(ep, settings, timing, None)
    shots = timing["shots"]
    if n < len(shots):
        step = (len(shots) - 1) / max(1, n - 1)
        shots = [shots[round(i * step)] for i in range(n)]
    outs = []
    for i, s in enumerate(shots):
        f = (s["start_frame"] + s["end_frame"]) // 2
        p = pdir / f"placeholder_{i:02d}_{s['id']}.png"
        comp.render(f).save(p)
        outs.append(p)
    contact_sheet(outs, pdir / "contact_sheet.png")
    print(f"  placeholder stills: {pdir}")
    return outs


def assemble(ep: dict, settings: dict, placeholder: bool = False, draft: bool = False) -> Path:
    od = out_dir(ep)
    timing = read_timing(ep)
    frames_dir = od / "frames"
    stamp = _load_json(frames_dir / ".timing.json")
    if not placeholder:
        if not frames_dir.exists() or not any(frames_dir.glob("frame_*.png")):
            raise RuntimeError("No rendered frames. Run `render` first, or use --placeholder.")
        if stamp and stamp.get("total_frames") != timing["total_frames"]:
            print("  WARNING: frames were rendered with a different timeline - re-render for a correct video")

    tracking = None if placeholder else _load_json(od / "tracking.json")
    comp = make_compositor(ep, settings, timing, tracking)
    vc = voice.load_cached(ep)

    print("  mixing audio ...")
    mix_path = audio.mix(ep, timing, vc, od / "audio_mix.wav", settings)

    W, H, fps = comp.W, comp.H, timing["fps"]
    suffix = "_draft" if draft else ""
    out_path = od / f"{ep['id']}{suffix}.mp4"
    enc = settings.get("encode", {})
    cmd = [audio.ffmpeg(), "-hide_banner", "-loglevel", "error", "-y",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
           "-i", str(mix_path), "-map", "0:v", "-map", "1:a",
           "-c:v", "libx264", "-preset", "veryfast" if draft else enc.get("preset", "medium"),
           "-crf", "24" if draft else str(enc.get("crf", 18)), "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", str(out_path)]
    print(f"  encoding {timing['total_frames']} frames -> {out_path}")
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    assert proc.stdin is not None
    last, missing, t0 = None, 0, time.time()
    try:
        for f in range(1, timing["total_frames"] + 1):
            img = None
            if not placeholder:
                src = frames_dir / f"frame_{f:04d}.png"
                if src.exists():
                    try:
                        img = Image.open(src)
                        img.load()
                        last = img
                    except OSError:
                        img = last
                        missing += 1
                else:
                    img = last
                    missing += 1
            proc.stdin.write(comp.render(f, img).tobytes())
            if f % 60 == 0:
                print(f"  ... {f}/{timing['total_frames']} ({time.time() - t0:.0f}s)", flush=True)
    finally:
        proc.stdin.close()
        rc = proc.wait()
    if rc != 0:
        raise RuntimeError(f"ffmpeg encode failed (exit {rc})")
    if missing:
        print(f"  WARNING: {missing} frames were missing/unreadable and were filled with the previous frame")
    print(f"  done: {out_path}")
    return out_path
