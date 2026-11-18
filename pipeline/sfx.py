"""Synthesised sound effects (no licensing worries).

Drop a WAV called assets/sfx/<name>.wav to override any of these with a real sound.
Available names: click, shutter, whoosh, beep, pop, ding, tick, alarm
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np

from .config import ASSETS_DIR

SR = 48000
_rng = np.random.default_rng(1234)


def _t(sec: float) -> np.ndarray:
    return np.arange(int(sec * SR)) / SR


def _fade(x: np.ndarray, a: float = 0.004, r: float = 0.02) -> np.ndarray:
    n = len(x)
    ai, ri = min(n, int(a * SR)), min(n, int(r * SR))
    env = np.ones(n, dtype=np.float32)
    if ai:
        env[:ai] = np.linspace(0, 1, ai)
    if ri:
        env[-ri:] *= np.linspace(1, 0, ri)
    return (x * env).astype(np.float32)


def _lowpass(x: np.ndarray, k: int) -> np.ndarray:
    return np.convolve(x, np.ones(k) / k, mode="same")


def shutter() -> np.ndarray:
    def burst(sec, decay):
        t = _t(sec)
        return _rng.uniform(-1, 1, len(t)) * np.exp(-t * decay)
    a = burst(0.05, 90)
    b = burst(0.06, 70) * 0.8
    gap = np.zeros(int(0.07 * SR))
    return _fade(np.concatenate([a, gap, b]) * 0.8)


def whoosh() -> np.ndarray:
    t = _t(0.7)
    noise = _lowpass(_rng.uniform(-1, 1, len(t)), 24)
    env = np.sin(np.pi * t / t[-1]) ** 2
    return _fade(noise * env * 2.2)


def beep() -> np.ndarray:
    t = _t(0.14)
    return _fade(np.sin(2 * np.pi * 1200 * t) * 0.5)


def pop() -> np.ndarray:
    t = _t(0.09)
    f = np.linspace(900, 220, len(t))
    return _fade(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 25) * 0.8)


def ding() -> np.ndarray:
    t = _t(0.8)
    s = np.sin(2 * np.pi * 1480 * t) + 0.5 * np.sin(2 * np.pi * 2220 * t)
    return _fade(s * np.exp(-t * 5) * 0.4, r=0.05)


def tick() -> np.ndarray:
    t = _t(0.012)
    return _fade(_rng.uniform(-1, 1, len(t)) * np.exp(-t * 400) * 0.7, a=0.0005, r=0.004)


def alarm() -> np.ndarray:
    t = _t(0.6)
    f = np.where((t * 6).astype(int) % 2 == 0, 880, 660)
    return _fade(np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * 0.18)


SOUNDS = {"click": shutter, "shutter": shutter, "whoosh": whoosh, "beep": beep,
          "pop": pop, "ding": ding, "tick": tick, "alarm": alarm}


@lru_cache(maxsize=None)
def get(name: str) -> np.ndarray:
    override = ASSETS_DIR / "sfx" / f"{name}.wav"
    if override.exists():
        from .audio import read_wav, _resample
        data, sr = read_wav(override)
        return _resample(data, sr, SR)
    if name not in SOUNDS:
        raise KeyError(f"Unknown sfx '{name}'. Built-in: {sorted(SOUNDS)} (or add assets/sfx/{name}.wav)")
    return SOUNDS[name]().astype(np.float32)
