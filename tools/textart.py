"""Helpers for painting English text onto exported screen images (gfx/screens/*/make.py).

Text is rendered as a 1-bit mask, then composited as stacked outline layers, e.g.
    layers=[(RED, 2), (WHITE, 1), (BLUE, 0)]  -> 2px red outer ring, 1px white ring, blue fill
Everything stays within the screen's existing colours so the retiler can find palettes.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT_DIR = Path("/System/Library/Fonts/Supplemental")
ROOT = Path(__file__).resolve().parent.parent


def load_bitmap_font(path=ROOT / "gfx/font_en.txt"):
    glyphs, cur, rows = {}, None, []
    for line in Path(path).read_text().splitlines():
        if line.startswith("//") or not line.strip():
            continue
        if line.startswith("== "):
            if cur is not None:
                glyphs[cur] = rows
            cur, rows = line[3:], []
        else:
            rows.append(line)
    glyphs[cur] = rows
    return glyphs


def bitmap_mask(text, font=None, spacing=1, space=3):
    """Proportional rendering of the 8x8 dialogue font (ink columns only)."""
    font = font or load_bitmap_font()
    cols = []
    for ch in text:
        if ch == " ":
            cols += [[0] * 8] * space
            continue
        g = font[ch]
        ink = [x for x in range(8) if any(r[x] == "#" for r in g)]
        for x in range(min(ink), max(ink) + 1):
            cols.append([1 if g[y][x] == "#" else 0 for y in range(8)])
        cols += [[0] * 8] * spacing
    cols = cols[:-spacing] if spacing else cols
    m = Image.new("1", (len(cols), 8))
    for x, c in enumerate(cols):
        for y, v in enumerate(c):
            if v:
                m.putpixel((x, y), 1)
    return m.crop(m.getbbox())


def ttf_mask(text, font="Arial Rounded Bold.ttf", size=20, tracking=0):
    f = ImageFont.truetype(str(FONT_DIR / font), size)
    w = sum(int(f.getlength(c)) + tracking for c in text) + size
    m = Image.new("L", (w, size * 2), 0)
    d = ImageDraw.Draw(m)
    d.fontmode = "1"  # no anti-aliasing
    x = 0
    for c in text:
        d.text((x, 0), c, font=f, fill=255)
        x += int(f.getlength(c)) + tracking
    m = m.point(lambda v: 255 if v > 0 else 0).convert("1")
    return m.crop(m.getbbox())


def scale_mask(mask, width=None, height=None):
    w = width or mask.width
    h = height or mask.height
    return mask.resize((w, h), Image.NEAREST)


def dilate(mask, r):
    if r == 0:
        return mask
    out = Image.new("1", (mask.width + 2 * r, mask.height + 2 * r))
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if abs(dx) + abs(dy) <= r + (1 if r > 1 else 0):   # rounded-ish ring
                out.paste(1, (r + dx, r + dy), mask)
    return out


def stamp(img, mask, center_or_xy, layers, anchor="center"):
    """Composite `mask` with outline `layers` [(colour, radius), ...] largest radius first."""
    R = max(r for _, r in layers)
    w, h = mask.width + 2 * R, mask.height + 2 * R
    if anchor == "center":
        cx, cy = center_or_xy
        x0, y0 = int(round(cx - w / 2)), int(round(cy - h / 2))
    else:
        x0, y0 = center_or_xy
    for colour, r in sorted(layers, key=lambda l: -l[1]):
        m = dilate(mask, r)
        img.paste(colour, (x0 + R - r, y0 + R - r), m)
    return (x0, y0, x0 + w, y0 + h)


def replace(img, box, colours, with_colour):
    """Inside `box`, repaint every pixel whose colour is in `colours`."""
    px = img.load()
    x0, y0, x1, y1 = box
    for y in range(y0, y1):
        for x in range(x0, x1):
            if px[x, y] in colours:
                px[x, y] = with_colour
