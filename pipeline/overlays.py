"""2D compositor: sky background + rendered 3D frame + animated overlays.

Overlay types (in a shot's "overlays" list; start/end are seconds relative to the shot,
end defaults to the end of the shot; pos = [x, y] as 0-1 fractions of the frame):

  title    {"text", "pos"?, "upper"?: true, "box"?: false}
  label    {"text", "anchor": "<3D object name>", "offset"?: [dx, dy]}   follows the object
  counter  {"from", "to", "suffix"?, "decimals"?, "sub"?, "alert_above"?, "count_time"?, "pos"?}
  card     {"title"?, "items": [..], "stagger"?: 0.45, "pos"?}
  flash    {"duration"?: 0.35}                                          white screen flash
  image    {"file", "width"?: 0.3, "pos"?}
  caption  generated automatically from narration (see captions.py)

Use *asterisks* around words in titles/captions to highlight them.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .config import ROOT, find_font

DEFAULT_STYLE = {
    "sky_top": "#8FD0F0",
    "sky_bottom": "#F7F0DC",
    "text_color": "#FFFFFF",
    "highlight_color": "#FFD23F",
    "stroke_color": "#111111",
    "accent": "#FF4D4D",
    "caption_y": 0.70,
    "caption_size": 0.050,
    "title_y": 0.17,
    "title_size": 0.064,
    "label_size": 0.027,
    "label_bg": "#111111",
    "label_fg": "#FFFFFF",
    "counter_size": 0.075,
    "card_bg": "#FFFFFF",
    "card_fg": "#1A1A1A",
    "handle": "",
}

Z_ORDER = ["label", "image", "counter", "card", "flash", "title", "caption"]


def _hex(c, a=1.0):
    if isinstance(c, (list, tuple)):
        r, g, b = c[:3]
    else:
        c = c.lstrip("#")
        r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
    return (int(r), int(g), int(b), int(round(255 * max(0.0, min(1.0, a)))))


def _clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def ease_out_back(x):
    c1, c3 = 1.70158, 2.70158
    x = _clamp(x)
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def ease_out_cubic(x):
    return 1 - (1 - _clamp(x)) ** 3


def _parse_rich(text, upper):
    out = []
    for w in text.split():
        hl = w.startswith("*") or w.endswith("*") or w.endswith("*,") or w.endswith("*.")
        clean = w.replace("*", "")
        out.append((clean.upper() if upper else clean, hl))
    return out


class Compositor:
    def __init__(self, ep, timing, settings, tracking=None, captions=()):
        self.W, self.H = [int(v) for v in ep.get("resolution", [1080, 1920])]
        self.fps = int(timing["fps"])
        self.st = {**DEFAULT_STYLE, **settings.get("style", {}), **ep.get("style", {})}
        self.font_path = find_font(settings)
        self._fonts = {}
        self._images = {}
        self._warned = set()
        self.tracking = tracking
        self._tidx = {f: i for i, f in enumerate(tracking["frames"])} if tracking else {}

        tmap = {t["id"]: t for t in timing["shots"]}
        self.items = []
        for shot in ep["shots"]:
            t = tmap[shot["id"]]
            for ov in shot.get("overlays", []):
                it = dict(ov)
                it["start"] = t["start"] + float(ov.get("start", 0))
                if ov.get("type") == "flash":
                    it["end"] = it["start"] + float(ov.get("duration", 0.35))
                elif "end" in ov:
                    it["end"] = t["start"] + float(ov["end"])
                else:
                    it["end"] = t["end"]
                self.items.append(it)
        self.items += list(captions)
        self.items.sort(key=lambda i: Z_ORDER.index(i["type"]) if i["type"] in Z_ORDER else 0)
        self.bg = self._sky()

    # ---- resources ----------------------------------------------------
    def font(self, size):
        size = max(8, int(size))
        if size not in self._fonts:
            if self.font_path:
                self._fonts[size] = ImageFont.truetype(self.font_path, size)
            else:
                try:
                    self._fonts[size] = ImageFont.load_default(size=size)
                except TypeError:
                    self._fonts[size] = ImageFont.load_default()
        return self._fonts[size]

    def _sky(self):
        top = np.array(_hex(self.st["sky_top"])[:3], dtype=np.float32)
        bot = np.array(_hex(self.st["sky_bottom"])[:3], dtype=np.float32)
        ramp = np.linspace(0, 1, self.H, dtype=np.float32)[:, None]
        col = top * (1 - ramp) + bot * ramp
        arr = np.repeat(col[:, None, :], self.W, axis=1).astype(np.uint8)
        return Image.fromarray(arr, "RGB").convert("RGBA")

    def _warn(self, msg):
        if msg not in self._warned:
            self._warned.add(msg)
            print("  [overlay warning]", msg)

    # ---- main ---------------------------------------------------------
    def render(self, frame_no, rgba=None):
        t = (frame_no - 1) / self.fps
        base = self.bg.copy()
        if rgba is not None:
            if rgba.size != (self.W, self.H):
                rgba = rgba.resize((self.W, self.H), Image.LANCZOS)
            base.alpha_composite(rgba.convert("RGBA"))
        layer = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        for it in self.items:
            if it["start"] <= t < it["end"]:
                fn = getattr(self, "_draw_" + it["type"], None)
                if fn is None:
                    self._warn(f"unknown overlay type {it['type']}")
                    continue
                if it["type"] == "flash":
                    base.alpha_composite(layer)
                    layer = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
                    d = ImageDraw.Draw(layer)
                    self._draw_flash(base, it, t)
                else:
                    fn(layer, d, it, t, frame_no)
        if self.st.get("handle"):
            f = self.font(self.H * 0.022)
            d.text((self.W * 0.05, self.H * 0.045), self.st["handle"], font=f,
                   fill=_hex("#FFFFFF", 0.85), stroke_width=3, stroke_fill=_hex("#000000", 0.6))
        base.alpha_composite(layer)
        return base.convert("RGB")

    # ---- helpers ------------------------------------------------------
    def _alpha(self, it, t, fin=0.18, fout=0.18):
        a = _clamp((t - it["start"]) / fin) if fin else 1.0
        b = _clamp((it["end"] - t) / fout) if fout else 1.0
        return min(a, b)

    def _layout(self, d, words, font, max_w):
        lines, cur = [], []
        space = d.textlength(" ", font=font)
        for w in words:
            trial = cur + [w]
            width = sum(d.textlength(x[0], font=font) for x in trial) + space * (len(trial) - 1)
            if cur and width > max_w:
                lines.append(cur)
                cur = [w]
            else:
                cur = trial
        if cur:
            lines.append(cur)
        return lines

    def _draw_rich(self, d, text, size, cx, cy, alpha, upper=True, max_w=None,
                   color=None, stroke_ratio=0.11, hl_color=None):
        font = self.font(size)
        words = _parse_rich(text, upper)
        lines = self._layout(d, words, font, max_w or self.W * 0.86)
        space = d.textlength(" ", font=font)
        lh = size * 1.12
        top = cy - lh * len(lines) / 2
        fill = _hex(color or self.st["text_color"], alpha)
        hl = _hex(hl_color or self.st["highlight_color"], alpha)
        stroke = _hex(self.st["stroke_color"], alpha)
        sw = max(2, int(size * stroke_ratio)) if stroke_ratio > 0 else 0
        for li, line in enumerate(lines):
            widths = [d.textlength(w, font=font) for w, _ in line]
            x = cx - (sum(widths) + space * (len(line) - 1)) / 2
            y = top + lh * (li + 0.5)
            for (w, is_hl), wd in zip(line, widths):
                d.text((x, y), w, font=font, fill=hl if is_hl else fill, anchor="lm",
                       stroke_width=sw, stroke_fill=stroke)
                x += wd + space
        return top, top + lh * len(lines)

    def _pos(self, it, default):
        p = it.get("pos", default)
        return p[0] * self.W, p[1] * self.H

    def _anchor_px(self, it, frame_no):
        name = it.get("anchor")
        if name and self.tracking:
            idx = self._tidx.get(frame_no)
            if idx is None:
                return None
            data = self.tracking["anchors"].get(name)
            if not data:
                self._warn(f"anchor '{name}' not in tracking data")
                return None
            x, y, vis = data[idx]
            return (x * self.W, y * self.H) if vis else None
        if it.get("pos"):
            return self._pos(it, (0.5, 0.5))
        self._warn(f"no tracking data for anchor '{name}' (placeholder mode) - drawing at centre")
        return self.W * 0.5, self.H * 0.45

    # ---- overlay types ------------------------------------------------
    def _draw_caption(self, layer, d, it, t, frame_no):
        a = self._alpha(it, t, 0.06, 0.06)
        pop = _clamp((t - it["start"]) / 0.12)
        size = self.H * self.st["caption_size"] * (1.12 - 0.12 * ease_out_cubic(pop))
        self._draw_rich(d, it["text"], size, self.W / 2, self.H * self.st["caption_y"], a,
                        upper=it.get("upper", True), max_w=self.W * 0.84)

    def _draw_title(self, layer, d, it, t, frame_no):
        a = self._alpha(it, t, 0.12, 0.25)
        pop = ease_out_back((t - it["start"]) / 0.35)
        size = self.H * float(it.get("size", self.st["title_size"])) * (0.6 + 0.4 * pop)
        cx, cy = self._pos(it, (0.5, self.st["title_y"]))
        if it.get("box"):
            font = self.font(size)
            lines = self._layout(d, _parse_rich(it["text"], it.get("upper", True)), font, self.W * 0.8)
            h = size * 1.12 * len(lines)
            w = max(sum(d.textlength(x[0], font=font) for x in ln) for ln in lines) + size * 0.6 * len(lines[0])
            w = min(w, self.W * 0.92)
            d.rounded_rectangle([cx - w / 2 - size * 0.4, cy - h / 2 - size * 0.3,
                                 cx + w / 2 + size * 0.4, cy + h / 2 + size * 0.3],
                                radius=size * 0.35, fill=_hex(self.st["highlight_color"], a))
            self._draw_rich(d, it["text"], size, cx, cy, a, upper=it.get("upper", True),
                            max_w=self.W * 0.8, color=self.st["card_fg"], stroke_ratio=0,
                            hl_color=self.st["accent"])
        else:
            self._draw_rich(d, it["text"], size, cx, cy, a, upper=it.get("upper", True),
                            max_w=self.W * 0.88)

    def _draw_label(self, layer, d, it, t, frame_no):
        pt = self._anchor_px(it, frame_no)
        if pt is None:
            return
        ax, ay = pt
        a = self._alpha(it, t, 0.2, 0.15)
        pop = ease_out_back((t - it["start"]) / 0.3)
        off = it.get("offset", [0.0, -0.075])
        size = self.H * self.st["label_size"]
        font = self.font(size)
        tw = d.textlength(it["text"], font=font)
        padx, pady = size * 0.6, size * 0.38
        bw, bh = (tw + 2 * padx) * (0.7 + 0.3 * pop), size + 2 * pady
        bx = _clamp(ax + off[0] * self.W, self.W * 0.03 + bw / 2, self.W * 0.97 - bw / 2)
        by = _clamp(ay + off[1] * self.H * pop, self.H * 0.03 + bh / 2, self.H * 0.97 - bh / 2)
        dark, white = _hex(self.st["stroke_color"], a), _hex("#FFFFFF", a)
        d.line([(ax, ay), (bx, by)], fill=dark, width=9)
        d.line([(ax, ay), (bx, by)], fill=white, width=4)
        r = size * 0.28
        d.ellipse([ax - r, ay - r, ax + r, ay + r], fill=white, outline=dark, width=4)
        d.rounded_rectangle([bx - bw / 2, by - bh / 2, bx + bw / 2, by + bh / 2], radius=bh / 2,
                            fill=_hex(it.get("bg", self.st["label_bg"]), a * 0.92), outline=white, width=4)
        if pop > 0.6:
            d.text((bx, by), it["text"], font=font, fill=_hex(self.st["label_fg"], a), anchor="mm")

    def _draw_counter(self, layer, d, it, t, frame_no):
        a = self._alpha(it, t, 0.15, 0.2)
        dur = float(it.get("count_time", max(0.3, it["end"] - it["start"] - 0.4)))
        p = ease_out_cubic((t - it["start"]) / dur)
        v0, v1 = float(it.get("from", 0)), float(it.get("to", 100))
        val = v0 + (v1 - v0) * p
        txt = f"{val:.{int(it.get('decimals', 0))}f}{it.get('suffix', '')}"
        alert = it.get("alert_above") is not None and val > float(it["alert_above"])
        cx, cy = self._pos(it, (0.5, 0.33))
        size = self.H * float(it.get("size", self.st["counter_size"]))
        font = self.font(size)
        sub = it.get("sub")
        sfont = self.font(size * 0.34)
        tw = max(d.textlength(txt, font=font), d.textlength(sub, font=sfont) if sub else 0)
        h = size * (1.0 + (0.55 if sub else 0))
        d.rounded_rectangle([cx - tw / 2 - size * 0.4, cy - h / 2 - size * 0.25,
                             cx + tw / 2 + size * 0.4, cy + h / 2 + size * 0.25],
                            radius=size * 0.3, fill=_hex("#111111", a * 0.78))
        ty = cy - (size * 0.25 if sub else 0)
        d.text((cx, ty), txt, font=font, anchor="mm",
               fill=_hex(self.st["accent"] if alert else self.st["text_color"], a))
        if sub:
            d.text((cx, cy + size * 0.48), sub, font=sfont, anchor="mm", fill=_hex("#DDDDDD", a))

    def _draw_card(self, layer, d, it, t, frame_no):
        a = self._alpha(it, t, 0.2, 0.2)
        pop = ease_out_back((t - it["start"]) / 0.35)
        cx, cy = self._pos(it, (0.5, 0.30))
        items = it.get("items", [])
        isz = self.H * 0.031
        tsz = self.H * 0.037
        row = isz * 1.75
        w = self.W * 0.84 * (0.85 + 0.15 * pop)
        h = (tsz * 1.6 if it.get("title") else 0) + row * len(items) + isz * 1.0
        x0, y0 = cx - w / 2, cy - h / 2
        d.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=isz * 0.8,
                            fill=_hex(self.st["card_bg"], a * 0.95),
                            outline=_hex(self.st["stroke_color"], a), width=5)
        y = y0 + isz * 0.5
        if it.get("title"):
            d.text((cx, y + tsz * 0.7), it["title"].upper(), font=self.font(tsz), anchor="mm",
                   fill=_hex(self.st["card_fg"], a))
            y += tsz * 1.6
        stagger = float(it.get("stagger", 0.45))
        for k, text in enumerate(items):
            ia = a * _clamp((t - it["start"] - 0.25 - k * stagger) / 0.2)
            if ia <= 0:
                y += row
                continue
            r = isz * 0.6
            ccx, ccy = x0 + isz * 1.3, y + row / 2
            d.ellipse([ccx - r, ccy - r, ccx + r, ccy + r], fill=_hex(self.st["accent"], ia))
            d.text((ccx, ccy), str(k + 1), font=self.font(isz * 0.8), anchor="mm", fill=_hex("#FFFFFF", ia))
            d.text((ccx + r + isz * 0.6, ccy), text, font=self.font(isz), anchor="lm",
                   fill=_hex(self.st["card_fg"], ia))
            y += row

    def _draw_flash(self, base, it, t):
        dur = max(0.01, it["end"] - it["start"])
        a = (1 - _clamp((t - it["start"]) / dur)) ** 1.5 * float(it.get("strength", 0.85))
        base.alpha_composite(Image.new("RGBA", (self.W, self.H), _hex("#FFFFFF", a)))

    def _draw_image(self, layer, d, it, t, frame_no):
        path = Path(it["file"])
        path = path if path.is_absolute() else ROOT / path
        key = (str(path), it.get("width", 0.3))
        if key not in self._images:
            img = Image.open(path).convert("RGBA")
            w = int(self.W * float(it.get("width", 0.3)))
            self._images[key] = img.resize((w, int(img.height * w / img.width)), Image.LANCZOS)
        img = self._images[key]
        a = self._alpha(it, t)
        if a < 1:
            img = img.copy()
            img.putalpha(img.getchannel("A").point(lambda v: int(v * a)))
        cx, cy = self._pos(it, (0.5, 0.4))
        layer.alpha_composite(img, (int(cx - img.width / 2), int(cy - img.height / 2)))


def contact_sheet(paths, out_path, cols=2, width=540):
    imgs = [Image.open(p).convert("RGB") for p in paths]
    if not imgs:
        return None
    h = int(imgs[0].height * width / imgs[0].width)
    rows = math.ceil(len(imgs) / cols)
    sheet = Image.new("RGB", (cols * width, rows * h), (30, 30, 30))
    for i, im in enumerate(imgs):
        sheet.paste(im.resize((width, h), Image.LANCZOS), ((i % cols) * width, (i // cols) * h))
    sheet.save(out_path)
    return out_path
