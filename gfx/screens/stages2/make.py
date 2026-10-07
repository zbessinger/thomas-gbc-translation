"""Stage select page 2 (the Stage 5 card, $9C00 tilemap).  python gfx/screens/stages2/make.py"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "tools"))
from PIL import Image
from textart import bitmap_mask, replace, stamp, ttf_mask

SKY, BLUE, YELLOW = (0, 224, 248), (0, 80, 248), (248, 248, 0)

img = Image.open(HERE / "original.png").convert("RGB")
replace(img, (16, 12, 144, 50), {BLUE, YELLOW}, SKY)        # ステージ5 / おおきなまち
stamp(img, bitmap_mask("Stage 5", space=3), (80, 24), [(BLUE, 1), (YELLOW, 0)])
town = ttf_mask("Big Town", "Arial Black.ttf", 14)
assert town.width <= 120, town.width
stamp(img, town, (80, 40), [(BLUE, 1), (YELLOW, 0)])
img.save(HERE / "screen.png")
print("wrote", HERE / "screen.png")
