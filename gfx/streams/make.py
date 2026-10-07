"""English art for tile regions inside shared streams (see tools/stream_edits.py).
Reads <name>.orig.png, writes <name>.png.   python gfx/streams/make.py"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tools"))
from PIL import Image
from textart import bitmap_mask, stamp, ttf_mask

YELLOW, BLACK, RED, WHITE = (248, 248, 0), (0, 0, 0), (248, 0, 0), (248, 248, 248)
LBLUE = (8, 176, 248)
FAIL_SKY, OK_SKY, OK_RED = (136, 176, 200), (88, 184, 248), (248, 0, 16)


def load(name):
    return Image.open(HERE / f"{name}.orig.png").convert("RGB")


def fill(img, box, colour):
    img.paste(colour, box)


def fit(mask, width, name):
    assert mask.width <= width, (name, mask.width, width)
    return mask


# --- minigame banners: yellow box, red text with black outline
for name, text in (("banner_clear", "CLEAR!"), ("banner_start", "START!"), ("banner_timeup", "TIME UP!")):
    img = load(name)
    w, h = img.size
    fill(img, (2, 2, w - 2, h - 2), YELLOW)
    m = fit(bitmap_mask(text, space=2), w - 6, name)
    stamp(img, m, (w / 2, h / 2), [(BLACK, 1), (RED, 0)])
    img.save(HERE / f"{name}.png")

# --- race result sprites: red box, light-blue text with black outline
for name, text in (("race_win", "WIN!"), ("race_lose", "LOSE")):
    img = load(name)
    w, h = img.size
    fill(img, (2, 2, w - 2, h - 2), RED)
    m = fit(bitmap_mask(text, space=2), w - 6, name)
    stamp(img, m, (w / 2, h / 2), [(BLACK, 1), (LBLUE, 0)])
    img.save(HERE / f"{name}.png")

# --- HUD "time left" label: white text, black outline, on the yellow bar
for name in ("hud_time", "hud_race_time"):
    img = load(name)
    fill(img, (0, 0) + img.size, YELLOW)
    m = fit(ttf_mask("TIME", "Arial Black.ttf", 12), 44, name)
    stamp(img, m, (24, 8), [(BLACK, 1), (WHITE, 0)])
    img.save(HERE / f"{name}.png")

# --- race progress-bar labels: white on black, 8px tall
for name, text in (("hud_race_start", "START"), ("hud_race_goal", "GOAL")):
    img = load(name)
    fill(img, (0, 0) + img.size, BLACK)
    m = fit(bitmap_mask(text, space=2), img.width, name)
    stamp(img, m, (0, 0), [(WHITE, 0)], anchor="xy")
    img.save(HERE / f"{name}.png")

# --- result pictures. Failure (4-7): white + black outline on the sky. 96 x 40 region.
for k in range(4, 8):
    img = load(f"picture{k}")
    fill(img, (0, 0) + img.size, FAIL_SKY)
    # shared sky cells: row 2 col 14 (x 80-88, y 0-8) and the corners of rows 5-6, so the
    # big line sits in x 8-88 / y 8-26 and the small one inside x 8-88 below it.
    big = fit(ttf_mask("Too bad!", "Arial Black.ttf", 14), 76, "too bad")
    stamp(img, big, (48, 17), [(BLACK, 1), (WHITE, 0)])
    small = fit(bitmap_mask("Try again!", space=3), 78, "try again")
    stamp(img, small, (48, 34), [(BLACK, 1), (WHITE, 0)])
    img.save(HERE / f"picture{k}.png")

# Success (8-11): red + yellow outline. 112 x 32 region.
for k in range(8, 12):
    img = load(f"picture{k}")
    fill(img, (0, 0) + img.size, OK_SKY)
    big = fit(ttf_mask("Hooray!", "Arial Black.ttf", 17), 108, "hooray")
    stamp(img, big, (56, 11), [(YELLOW, 1), (OK_RED, 0)])
    small = fit(bitmap_mask("Well done!", space=3), 62, "well done")
    stamp(img, small, (56, 27), [(YELLOW, 1), (OK_RED, 0)])
    img.save(HERE / f"picture{k}.png")

print("wrote stream art")

# --- "おわり" end screen -> "THE END": black with grey outline (index space), rows 7-8 only
import stream_edits as se  # noqa: E402

GREY_BG, GREY_MID, GREY_INK = se.GREYS[0], se.GREYS[1], se.GREYS[3]
orig = load("owari")
img = orig.copy()
rom = (HERE.parents[1] / "rom/thomas-jp.gbc").read_bytes()
for r, row in enumerate(se.end_layout(rom)):
    for c, t in enumerate(row):
        if not isinstance(t, tuple):                  # unique cell: free to repaint
            img.paste(GREY_BG, (c * 8, r * 8, c * 8 + 8, r * 8 + 8))
m = fit(ttf_mask("THE END", "Arial Black.ttf", 13), 76, "the end")
stamp(img, m, (40, 16), [(GREY_MID, 1), (GREY_INK, 0)])
img.save(HERE / "owari.png")
print("wrote owari.png")
