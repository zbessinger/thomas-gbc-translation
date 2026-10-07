"""'Game Boy Color only' screen (shown on an original Game Boy). Monochrome: drawn in the
index-space greys of tools/screen.py (white = text, black = background).
python gfx/screens/dmg/make.py"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "tools"))
from PIL import Image
from textart import bitmap_mask, stamp, ttf_mask

WHITE, BLACK = (248, 248, 248), (0, 0, 0)

img = Image.open(HERE / "original.png").convert("RGB")
img.paste(BLACK, (16, 20, 98, 87))          # inside the speech bubble
img.paste(BLACK, (4, 100, 156, 128))        # title + subtitle (keep the copyright line)

lines = ["This game only", "works on a", "Game Boy Color.", "Please use a", "Game Boy Color!"]
for i, line in enumerate(lines):
    m = bitmap_mask(line, space=2)
    assert m.width <= 76, (line, m.width)
    stamp(img, m, (20, 26 + 12 * i), [(WHITE, 0)], anchor="xy")

title = ttf_mask("Thomas the Tank Engine", "Arial Bold.ttf", 12)
assert title.width <= 150, title.width
stamp(img, title, (80, 110), [(WHITE, 0)])
stamp(img, bitmap_mask("Friends of Sodor", space=3), (80, 122), [(WHITE, 0)])
img.save(HERE / "screen.png")
print("wrote", HERE / "screen.png")
