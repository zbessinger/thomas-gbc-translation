"""Title screen: original.png -> screen.png with English text.  python gfx/screens/title/make.py"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "tools"))
from PIL import Image
from textart import bitmap_mask, replace, scale_mask, stamp, ttf_mask

WHITE, RED, BLUE = (248, 248, 248), (248, 0, 0), (0, 112, 176)
YELLOW, NAVY, GREEN, PINK = (248, 224, 0), (16, 48, 144), (0, 200, 88), (248, 128, 128)

img = Image.open(HERE / "original.png").convert("RGB")

# --- erase the Japanese
replace(img, (32, 36, 140, 95), {WHITE, RED, BLUE}, YELLOW)        # きかんしゃ / トーマス
replace(img, (34, 97, 128, 110), {WHITE, PINK}, RED)                 # ソドーとうのなかまたち
replace(img, (30, 112, 132, 128), {WHITE, RED}, GREEN)               # ボタンをおしてね!

# --- "TANK ENGINE" (white, blue ring, red ring) where きかんしゃ was
stamp(img, bitmap_mask("TANK ENGINE"), (80, 47), [(RED, 2), (BLUE, 1), (WHITE, 0)])

# --- "THOMAS": big rounded capitals, blue fill / white ring / red ring
thomas = ttf_mask("THOMAS", "Arial Black.ttf", 26, tracking=1)
thomas = scale_mask(thomas, width=min(thomas.width, 90), height=21)
stamp(img, thomas, (80, 72), [(RED, 2), (WHITE, 1), (BLUE, 0)])

# --- ribbon: "Friends of Sodor" in white. Must stay inside columns 5-14 (x 40-119): the
# ribbon's end cells use palette 2 (navy/red/yellow/green), which has no white.
ribbon = bitmap_mask("Friends of Sodor", space=1)
assert ribbon.width <= 80, ribbon.width
stamp(img, ribbon, (40, 99), [(WHITE, 0)], anchor="xy")

# --- "PRESS START": white with red ring, as the original prompt
press = ttf_mask("PRESS START", "Arial Black.ttf", 11, tracking=1)
stamp(img, press, (80, 120), [(RED, 1), (WHITE, 0)])

img.save(HERE / "screen.png")
print("wrote", HERE / "screen.png")
