"""Minigame menu: the "clear stages for more games" banner is 20 OBJ sprites (8x16, 10x2)
using tiles $02-$29 of the screen's sprite stream ($1E:4000 -> $8000, VRAM bank 0) and OBJ
palette 1. gfx/screens/minigame/banner.png (80x32) is encoded back 1:1."""
import json
from pathlib import Path

from PIL import Image

from sprites import block_tiles, encode_block, obj_palette

DIR = Path(__file__).resolve().parent.parent / "gfx/screens/minigame"


class MinigameBanner:
    def reserved(self, rom):
        return set()

    def __call__(self, rom, vram, tmap, tattr):
        png = DIR / "banner.png"
        if png.exists():
            meta = json.loads((DIR / "meta.json").read_text())
            pal = obj_palette(bytes.fromhex(meta["obj_palettes"]), 1)
            encode_block(Image.open(png), vram[0], block_tiles(0x02, 10, 2), pal)
        return []
