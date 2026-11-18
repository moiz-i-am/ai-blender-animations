"""Narration: one audio clip per shot.

Backends (episode "voice.backend", or --backend on the CLI):
  none        no voice; shots keep their declared durations
  system      OS voice (macOS `say`, Windows SAPI) - free, robotic, good for testing timing
  kokoro      Kokoro TTS, free & local (pip install -r requirements-voice.txt)
  elevenlabs  ElevenLabs API, paid, best quality (ELEVENLABS_API_KEY in .env)

Clips are cached by text+voice, so re-running only regenerates changed lines.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import tempfile
from pathlib import Path

from . import audio
from .episode import out_dir

BACKENDS = ("none", "system", "kokoro", "elevenlabs")


def _cfg(ep: dict, settings: dict, backend: str | None) -> dict:
    cfg = {**settings.get("voice", {}), **ep.get("voice", {})}
    if backend:
        cfg["backend"] = backend
    cfg.setdefault("backend", "none")
    if cfg["backend"] not in BACKENDS:
        raise ValueError(f"Unknown voice backend '{cfg['backend']}'. Use one of {BACKENDS}")
    return cfg


def run(ep: dict, settings: dict, backend: str | None = None, force: bool = False) -> dict:
    cfg = _cfg(ep, settings, backend)
    vdir = out_dir(ep) / "voice"
    vdir.mkdir(exist_ok=True)
    result: dict = {}
    if cfg["backend"] != "none":
        for shot in ep["shots"]:
            text = (shot.get("narration") or "").strip()
            if not text:
                continue
            voice_name = cfg.get(f"{cfg['backend']}_voice") or cfg.get("voice")
            sig = json.dumps([cfg["backend"], voice_name, cfg.get("speed", 1.0), text])
            key = hashlib.sha1(sig.encode()).hexdigest()[:10]
            wav = vdir / f"{shot['id']}_{key}.wav"
            if force or not wav.exists():
                print(f"  voice [{cfg['backend']}] {shot['id']}: {text[:60]}")
                _synth(cfg["backend"], text, wav, cfg, voice_name)
            result[shot["id"]] = {"path": str(wav), "duration": round(audio.wav_duration(wav), 3),
                                  "text": text}
    (out_dir(ep) / "voice.json").write_text(
        json.dumps({"backend": cfg["backend"], "shots": result}, indent=2), encoding="utf-8")
    return result


def load_cached(ep: dict) -> dict:
    p = out_dir(ep) / "voice.json"
    if not p.exists():
        return {}
    shots = json.loads(p.read_text(encoding="utf-8")).get("shots", {})
    return {k: v for k, v in shots.items() if Path(v["path"]).exists()}


def _synth(backend: str, text: str, wav: Path, cfg: dict, voice_name: str | None) -> None:
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        if backend == "system":
            raw = _system(text, td, voice_name, float(cfg.get("speed", 1.0)))
        elif backend == "kokoro":
            raw = _kokoro(text, td, voice_name or "am_michael", float(cfg.get("speed", 1.0)))
        elif backend == "elevenlabs":
            raw = _elevenlabs(text, td, voice_name, cfg)
        else:
            raise ValueError(backend)
        audio.to_wav(raw, wav)


def _system(text: str, td: Path, voice_name: str | None, speed: float) -> Path:
    system = platform.system()
    if system == "Darwin":
        out = td / "say.aiff"
        cmd = ["say", "-o", str(out), "-r", str(int(180 * speed))]
        if voice_name:
            cmd += ["-v", voice_name]
        subprocess.run(cmd + [text], check=True)
        return out
    if system == "Windows":
        out = td / "sapi.wav"
        safe = text.replace("'", "''")
        rate = max(-10, min(10, int(round((speed - 1.0) * 10))))
        ps = ("Add-Type -AssemblyName System.Speech; "
              "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
              f"$s.Rate = {rate}; "
              + (f"$s.SelectVoice('{voice_name}'); " if voice_name else "")
              + f"$s.SetOutputToWaveFile('{out}'); $s.Speak('{safe}'); $s.Dispose()")
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True)
        return out
    out = td / "espeak.wav"
    subprocess.run(["espeak-ng", "-w", str(out), text], check=True)
    return out


_KOKORO = {}


def _kokoro(text: str, td: Path, voice_name: str, speed: float) -> Path:
    try:
        import numpy as np
        from kokoro import KPipeline
    except ImportError:
        raise RuntimeError("Kokoro not installed: pip install -r requirements-voice.txt") from None
    lang = voice_name[0]          # 'a' = American, 'b' = British, ...
    if lang not in _KOKORO:
        _KOKORO[lang] = KPipeline(lang_code=lang)
    chunks = []
    for _, _, a in _KOKORO[lang](text, voice=voice_name, speed=speed):
        chunks.append(a.numpy() if hasattr(a, "numpy") else np.asarray(a))
    data = np.concatenate(chunks) if chunks else np.zeros(1, dtype=np.float32)
    out = td / "kokoro.wav"
    audio.write_wav(out, data, sr=24000)
    return out


def _elevenlabs(text: str, td: Path, voice_id: str | None, cfg: dict) -> Path:
    import requests
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        raise RuntimeError("ELEVENLABS_API_KEY not set (put it in .env)")
    if not voice_id:
        raise RuntimeError("Set voice.elevenlabs_voice (a voice ID) in the episode or config/local.json")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=mp3_44100_128"
    body = {"text": text, "model_id": cfg.get("elevenlabs_model", "eleven_multilingual_v2")}
    if cfg.get("elevenlabs_settings"):
        body["voice_settings"] = cfg["elevenlabs_settings"]
    r = requests.post(url, json=body, headers={"xi-api-key": key, "accept": "audio/mpeg"}, timeout=120)
    if r.status_code != 200:
        raise RuntimeError(f"ElevenLabs error {r.status_code}: {r.text[:300]}")
    out = td / "el.mp3"
    out.write_bytes(r.content)
    return out
