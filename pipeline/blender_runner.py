"""Run blender/build_scene.py headless."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from .config import BLENDER_DIR, ROOT, find_blender
from .episode import out_dir

_SHOW = ("[shorts3d]", "Error", "ERROR", "Traceback", "File \"", "Exception", "Warning: ", "Saved:")


def run(ep: dict, settings: dict, mode: str, engine: str | None = None, scale: int | None = None,
        frames: str | None = None, resume: bool = False, preview_shots: str | None = None,
        save_blend: bool = False, verbose: bool = False) -> None:
    exe = find_blender(settings)
    if not exe:
        raise RuntimeError("Blender not found. Install Blender 4.5 LTS or set blender_path in "
                           "config/local.json (see docs/SETUP.md).")
    od = out_dir(ep)
    (od / "logs").mkdir(exist_ok=True)
    script = BLENDER_DIR / "build_scene.py"
    args = ["--episode", ep["_path"], "--timing", str(od / "timing.json"), "--out", str(od),
            "--mode", mode, "--engine", engine or settings.get("engine", "eevee")]
    if scale:
        args += ["--scale", str(scale)]
    if frames:
        args += ["--frames", frames]
    if resume:
        args.append("--resume")
    if preview_shots:
        args += ["--preview-shots", str(preview_shots)]
    if save_blend:
        args.append("--save-blend")

    if Path(exe).name.lower().startswith("python"):
        # a Python interpreter with the `bpy` module installed (pip install bpy)
        cmd = [exe, str(script), "--", *args]
    else:
        cmd = [exe, "-b", "--factory-startup", "-noaudio", "--python-exit-code", "1",
               "-P", str(script), "--", *args]

    log_path = od / "logs" / f"blender_{mode}.log"
    print(f"  blender: {exe}")
    print(f"  log:     {log_path}")
    frame_count = 0
    with open(log_path, "w", encoding="utf-8") as log:
        log.write(" ".join(cmd) + "\n\n")
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=str(ROOT),
                                text=True, encoding="utf-8", errors="replace")
        assert proc.stdout is not None
        for line in proc.stdout:
            log.write(line)
            if verbose or any(s in line for s in _SHOW):
                if line.startswith("Saved:") and mode == "full":
                    frame_count += 1
                    if frame_count % 30 == 0:
                        print(f"  ... {frame_count} frames saved", flush=True)
                    continue
                sys.stdout.write("  " + line)
                sys.stdout.flush()
        rc = proc.wait()
    if rc != 0:
        raise RuntimeError(f"Blender exited with code {rc}. Full log: {log_path}")
