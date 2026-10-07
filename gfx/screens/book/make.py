"""Encyclopedia ("Friends Book"): intro header, 26 name plates and the page-bar suffix.
Writes header.png (96x24), plates.png (80 x 24*26), pagebar.png (32x16); see tools/book_plates.py.
python gfx/screens/book/make.py"""
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "tools"))
from PIL import Image
from screen import palettes_rgb
from textart import stamp, ttf_mask

pals = palettes_rgb(bytes.fromhex(json.loads((HERE / "meta.json").read_text())["palettes"]))
GOLD, BLACK, YELLOW = pals[5][0], pals[5][1], pals[5][2]

NAMES = ["Thomas", "Edward", "Henry", "Gordon", "James", "Percy", "Toby", "Duck", "Donald",
         "Douglas", "Oliver", "BoCo", "Diesel", "Bill", "Ben", "Mavis", "Rusty", "Daisy",
         "Stepney", "Troublesome\nTrucks", "Harold", "Trevor", "George", "Terence", "Bertie",
         "Caroline"]

shutil.copy(HERE / "original.png", HERE / "screen.png")   # static map has no text


def name_art(text, w, h):
    img = Image.new("RGB", (w, h), GOLD)
    lines = text.split("\n")
    for size in (15, 14, 13, 12, 11, 10, 9):
        masks = [ttf_mask(l, "Arial Black.ttf", size) for l in lines]
        if max(m.width for m in masks) + 2 <= w - 2 and sum(m.height + 2 for m in masks) <= h:
            break
    else:
        raise ValueError(f"{text!r} does not fit {w}x{h}")
    total = sum(m.height + 2 for m in masks)
    y = (h - total) / 2
    for m in masks:
        stamp(img, m, (w / 2, y + (m.height + 2) / 2), [(BLACK, 1), (YELLOW, 0)])
        y += m.height + 2
    return img


name_art("Friends Book", 96, 24).save(HERE / "header.png")

sheet = Image.new("RGB", (80, 24 * len(NAMES)))
for i, n in enumerate(NAMES):
    sheet.paste(name_art(n, 80, 24), (0, 24 * i))
sheet.save(HERE / "plates.png")
sheet.resize((sheet.width * 2, sheet.height * 2), Image.NEAREST).save(HERE / "plates_preview.png")

# page bar: "ページ" -> "/26", orange (index 2) on black (index 1) like the page digits
ORANGE = (248, 160, 0)
pb = Image.new("RGB", (32, 16), BLACK)
m = ttf_mask("/26", "Arial Black.ttf", 15)
assert m.width <= 31, m.width
stamp(pb, m, (16, 8), [(ORANGE, 0)])
pb.save(HERE / "pagebar.png")
print("wrote header.png, plates.png, pagebar.png")
