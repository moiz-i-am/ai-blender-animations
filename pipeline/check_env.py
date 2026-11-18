"""`python make_episode.py check` - verify everything the pipeline needs is installed."""
from __future__ import annotations

import importlib
import os
import re
import shutil
import subprocess
import sys

from .config import find_blender, find_ffmpeg, find_ffprobe, find_font, load_settings

OK, WARN, BAD = "OK  ", "WARN", "FAIL"


def _line(status, name, detail=""):
    print(f"  [{status}] {name:<22} {detail}")


def _version(cmd):
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return (out.stdout or out.stderr).strip().splitlines()[0]
    except Exception as e:  # noqa: BLE001
        return f"error: {e}"


def main() -> int:
    settings = load_settings()
    failures = 0
    print("\nshorts3d environment check\n")

    v = sys.version_info
    if v >= (3, 10):
        _line(OK, "python", sys.version.split()[0] + ("" if v < (3, 13) else "  (kokoro needs 3.10-3.12)"))
    else:
        _line(BAD, "python", f"{sys.version.split()[0]} - need 3.10+ (3.11 recommended)")
        failures += 1

    for mod, required, why in (("numpy", True, "audio + images"),
                               ("PIL", True, "overlays (pip install Pillow)"),
                               ("requests", False, "ElevenLabs voice"),
                               ("kokoro", False, "free local voice (requirements-voice.txt)"),
                               ("faster_whisper", False, "word-accurate caption timing")):
        try:
            m = importlib.import_module(mod)
            _line(OK, mod, getattr(m, "__version__", ""))
        except Exception:  # noqa: BLE001
            _line(BAD if required else WARN, mod, ("MISSING - " if required else "optional - ") + why)
            failures += required

    ff = find_ffmpeg(settings)
    if ff:
        _line(OK, "ffmpeg", _version([ff, "-version"])[:70])
    else:
        _line(BAD, "ffmpeg", "not found - install it or set ffmpeg_path in config/local.json")
        failures += 1
    fp = find_ffprobe(settings)
    _line(OK if fp else WARN, "ffprobe", fp or "not found (optional)")

    bl = find_blender(settings)
    if bl and (os.path.exists(bl) or shutil.which(bl)):
        ver = _version([bl, "-b", "--factory-startup", "--version"]) if "python" not in os.path.basename(bl).lower() \
            else _version([bl, "-c", "import bpy;print('bpy', bpy.app.version_string)"])
        m = re.search(r"(\d+)\.(\d+)", ver)
        status = OK if m and (int(m.group(1)), int(m.group(2))) >= (4, 2) else WARN
        _line(status, "blender", f"{ver}  [{bl}]" + ("" if status == OK else "  (4.5 LTS recommended)"))
    else:
        _line(BAD, "blender", f"not found ({bl or 'no path'}) - install Blender 4.5 LTS or set blender_path")
        failures += 1

    font = find_font(settings)
    _line(OK if font else WARN, "font", font or "none found - captions will use Pillow's basic font")

    _line(OK if os.environ.get("ELEVENLABS_API_KEY") else WARN, "ELEVENLABS_API_KEY",
          "set" if os.environ.get("ELEVENLABS_API_KEY") else "not set (only needed for ElevenLabs voice)")
    uvx = shutil.which("uvx")
    _line(OK if uvx else WARN, "uvx (Blender MCP)", uvx or "not found - only needed for Blender MCP (docs/BLENDER_MCP.md)")

    print()
    if failures:
        print(f"  {failures} required item(s) missing. See docs/SETUP.md.\n")
        return 1
    print("  All required tools found. Next: python make_episode.py preview traffic_camera\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
