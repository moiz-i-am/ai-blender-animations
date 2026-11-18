"""Turn narration into short, timed caption chunks.

Timing comes from (best first):
  1. faster-whisper word timestamps on the voice clip (captions.word_timing = true and
     faster-whisper installed) - mapped back onto the script words, so spelling is always right
  2. proportional timing across the voice clip (or the shot, when there is no voice)

Wrap words in *asterisks* in the narration/caption to highlight them.
"""
from __future__ import annotations

import re

from .episode import DEFAULT_VOICE_DELAY

_PUNCT_BREAK = re.compile(r"[.,!?;:—]$")
_WHISPER = {}


def _chunk(words: list[str], max_words: int) -> list[list[int]]:
    """Group word indices into chunks of <= max_words, breaking after punctuation."""
    chunks, cur = [], []
    for i, w in enumerate(words):
        cur.append(i)
        if len(cur) >= max_words or _PUNCT_BREAK.search(w.strip("*")):
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    return chunks


def _whisper_words(path: str, n_words: int, model_size: str, language: str):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return None
    if model_size not in _WHISPER:
        _WHISPER[model_size] = WhisperModel(model_size, device="auto")
    segments, _ = _WHISPER[model_size].transcribe(path, word_timestamps=True, language=language)
    ws = [(w.start, w.end) for seg in segments for w in (seg.words or [])]
    if not ws or abs(len(ws) - n_words) > max(2, 0.25 * n_words):
        return None
    if len(ws) == n_words:
        return ws
    # map script word i -> nearest whisper word by relative position
    return [ws[round(i * (len(ws) - 1) / max(1, n_words - 1))] for i in range(n_words)]


def build(ep: dict, timing: dict, voice: dict, settings: dict) -> list[dict]:
    cfg = {**settings.get("captions", {}), **ep.get("captions", {})}
    if cfg.get("enabled", True) is False:
        return []
    max_words = int(cfg.get("max_words", 4))
    tmap = {t["id"]: t for t in timing["shots"]}
    caps: list[dict] = []
    for shot in ep["shots"]:
        if shot.get("captions") is False:
            continue
        text = shot.get("caption") or shot.get("narration") or ""
        words = text.split()
        if not words:
            continue
        t = tmap[shot["id"]]
        v = voice.get(shot["id"])
        if v:
            s0 = t["start"] + float(shot.get("voice_delay", DEFAULT_VOICE_DELAY))
            s1 = s0 + v["duration"]
        else:
            s0, s1 = t["start"] + 0.15, t["end"] - 0.2
        stamps = None
        if v and cfg.get("word_timing", False) and not shot.get("caption"):
            stamps = _whisper_words(v["path"], len(words), cfg.get("whisper_model", "small"),
                                    ep.get("language", "en"))
        chunks = _chunk(words, max_words)
        if stamps:
            spans = [(s0 + stamps[c[0]][0], s0 + stamps[c[-1]][1]) for c in chunks]
        else:
            weights = [sum(len(words[i]) + 1 for i in c) for c in chunks]
            total = float(sum(weights))
            spans, acc = [], s0
            for w in weights:
                d = (s1 - s0) * w / total
                spans.append((acc, acc + d))
                acc += d
        for k, (c, (a, b)) in enumerate(zip(chunks, spans)):
            nxt = spans[k + 1][0] if k + 1 < len(spans) else t["end"]
            caps.append({"type": "caption", "text": " ".join(words[i] for i in c),
                         "start": round(a, 3), "end": round(min(max(b, a + 0.25), nxt, t["end"]), 3)})
    return caps
