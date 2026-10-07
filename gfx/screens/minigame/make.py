"""Minigame menu: the sprite banner (banner.png). The background has no text.
python gfx/screens/minigame/make.py"""
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "tools"))
from PIL import Image
from textart import bitmap_mask, replace, stamp

RED, ORANGE, PEACH = (248, 0, 0), (248, 144, 40), (248, 208, 144)

shutil.copy(HERE / "original.png", HERE / "screen.png")   # background unchanged

img = Image.open(HERE / "banner_original.png").convert("RGB")
replace(img, (3, 5, 77, 28), {RED, ORANGE}, PEACH)           # erase the Japanese (+ its orange edges)
for text, y in (("Clear stages", 11), ("for more games!", 22)):
    m = bitmap_mask(text, space=3)
    assert m.width <= 76, (text, m.width)
    stamp(img, m, (40, y), [(RED, 0)])
img.save(HERE / "banner.png")
img.resize((img.width * 4, img.height * 4), Image.NEAREST).save(HERE / "banner_preview.png")
print("wrote banner.png")

# --- card titles (code-drawn labels, see tools/card_labels.py); same for both dubs
from textart import ttf_mask

# palette 0 (sky cards) and palette 2 (card 1's grass) use slightly different yellows
YELLOWS = [(248, 248, 0), (248, 232, 0), (248, 232, 0), (248, 232, 0)]
TITLES = ["Coupling", "Bridge Run", "Big Race", "Lightning"]   # きゃくしゃつなぎ はしわたり きょうそう かみなりよけ
CARDS = [(8, 8), (88, 8), (8, 80), (88, 80)]
base = Image.open(HERE / "original.png").convert("RGB")
sheet = Image.new("RGB", (64, 96))
for i, ((x, y), title) in enumerate(zip(CARDS, TITLES)):
    lab = base.crop((x, y, x + 64, y + 24))
    m = ttf_mask(title, "Arial Black.ttf", 10)
    assert m.width <= 60, (title, m.width)
    stamp(lab, m, (32, 9), [(RED, 1), (YELLOWS[i], 0)])
    sheet.paste(lab, (0, 24 * i))
for dub in ("uk", "us"):
    sheet.save(HERE / f"labels_{dub}.png")
sheet.resize((256, 384), Image.NEAREST).save(HERE / "labels_preview.png")
print("wrote labels_uk.png, labels_us.png")
