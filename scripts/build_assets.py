#!/usr/bin/env python3
"""Builds the README images in ../assets.

GitHub shows SVGs through <img>, which cannot load fonts, so all text is outlined.
Colours, type and photo come from ledutu.com (theme preset04, Public Sans, the
landing hero).

    pip install uharfbuzz fonttools
    python scripts/build_assets.py /path/to/folder/with/PublicSans-{700,800}.ttf
"""

import base64
import re
import sys
from pathlib import Path

import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "scripts" / "src"
OUT = ROOT / "assets"

GREEN = "#00A76F"
GREEN_BORDER = "#00A76F"
GREY_900 = "#161C24"
GREY_800 = "#212B36"
GREY_700 = "#454F5B"
GREY_300 = "#DFE3E8"

HEADLINE = ("Chơi được bài hát.", "Rồi hiểu vì sao nó hay.")

# Rootless ii-V-I in C. Each voice moves by a step at most, which is the point of
# the voicing: E5 F4 A4 C5 -> E5 F4 A4 B4 -> D5 E4 G4 B4.
CHORDS = (
    ("Dm9", 0, (65, 69, 72, 76)),
    ("G13", 4, (65, 69, 71, 76)),
    ("Cmaj9", 8, (64, 67, 71, 74)),
)
# (start beat, length in beats) within a four-beat bar: the Charleston comping figure.
COMP = ((0, 1.5), (1.5, 1.0))
HOLD = ((0, 4.0),)
LOW, HIGH = 64, 76
BLACK_KEYS = {1, 3, 6, 8, 10}

SWEEP_SECONDS = 6.0
SWEEP_DELAY = 0.6


class Face:
    def __init__(self, path):
        self.tt = TTFont(path)
        self.glyphs = self.tt.getGlyphSet()
        self.order = self.tt.getGlyphOrder()
        self.upem = self.tt["head"].unitsPerEm
        blob = hb.Blob.from_file_path(str(path))
        self.font = hb.Font(hb.Face(blob))

    def shape(self, text):
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(self.font, buf)
        return buf.glyph_infos, buf.glyph_positions

    def width(self, text, size):
        _, pos = self.shape(text)
        return sum(p.x_advance for p in pos) * size / self.upem

    def path(self, text, x, baseline, size):
        """Returns one <path> d string with its origin at (x, baseline)."""
        infos, pos = self.shape(text)
        scale = size / self.upem
        pen_x = 0
        parts = []
        for info, p in zip(infos, pos):
            pen = SVGPathPen(self.glyphs, ntos=lambda v: f"{v:g}")
            self.glyphs[self.order[info.codepoint]].draw(pen)
            d = pen.getCommands()
            if d:
                gx = x + (pen_x + p.x_offset) * scale
                gy = baseline - p.y_offset * scale
                parts.append((d, gx, gy))
            pen_x += p.x_advance
        return "".join(
            f'<path transform="translate({gx:.2f} {gy:.2f}) scale({scale:.5f} {-scale:.5f})" d="{d}"/>'
            for d, gx, gy in parts
        )


def logo(x, y, size):
    """The site logo, inverted the way the site inverts it on dark surfaces."""
    raw = (SRC / "logo.svg").read_text()
    inner = re.search(r"<svg[^>]*>(.*)</svg>", raw, re.S).group(1)

    def invert(match):
        value = int(match.group(1), 16)
        return f"#{0xFFFFFF - value:06x}"

    inner = re.sub(r"#([0-9a-fA-F]{6})\b", invert, inner)
    return f'<svg x="{x}" y="{y}" width="{size}" height="{size}" viewBox="0 0 750 750">{inner}</svg>'


def piano_roll(x, y, width, row, keys_w):
    roll_x = x + keys_w + 6
    roll_w = width - keys_w - 6
    beat = roll_w / 12
    top = y

    def row_y(midi):
        return top + (HIGH - midi) * row

    out = []
    for midi in range(LOW, HIGH + 1):
        ry = row_y(midi)
        black = midi % 12 in BLACK_KEYS
        out.append(
            f'<rect x="{roll_x:.1f}" y="{ry:.1f}" width="{roll_w:.1f}" height="{row}" '
            f'fill="{"#000" if black else GREY_900}"/>'
        )
        out.append(
            f'<rect x="{x:.1f}" y="{ry + 0.5:.1f}" width="{keys_w * (0.62 if black else 1):.1f}" '
            f'height="{row - 1}" rx="1.5" fill="{GREY_700 if black else GREY_300}"/>'
        )
    roll_h = (HIGH - LOW + 1) * row
    for bar in range(0, 4):
        bx = roll_x + bar * 4 * beat
        out.append(f'<rect x="{bx:.1f}" y="{top}" width="1.5" height="{roll_h}" fill="{GREY_700}"/>')

    for _, start_bar, midis in CHORDS:
        pattern = HOLD if start_bar == 8 else COMP
        for start, length in pattern:
            beat_at = start_bar + start
            delay = SWEEP_DELAY + beat_at / 12 * SWEEP_SECONDS
            for midi in midis:
                out.append(
                    f'<rect class="note" style="animation-delay:{delay:.2f}s" '
                    f'x="{roll_x + beat_at * beat + 2:.1f}" y="{row_y(midi) + 1:.1f}" '
                    f'width="{length * beat - 4:.1f}" height="{row - 2}" rx="3"/>'
                )
    out.append(
        f'<rect class="playhead" x="{roll_x:.1f}" y="{top - 4}" width="3" height="{roll_h + 8}" fill="#fff"/>'
    )
    return "".join(out), roll_x, beat, roll_w


def hero(path, face, w, h, headline_w, logo_size, roll_w, row, keys_w, chord_size, gap_top, name_size):
    photo = base64.b64encode((SRC / "hero-photo.jpg").read_bytes()).decode()
    photo_h = w * 853 / 1280
    size = headline_w / face.width(HEADLINE[1], 1)
    lead = size * 1.06

    pad = w * 0.035
    logo_svg = logo(pad, pad, logo_size)
    name = face.path("ledutu", pad + logo_size + logo_size * 0.2, pad + logo_size * 0.78, name_size)

    head_top = pad + logo_size + gap_top
    lines = "".join(
        face.path(line, (w - face.width(line, size)) / 2, head_top + size + i * lead, size)
        for i, line in enumerate(HEADLINE)
    )

    roll_h = (HIGH - LOW + 1) * row
    roll_y = h - pad - roll_h
    roll_x0 = (w - roll_w) / 2
    roll, inner_x, beat, inner_w = piano_roll(roll_x0, roll_y, roll_w, row, keys_w)
    labels = "".join(
        face.path(label, inner_x + bar * beat + 4, roll_y - chord_size * 0.55, chord_size)
        for label, bar, _ in CHORDS
    )
    fade_end = (head_top + size + lead + size * 0.9) / h

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="ledutu. {' '.join(HEADLINE)}">
<style>
.note{{fill:{GREEN};animation:lit .18s linear backwards}}
@keyframes lit{{from{{fill:{GREY_700}}}to{{fill:{GREEN}}}}}
.playhead{{opacity:0;animation:sweep {SWEEP_SECONDS}s linear {SWEEP_DELAY}s}}
@keyframes sweep{{from{{opacity:1;transform:translateX(0)}}99%{{opacity:1;transform:translateX({inner_w:.1f}px)}}to{{opacity:0;transform:translateX({inner_w:.1f}px)}}}}
@media (prefers-reduced-motion:reduce){{.note,.playhead{{animation:none}}}}
</style>
<defs>
<linearGradient id="fade" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#000" stop-opacity=".5"/><stop offset="{fade_end * 0.6:.3f}" stop-color="#000" stop-opacity=".62"/><stop offset="{fade_end:.3f}" stop-color="#000"/></linearGradient>
<clipPath id="corners"><rect width="{w}" height="{h}" rx="{w * 0.012:.1f}"/></clipPath>
</defs>
<g clip-path="url(#corners)">
<rect width="{w}" height="{h}" fill="#000"/>
<image width="{w}" height="{photo_h:.1f}" preserveAspectRatio="xMidYMid slice" xlink:href="data:image/jpeg;base64,{photo}"/>
<rect width="{w}" height="{h}" fill="url(#fade)"/>
{logo_svg}
<g fill="#fff">{name}{lines}{labels}</g>
{roll}
</g>
</svg>
"""
    (OUT / path).write_text(svg)


def button(path, face, label, fill, border, icon_body, icon_after):
    height, size, pad, icon = 52, 16, 22, 22
    text_w = face.width(label, size)
    width = pad * 2 + text_w + icon + 10
    text_x = pad + (0 if icon_after else icon + 10)
    icon_x = pad + text_w + 10 if icon_after else pad
    baseline = height / 2 + size * 0.35
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.1f} {height}" width="{width:.1f}" height="{height}" role="img" aria-label="{label}">
<rect x=".75" y=".75" width="{width - 1.5:.1f}" height="{height - 1.5}" rx="8" fill="{fill}" stroke="{border}" stroke-width="1.5"/>
<g fill="#fff">{face.path(label, text_x, baseline, size)}</g>
<svg x="{icon_x:.1f}" y="{(height - icon) / 2}" width="{icon}" height="{icon}" viewBox="0 0 24 24" color="#fff">{icon_body}</svg>
</svg>
"""
    (OUT / path).write_text(svg)


def main():
    fonts = Path(sys.argv[1])
    bold = Face(fonts / "PublicSans-700.ttf")
    heavy = Face(fonts / "PublicSans-800.ttf")
    OUT.mkdir(exist_ok=True)

    hero("hero.svg", heavy, 1600, 860, 1240, 64, 1160, 17, 70, 34, 34, 56)
    hero("hero-mobile.svg", heavy, 800, 640, 720, 56, 720, 16, 44, 30, 40, 48)

    arrow = (SRC / "icon-arrow.svg").read_text().strip()
    sheet = (SRC / "icon-sheet.svg").read_text().strip()
    button("cta-chords.svg", bold, "Tìm hợp âm bài hát", GREEN, GREEN, arrow, True)
    button("cta-scriptor.svg", bold, "Tạo sheet từ audio", "#000", GREEN_BORDER, sheet, False)


if __name__ == "__main__":
    main()
