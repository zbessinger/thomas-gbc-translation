"""Main menu: header via screen.png, the 4 items via items.png (index art, see tools/menu_items.py).
python gfx/screens/menu/make.py"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "tools"))
from PIL import Image
from textart import replace, stamp, ttf_mask

WHITE, RED, DKRED, MAGENTA = (248, 248, 248), (248, 0, 0), (144, 0, 24), (248, 0, 248)

ITEMS = ["Continue", "New Story", "Mini-Games", "Friends Book"]

# --- header sign: "What will you play?"
img = Image.open(HERE / "original.png").convert("RGB")
replace(img, (26, 18, 142, 32), {RED, DKRED}, WHITE)
header = ttf_mask("What will you play?", "Arial Bold.ttf", 11)
assert header.width <= 110, header.width
stamp(img, header, (84, 25), [(DKRED, 1), (RED, 0)])
img.save(HERE / "screen.png")

# --- items: index art (0 outline, 1 fill, 2 underline, 3 background), 112x16 per item
art = Image.new("RGB", (112, 16 * len(ITEMS)), (3, 3, 3))
for i, text in enumerate(ITEMS):
    m = ttf_mask(text, "Arial Black.ttf", 12)
    if m.height > 12:
        m = m.resize((m.width, 12), Image.NEAREST)
    assert m.width <= 106, (text, m.width)
    stamp(art, m, (56, 16 * i + 8), [((0, 0, 0), 1), ((1, 1, 1), 0)])
    for x in range(112):
        art.putpixel((x, 16 * i + 15), (2, 2, 2))
art.convert("L").save(HERE / "items.png")

# preview in the normal palette
pal = {0: (0, 40, 248), 1: (248, 240, 0), 2: (248, 160, 72), 3: (248, 240, 120)}
p = Image.new("RGB", art.size)
p.putdata([pal[c[0]] for c in art.getdata()])
p.resize((p.width * 3, p.height * 3), Image.NEAREST).save(HERE / "items_preview.png")
print("wrote screen.png, items.png")
