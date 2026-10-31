#!/usr/bin/env python3
"""Builds the README images in ../assets, in the idiom of ledutu.com/scriptor.

That page is laid out as the first page of a printed score: expression mark
top-left, composer top-right, title centred, then the first system. Green means
ink that is still wet, so a note appears green and dries to black.

GitHub shows SVGs through <img>, which cannot load fonts, so all text is outlined.

    pip install uharfbuzz fonttools pillow
    python scripts/build_assets.py /path/to/fonts

The folder holds PublicSans-700.ttf and three Newsreader instances:
Newsreader-display.ttf (opsz 48, wght 500), Newsreader-text.ttf (opsz 18, wght 500)
and Newsreader-italic.ttf (italic, opsz 18, wght 400).
"""

import re
import sys
from pathlib import Path

import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "scripts" / "src"
OUT = ROOT / "assets"

# src/sections/generations/landing-type.ts on the site.
PAPER = "#FDFDFB"
TEXT = "#14171A"
MUTED = "rgba(20,23,26,.68)"
LINE = "rgba(20,23,26,.14)"
STAFF = "rgba(20,23,26,.30)"
ACCENT = "#00A76F"
ON_ACCENT = "#04170F"
KEY_BLACK = "#1B1F23"

EXPRESSION = "chép nhạc tự động từ video"
TITLE = "Biến bất kỳ video YouTube, TikTok hoặc Instagram nào thành bản nhạc bạn chơi được"
TITLE_WIDE = (
    "Biến bất kỳ video YouTube, TikTok hoặc",
    "Instagram nào thành bản nhạc bạn chơi được",
)
TITLE_NARROW = (
    "Biến bất kỳ video YouTube,",
    "TikTok hoặc Instagram nào",
    "thành bản nhạc bạn chơi được",
)

# src/sections/generations/hero-score.tsx on the site: the opening phrase and its
# staff geometry, in the same units.
OPENING = (48, 64, 67, 69, 55, 67, 64, 62, 52, 60, 64, 67)
SPACE = 10
SYSTEM_H = 188
TREBLE_BOTTOM = 20 + 4 * SPACE
BASS_BOTTOM = SYSTEM_H - 22
SYSTEM_LEFT = 26
CLEF_X = SYSTEM_LEFT + 18
FIRST_NOTE_X = SYSTEM_LEFT + 92
NOTES_PER_BAR = 4
G_CLEF = (
    "M13 11V7.5l2.2-2.21c.8-.79.95-2.05.39-3.03A2.47 2.47 0 0 0 13.45 1c-.21 0-.45.03-.64.09"
    "C11.73 1.38 11 2.38 11 3.5v3.24L7.86 9.91a5.95 5.95 0 0 0-1.25 6.43c.77 1.9 2.45 3.21 4.39 3.55"
    "v.61c0 .26-.23.5-.5.5H9v2h1.5c1.35 0 2.5-1.11 2.5-2.5V20c2.03 0 4.16-1.92 4.16-4.75"
    "c0-2.3-1.92-4.25-4.16-4.25m0-7.5c0-.23.11-.41.32-.47c.22-.06.45.03.56.23a.5.5 0 0 1-.08.61"
    "l-.8.86zm-2 8c-.97.64-1.7 1.74-1.96 2.76l1.96.52v3.05a3.86 3.86 0 0 1-2.57-2.26"
    "c-.59-1.46-.27-3.12.83-4.24L11 9.5zm2 6.5v-5.06c1.17 0 2.18 1.1 2.18 2.31C15.18 17 13.91 18 13 18"
)

# Same timing as the site: a note every 300 ms, drying over 1.4 s.
START = 0.9
STEP = 0.3

WHITE_STEP = {0: 0, 2: 1, 4: 2, 5: 3, 7: 4, 9: 5, 11: 6}
BLACK_PCS = {1, 3, 6, 8, 10}
LOW, HIGH = 48, 71
TREBLE_BOTTOM_STEP = 30  # E4
BASS_BOTTOM_STEP = 18  # G2
TREBLE_MIDDLE_STEP = 34  # B4
BASS_MIDDLE_STEP = 22  # D3

READINGS = (
    ("Soạn bản piano", "arrangement"),
    ("Ký âm piano", "transcription"),
    ("Ký âm guitar", "guitar"),
    ("Ký âm bass", "bass"),
    ("Lead sheet", "leadsheet"),
    ("Band sheet", "bandsheet"),
)


class Face:
    def __init__(self, path):
        self.tt = TTFont(path)
        self.glyphs = self.tt.getGlyphSet()
        self.order = self.tt.getGlyphOrder()
        self.upem = self.tt["head"].unitsPerEm
        self.font = hb.Font(hb.Face(hb.Blob.from_file_path(str(path))))

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
                parts.append(
                    f'<path transform="translate({gx:.2f} {gy:.2f}) scale({scale:.5f} {-scale:.5f})" d="{d}"/>'
                )
            pen_x += p.x_advance
        return "".join(parts)


def logo(x, y, size):
    raw = (SRC / "logo.svg").read_text()
    inner = re.search(r"<svg[^>]*>(.*)</svg>", raw, re.S).group(1)
    return f'<svg x="{x:.1f}" y="{y:.1f}" width="{size}" height="{size}" viewBox="0 0 750 750">{inner}</svg>'


def step_of(midi):
    return (midi // 12 - 1) * 7 + WHITE_STEP[midi % 12]


def note_svg(midi, x, delay):
    """One written note. Hero-score draws the same shapes; every OPENING pitch is white."""
    step = step_of(midi)
    treble = midi >= 60
    bottom_y = TREBLE_BOTTOM if treble else BASS_BOTTOM
    bottom_step = TREBLE_BOTTOM_STEP if treble else BASS_BOTTOM_STEP
    middle_step = TREBLE_MIDDLE_STEP if treble else BASS_MIDDLE_STEP
    y = bottom_y - (step - bottom_step) * SPACE / 2
    up = step < middle_step
    rx, ry = SPACE * 0.58, SPACE * 0.42
    stem_x = x + rx - 0.7 if up else x - rx + 0.7
    stem_end = y - SPACE * 3.4 if up else y + SPACE * 3.4

    ledgers = ""
    if step <= bottom_step - 2:
        for s in range(bottom_step - 2, step - 1, -2):
            ly = bottom_y - (s - bottom_step) * SPACE / 2
            ledgers += f'<line x1="{x - rx - 4:.1f}" x2="{x + rx + 4:.1f}" y1="{ly}" y2="{ly}" stroke-width="1.1"/>'
    return (
        f'<g class="note" style="animation-delay:{delay:.2f}s,{delay + 0.45:.2f}s">{ledgers}'
        f'<ellipse cx="{x:.1f}" cy="{y}" rx="{rx}" ry="{ry}" stroke-width="0" transform="rotate(-22 {x:.1f} {y})"/>'
        f'<line x1="{stem_x:.1f}" x2="{stem_x:.1f}" y1="{y}" y2="{stem_end}" stroke-width="1.3" stroke-linecap="round"/></g>'
    )


def system_svg(width, note_w):
    """The grand staff in hero-score's own units; the caller scales it into place."""
    out = []
    for bottom in (TREBLE_BOTTOM, BASS_BOTTOM):
        for i in range(5):
            y = bottom - i * SPACE
            out.append(f'<line x1="{SYSTEM_LEFT}" x2="{width}" y1="{y}" y2="{y}" stroke="{STAFF}"/>')

    top = TREBLE_BOTTOM - 4 * SPACE
    out.append(
        f'<line x1="{SYSTEM_LEFT}" x2="{SYSTEM_LEFT}" y1="{top}" y2="{BASS_BOTTOM}" stroke="{TEXT}" stroke-width="1.4"/>'
    )
    brace_x, mid = SYSTEM_LEFT - 8, (top + BASS_BOTTOM) / 2
    out.append(
        f'<path d="M{brace_x} {top}C{brace_x - 9} {top + 14},{brace_x + 3} {mid - 22},{brace_x - 7} {mid}'
        f'C{brace_x + 3} {mid + 22},{brace_x - 9} {BASS_BOTTOM - 14},{brace_x} {BASS_BOTTOM}" '
        f'fill="none" stroke="{TEXT}" stroke-width="2.2" stroke-linecap="round"/>'
    )

    clef_size = SPACE * 5.6
    clef_y = TREBLE_BOTTOM - SPACE - 15.5 * (clef_size / 24)
    out.append(
        f'<svg x="{CLEF_X - 4}" y="{clef_y:.2f}" width="{clef_size}" height="{clef_size}" viewBox="0 0 24 24">'
        f'<path fill="{TEXT}" d="{G_CLEF}"/></svg>'
    )
    s, x, f = SPACE, CLEF_X + 4, BASS_BOTTOM - 3 * SPACE
    out.append(
        f'<path d="M{x} {f}C{x} {f - s * 1.35},{x + s * 1.2} {f - s * 1.5},{x + s * 1.9} {f - s * 0.9}'
        f'C{x + s * 2.6} {f - s * 0.2},{x + s * 2.3} {f + s * 1.3},{x + s * 1.3} {f + s * 2.4}'
        f'C{x + s * 0.7} {f + s * 3.1},{x} {f + s * 3.6},{x - s * 0.4} {f + s * 3.9}" '
        f'fill="none" stroke="{TEXT}" stroke-width="2.4" stroke-linecap="round"/>'
        f'<circle cx="{x + 1}" cy="{f}" r="{s * 0.36}" fill="{TEXT}"/>'
        f'<circle cx="{x + s * 3}" cy="{f - s * 0.5}" r="{s * 0.16}" fill="{TEXT}"/>'
        f'<circle cx="{x + s * 3}" cy="{f + s * 0.5}" r="{s * 0.16}" fill="{TEXT}"/>'
    )

    for i, midi in enumerate(OPENING):
        note_x = FIRST_NOTE_X + i * note_w
        out.append(note_svg(midi, note_x, START + i * STEP))
        if (i + 1) % NOTES_PER_BAR == 0 and i < len(OPENING) - 1:
            bar_x = note_x + note_w / 2
            out.append(
                f'<line class="bar" style="animation-delay:{START + i * STEP:.2f}s" x1="{bar_x}" x2="{bar_x}" '
                f'y1="{top}" y2="{BASS_BOTTOM}" stroke="{TEXT}" opacity=".7"/>'
            )

    cursor_x = FIRST_NOTE_X + len(OPENING) * note_w
    out.append(
        f'<g class="travel"><line class="cursor" x1="{cursor_x}" x2="{cursor_x}" y1="{top - 8}" '
        f'y2="{BASS_BOTTOM + 8}" stroke="{ACCENT}" stroke-width="1.5"/></g>'
    )
    travel = len(OPENING) * note_w
    return "".join(out), travel


def keyboard_svg(x, y, width, height, label_face):
    whites = [m for m in range(LOW, HIGH + 1) if m % 12 not in BLACK_PCS]
    white_w = width / len(whites)
    black_w = white_w * 0.58
    out = []

    def key_path(kx, kw, kh):
        r = 3
        return (
            f"M{kx:.2f} {y}H{kx + kw:.2f}V{y + kh - r}Q{kx + kw:.2f} {y + kh} {kx + kw - r:.2f} {y + kh}"
            f"H{kx + r:.2f}Q{kx:.2f} {y + kh} {kx:.2f} {y + kh - r}Z"
        )

    index = {}
    for i, midi in enumerate(whites):
        index[midi] = i
        kx = x + i * white_w
        out.append(f'<path d="{key_path(kx, white_w, height)}" fill="url(#white)" stroke="{LINE}"/>')
        if midi % 12 == 0:
            label = f"C{midi // 12 - 1}"
            lw = label_face.width(label, 11)
            out.append(
                f'<g fill="{MUTED}">{label_face.path(label, kx + (white_w - lw) / 2, y + height - 8, 11)}</g>'
            )

    # A key goes down as its note is written. Grey, as on the site: green is ink only.
    for i, midi in enumerate(OPENING):
        kx = x + index[midi] * white_w
        out.append(
            f'<path class="press" style="animation-delay:{START + i * STEP:.2f}s" '
            f'd="{key_path(kx, white_w, height)}" fill="#D9DDD8"/>'
        )

    after = -1
    for midi in range(LOW, HIGH + 1):
        if midi % 12 in BLACK_PCS:
            kx = x + (after + 1) * white_w - black_w / 2
            kh = height * 0.62
            out.append(
                f'<rect x="{kx:.2f}" y="{y + kh - 3:.2f}" width="{black_w:.2f}" height="6" rx="3" fill="#000"/>'
                f'<path d="{key_path(kx, black_w, kh)}" fill="url(#black)"/>'
            )
        else:
            after += 1
    out.append(f'<rect x="{x}" y="{y - 2}" width="{width}" height="2" fill="{KEY_BLACK}"/>')
    return "".join(out)


def hero(name, faces, w, lines, title_w, pad, top, mark_size, brand, note_w, k, keys_w, keys_h, fade_from):
    display, italic, wordmark, serif = faces
    size = title_w / max(display.width(line, 1) for line in lines)
    lead = size * 1.12

    mark_y = top + mark_size
    mark = italic.path(EXPRESSION, pad, mark_y, mark_size)

    # Composer's place on a title page: the product, top-right.
    word_size, name_size, logo_size = brand
    name_w = serif.width("Scriptor", name_size)
    word_w = wordmark.width("ledutu", word_size)
    gap = word_size * 0.32
    right = w - pad
    name_x = right - name_w
    word_x = name_x - gap - word_w
    logo_x = word_x - logo_size - gap * 0.7
    brand_svg = (
        logo(logo_x, mark_y - logo_size * 0.8, logo_size)
        + f'<g fill="{TEXT}">{wordmark.path("ledutu", word_x, mark_y, word_size)}'
        + f'{serif.path("Scriptor", name_x, mark_y, name_size)}</g>'
    )

    title_top = mark_y + size * 1.5
    title = "".join(
        display.path(line, (w - display.width(line, size)) / 2, title_top + i * lead, size)
        for i, line in enumerate(lines)
    )

    system_y = title_top + (len(lines) - 1) * lead + size * 0.55
    system_x = pad * 0.6
    system_w = (w - system_x) / k
    system, travel = system_svg(system_w, note_w)

    keys_x = (w - keys_w) / 2
    keys_y = system_y + SYSTEM_H * k + 12
    keys = keyboard_svg(keys_x, keys_y, keys_w, keys_h, wordmark)
    h = keys_y + keys_h + pad
    h = round(h)

    steps = len(OPENING)
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="ledutu Scriptor. {TITLE}">
<style>
.note{{fill:{TEXT};stroke:{TEXT};transform-box:fill-box;transform-origin:center;animation:write .24s cubic-bezier(.2,.8,.2,1) both,dry 1.4s ease-out both}}
@keyframes write{{from{{opacity:0;transform:scale(.55)}}to{{opacity:1;transform:scale(1)}}}}
@keyframes dry{{from{{fill:{ACCENT};stroke:{ACCENT}}}to{{fill:{TEXT};stroke:{TEXT}}}}}
.bar{{animation:settle .4s ease-out both}}
@keyframes settle{{from{{opacity:0}}to{{opacity:.7}}}}
.travel{{animation:travel {steps * STEP:.1f}s steps({steps},start) {START}s backwards}}
@keyframes travel{{from{{transform:translateX({-travel}px)}}to{{transform:translateX(0)}}}}
.cursor{{animation:blink 1.3s steps(1) infinite}}
@keyframes blink{{0%,60%{{opacity:1}}61%,100%{{opacity:0}}}}
.press{{opacity:0;animation:press .36s ease-out}}
@keyframes press{{from{{opacity:1}}to{{opacity:0}}}}
@media (prefers-reduced-motion:reduce){{.note,.bar,.travel,.cursor,.press{{animation:none}}}}
</style>
<defs>
<linearGradient id="white" x1="0" y1="0" x2="0" y2="1"><stop offset=".78" stop-color="#fff"/><stop offset="1" stop-color="#F1F2EF"/></linearGradient>
<linearGradient id="black" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2A2F34"/><stop offset=".7" stop-color="{KEY_BLACK}"/><stop offset="1" stop-color="#0E1114"/></linearGradient>
<linearGradient id="fade" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{PAPER}" stop-opacity="0"/><stop offset="1" stop-color="{PAPER}"/></linearGradient>
</defs>
<rect width="{w}" height="{h}" rx="3" fill="{PAPER}"/>
<g fill="{MUTED}">{mark}</g>
{brand_svg}
<g fill="{TEXT}">{title}</g>
<g transform="translate({system_x:.1f} {system_y:.1f}) scale({k})">{system}</g>
<rect x="{w * fade_from:.1f}" y="{system_y:.1f}" width="{w * (1 - fade_from):.1f}" height="{SYSTEM_H * k:.1f}" fill="url(#fade)"/>
{keys}
<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="3" fill="none" stroke="{LINE}"/>
</svg>
"""
    (OUT / name).write_text(svg)


def button(name, face, label):
    height, size, pad, icon, gap = 48, 18, 32, 20, 10
    text_w = face.width(label, size)
    width = pad * 2 + text_w + gap + icon
    body = (SRC / "icon-forward.svg").read_text().strip()
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.1f} {height}" width="{width:.1f}" height="{height}" role="img" aria-label="{label}">
<rect width="{width:.1f}" height="{height}" rx="3" fill="{ACCENT}"/>
<g fill="{ON_ACCENT}">{face.path(label, pad, height / 2 + size * 0.3, size)}</g>
<svg x="{pad + text_w + gap:.1f}" y="{(height - icon) / 2}" width="{icon}" height="{icon}" viewBox="0 0 24 24" color="{ON_ACCENT}">{body}</svg>
</svg>
"""
    (OUT / name).write_text(svg)


def readings(name, fonts):
    """The same two bars, six ways: panels captured from the live page's figure."""
    panels = [Image.open(SRC / "readings" / f"{key}.png").convert("RGB") for _, key in READINGS]
    pw, ph = panels[0].size
    # Lead sheet and band sheet are one staff, so the last row needs less height.
    last_h = int(ph * 0.58)
    panels[4:] = [panel.crop((0, 0, pw, last_h)) for panel in panels[4:]]
    margin, gutter, title_h, row_gap, head = 48, 40, 52, 28, 64
    width = margin * 2 + pw * 2 + gutter
    height = margin + head + (title_h + ph) * 2 + title_h + last_h + row_gap * 2 + margin
    sheet = Image.new("RGB", (width, height), PAPER)
    draw = ImageDraw.Draw(sheet)

    draw.text(
        (margin, margin),
        "Cùng hai ô nhịp, đọc theo sáu cách",
        font=ImageFont.truetype(str(fonts / "Newsreader-italic.ttf"), 26),
        fill="#595C5E",
    )
    title_font = ImageFont.truetype(str(fonts / "Newsreader-text.ttf"), 30)
    for i, ((title, _), panel) in enumerate(zip(READINGS, panels)):
        x = margin + (i % 2) * (pw + gutter)
        y = margin + head + (i // 2) * (title_h + ph + row_gap)
        draw.text((x, y), title, font=title_font, fill=TEXT)
        sheet.paste(panel, (x, y + title_h))
        draw.rectangle((x, y + title_h, x + pw - 1, y + title_h + panel.height - 1), outline="#DDDEDD")
    draw.rectangle((0, 0, width - 1, height - 1), outline="#DDDEDD")
    sheet.quantize(colors=64, dither=Image.Dither.NONE).save(OUT / name, optimize=True)


def main():
    fonts = Path(sys.argv[1])
    display = Face(fonts / "Newsreader-display.ttf")
    serif = Face(fonts / "Newsreader-text.ttf")
    italic = Face(fonts / "Newsreader-italic.ttf")
    wordmark = Face(fonts / "PublicSans-700.ttf")
    faces = (display, italic, wordmark, serif)
    OUT.mkdir(exist_ok=True)

    hero(
        "hero.svg", faces, w=1280, lines=TITLE_WIDE, title_w=1130, pad=48, top=30, mark_size=21,
        brand=(27, 29, 32), note_w=44, k=1.15, keys_w=880, keys_h=100, fade_from=0.8,
    )
    hero(
        "hero-mobile.svg", faces, w=640, lines=TITLE_NARROW, title_w=576, pad=30, top=22, mark_size=19,
        brand=(21, 23, 25), note_w=38, k=1, keys_w=580, keys_h=86, fade_from=0.9,
    )
    button("cta.svg", serif, "Thử ngay")
    readings("readings.png", fonts)


if __name__ == "__main__":
    main()
