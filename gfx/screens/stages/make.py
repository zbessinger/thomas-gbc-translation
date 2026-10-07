"""Stage select: the 4 code-drawn card labels (labels_<dub>.png, see tools/card_labels.py).
The background has no text.  python gfx/screens/stages/make.py"""
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "tools"))
from PIL import Image
from textart import bitmap_mask, stamp

BLUE, YELLOW = (0, 80, 248), (248, 248, 0)
CARDS = [(8, 8), (88, 8), (8, 80), (88, 80)]          # label top-left on screen (8x3 cells)
NAMES = {"uk": ["Farm", "Seaside", "Harbour", "Mountain"],
         "us": ["Farm", "Seaside", "Harbor", "Mountain"]}
# Card 4's label row 2-3 has rock in its first/last cells (palette without blue/yellow).
SAFE_X = {3: (9, 55)}

shutil.copy(HERE / "original.png", HERE / "screen.png")   # background unchanged
base = Image.open(HERE / "original.png").convert("RGB")

for dub, names in NAMES.items():
    sheet = Image.new("RGB", (64, 96))
    for i, ((x, y), name) in enumerate(zip(CARDS, names)):
        lab = base.crop((x, y, x + 64, y + 24))
        lo, hi = SAFE_X.get(i, (1, 63))
        for text, cy in ((f"Stage {i + 1}", 6), (name, 17)):
            m = bitmap_mask(text, space=3)
            assert m.width + 2 <= hi - lo, (text, m.width)
            stamp(lab, m, ((lo + hi) / 2, cy), [(BLUE, 1), (YELLOW, 0)])
        sheet.paste(lab, (0, 24 * i))
    sheet.save(HERE / f"labels_{dub}.png")
    sheet.resize((sheet.width * 4, sheet.height * 4), Image.NEAREST).save(HERE / f"labels_{dub}_preview.png")
print("wrote labels_uk.png, labels_us.png")
