"""Audio helpers: ffmpeg conversion, WAV I/O and the final mix (voice + sfx + music)."""
from __future__ import annotations

import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np

from .config import load_settings, find_ffmpeg

SR = 48000


def ffmpeg() -> str:
    ff = find_ffmpeg(load_settings())
    if not ff:
        raise RuntimeError("ffmpeg not found. Install it (see docs/SETUP.md) or set FFMPEG_PATH.")
    return ff


def run_ffmpeg(args: list[str]) -> None:
    cmd = [ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", *map(str, args)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {' '.join(cmd)}\n{res.stderr}")


def to_wav(src: Path | str, dst: Path | str, sr: int = SR) -> Path:
    run_ffmpeg(["-i", src, "-ac", "1", "-ar", sr, "-c:a", "pcm_s16le", dst])
    return Path(dst)


def read_wav(path: Path | str) -> tuple[np.ndarray, int]:
    """Mono float32 in [-1, 1]. Non-16-bit files are converted with ffmpeg first."""
    path = Path(path)
    with wave.open(str(path), "rb") as w:
        sw, ch, sr, n = w.getsampwidth(), w.getnchannels(), w.getframerate(), w.getnframes()
        raw = w.readframes(n)
    if sw != 2:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td) / "conv.wav"
            to_wav(path, tmp, sr)
            return read_wav(tmp)
    data = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    if ch > 1:
        data = data.reshape(-1, ch).mean(axis=1)
    return data, sr


def write_wav(path: Path | str, data: np.ndarray, sr: int = SR) -> Path:
    data = np.clip(np.asarray(data, dtype=np.float32), -1.0, 1.0)
    pcm = (data * 32767.0).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    return Path(path)


def wav_duration(path: Path | str) -> float:
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / float(w.getframerate())


def _resample(data: np.ndarray, sr_from: int, sr_to: int) -> np.ndarray:
    if sr_from == sr_to or len(data) == 0:
        return data
    n = int(len(data) * sr_to / sr_from)
    return np.interp(np.linspace(0, len(data) - 1, n), np.arange(len(data)), data).astype(np.float32)


def _add(buf: np.ndarray, clip: np.ndarray, start_s: float, gain: float = 1.0) -> None:
    i = int(start_s * SR)
    if i >= len(buf) or len(clip) == 0:
        return
    if i < 0:
        clip, i = clip[-i:], 0
    j = min(len(buf), i + len(clip))
    buf[i:j] += clip[: j - i] * gain


def mix(ep: dict, timing: dict, voice: dict, out_path: Path, settings: dict) -> Path:
    """Build the full soundtrack WAV."""
    from . import sfx as sfx_mod
    from .episode import DEFAULT_VOICE_DELAY

    total = timing["total_frames"] / timing["fps"]
    buf = np.zeros(int(total * SR) + SR // 2, dtype=np.float32)
    tmap = {t["id"]: t for t in timing["shots"]}
    audio_cfg = {**settings.get("audio", {}), **ep.get("audio", {})}
    voice_gain = float(audio_cfg.get("voice_gain", 1.0))
    sfx_gain = float(audio_cfg.get("sfx_gain", 0.6))

    voice_spans = []
    for shot in ep["shots"]:
        v = voice.get(shot["id"])
        if not v:
            continue
        start = tmap[shot["id"]]["start"] + float(shot.get("voice_delay", DEFAULT_VOICE_DELAY))
        clip, sr = read_wav(v["path"])
        clip = _resample(clip, sr, SR)
        _add(buf, clip, start, voice_gain)
        voice_spans.append((start, start + len(clip) / SR))

    for shot in ep["shots"]:
        t0 = tmap[shot["id"]]["start"]
        for ev in shot.get("sfx", []):
            clip = sfx_mod.get(ev["name"])
            _add(buf, clip, t0 + float(ev.get("t", 0)), sfx_gain * float(ev.get("gain", 1.0)))

    music = ep.get("music") or {}
    if music.get("file"):
        mpath = Path(music["file"])
        if not mpath.is_absolute():
            from .config import ROOT
            mpath = ROOT / mpath
        with tempfile.TemporaryDirectory() as td:
            tmp = to_wav(mpath, Path(td) / "music.wav")
            mclip, _ = read_wav(tmp)
        reps = int(np.ceil(len(buf) / max(1, len(mclip))))
        mtrack = np.tile(mclip, reps)[: len(buf)]
        gain = np.full(len(buf), float(music.get("volume", 0.15)), dtype=np.float32)
        duck = float(music.get("duck", 0.45))
        ramp = int(0.2 * SR)
        for s, e in voice_spans:
            i, j = int(s * SR), int(e * SR)
            gain[i:j] *= duck
            # soft edges
            lo = max(0, i - ramp)
            gain[lo:i] *= np.linspace(1, duck, i - lo, dtype=np.float32)
            hi = min(len(buf), j + ramp)
            gain[j:hi] *= np.linspace(duck, 1, hi - j, dtype=np.float32)
        fade = int(1.5 * SR)
        gain[-fade:] *= np.linspace(1, 0, fade, dtype=np.float32)
        gain[: SR // 2] *= np.linspace(0, 1, SR // 2, dtype=np.float32)
        buf += mtrack * gain

    peak = float(np.max(np.abs(buf))) if len(buf) else 0.0
    if peak > 0.89:
        buf *= 0.89 / peak
    return write_wav(out_path, buf)
