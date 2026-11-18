"""Paths, settings and tool discovery (Blender, ffmpeg)."""
from __future__ import annotations

import glob
import json
import os
import platform
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EPISODES_DIR = ROOT / "episodes"
OUTPUT_DIR = ROOT / "output"
BLENDER_DIR = ROOT / "blender"
ASSETS_DIR = ROOT / "assets"
CONFIG_DIR = ROOT / "config"


def _load_dotenv() -> None:
    path = ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _deep_merge(a: dict, b: dict) -> dict:
    out = dict(a)
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_settings() -> dict:
    """config/settings.json, overridden by config/local.json (git-ignored) and .env."""
    _load_dotenv()
    settings = json.loads((CONFIG_DIR / "settings.json").read_text(encoding="utf-8"))
    local = CONFIG_DIR / "local.json"
    if local.exists():
        settings = _deep_merge(settings, json.loads(local.read_text(encoding="utf-8")))
    return settings


def _pick(paths: list[str], prefer: str | None) -> str | None:
    hits = sorted({p for pat in paths for p in glob.glob(pat)})
    if not hits:
        return None
    if prefer:
        pref = [h for h in hits if prefer in h]
        if pref:
            return pref[-1]
    return hits[-1]


def find_blender(settings: dict) -> str | None:
    explicit = os.environ.get("BLENDER_PATH") or settings.get("blender_path")
    if explicit:
        return explicit
    prefer = settings.get("blender_prefer_version", "4.5")
    system = platform.system()
    if system == "Windows":
        pats = [
            r"C:\Program Files\Blender Foundation\Blender*\blender.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Blender Foundation\Blender*\blender.exe"),
            r"C:\Program Files (x86)\Steam\steamapps\common\Blender\blender.exe",
        ]
    elif system == "Darwin":
        pats = ["/Applications/Blender*.app/Contents/MacOS/Blender",
                os.path.expanduser("~/Applications/Blender*.app/Contents/MacOS/Blender")]
    else:
        pats = ["/usr/bin/blender", "/snap/bin/blender", os.path.expanduser("~/blender*/blender")]
    return _pick(pats, prefer) or shutil.which("blender")


def find_ffmpeg(settings: dict) -> str | None:
    return os.environ.get("FFMPEG_PATH") or settings.get("ffmpeg_path") or shutil.which("ffmpeg")


def find_ffprobe(settings: dict) -> str | None:
    explicit = os.environ.get("FFPROBE_PATH") or settings.get("ffprobe_path")
    if explicit:
        return explicit
    ff = find_ffmpeg(settings)
    if ff:
        cand = Path(ff).with_name("ffprobe" + Path(ff).suffix)
        if cand.exists():
            return str(cand)
    return shutil.which("ffprobe")


def find_font(settings: dict) -> str | None:
    if settings.get("font") and Path(settings["font"]).exists():
        return settings["font"]
    bundled = sorted(glob.glob(str(ASSETS_DIR / "fonts" / "*.[ot]tf")))
    if bundled:
        return bundled[0]
    candidates = [
        r"C:\Windows\Fonts\arialbd.ttf", r"C:\Windows\Fonts\segoeuib.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for c in candidates:
        if Path(c).exists():
            return c
    return None
