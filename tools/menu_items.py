"""Main-menu items: each of the 4 items has a normal and a highlighted version, drawn by the
menu code (bank 2) from tables of tile indices + attributes:

    $02:4431  4 x map address of each item's top-left cell (2 rows x 14 columns)
    $02:4439  normal tiles   (4 x 28)      $02:44A9  normal attributes   (4 x 28)
    $02:4521  selected tiles (4 x 28)      $02:4591  selected attributes (4 x 28)

gfx/screens/menu/items.png holds the English art as palette indices (0 outline, 1 fill,
2 underline, 3 background): 112 x 64, one 112 x 16 strip per item. The same index art is
used for both states; the state's palette (2 normal, 5 selected) supplies the colours.
"""
from pathlib import Path

from PIL import Image

from screen import tile_addr

BANK2 = 0x8000
POS, NORM_T, NORM_A, SEL_T, SEL_A = 0x8431, 0x8439, 0x84A9, 0x8521, 0x8591
ITEMS, CELLS = 4, 28
ATTR = {"normal": 0x0A, "selected": 0x0D}      # VRAM bank 1, palette 2 / 5
ART = Path(__file__).resolve().parent.parent / "gfx/screens/menu/items.png"


def _cells(rom, off):
    return [rom[off + i * CELLS:off + (i + 1) * CELLS] for i in range(ITEMS)]


class MenuItems:
    def reserved(self, rom):
        pool = set(rom[NORM_T:NORM_T + ITEMS * CELLS]) | set(rom[SEL_T:SEL_T + ITEMS * CELLS])
        self.pool = sorted(pool)
        return {(1, t) for t in pool}

    def __call__(self, rom, vram, tmap, tattr):
        if not ART.exists():
            return []
        art = Image.open(ART)
        if art.size != (112, 16 * ITEMS):
            raise ValueError(f"{ART} must be 112x{16 * ITEMS}")
        px = art.load()
        free = list(self.pool)
        seen, patches = {}, []
        new_tiles = []                               # per item: 28 tile indices
        for item in range(ITEMS):
            idx = []
            for cell in range(CELLS):
                row, col = divmod(cell, 14)
                data = bytearray()
                for y in range(8):
                    lo = hi = 0
                    for x in range(8):
                        v = px[col * 8 + x, item * 16 + row * 8 + y] & 3
                        lo |= (v & 1) << (7 - x)
                        hi |= (v >> 1) << (7 - x)
                    data += bytes([lo, hi])
                data = bytes(data)
                if data not in seen:
                    if not free:
                        raise ValueError("menu items need more tiles than the pool holds")
                    t = free.pop(0)
                    seen[data] = t
                    a = tile_addr(t) - 0x8000
                    vram[1][a:a + 16] = data
                idx.append(seen[data])
            new_tiles.append(bytes(idx))

        # which state does the screen's own tilemap start in, per item?
        old_norm, old_sel = _cells(rom, NORM_T), _cells(rom, SEL_T)
        for item in range(ITEMS):
            addr = rom[POS + 2 * item] | rom[POS + 2 * item + 1] << 8
            m = addr - 0x9800
            cur = bytes(tmap[m + r * 32 + c] for r in range(2) for c in range(14))
            state = "selected" if cur == bytes(old_sel[item]) and cur != bytes(old_norm[item]) else "normal"
            for cell in range(CELLS):
                r, c = divmod(cell, 14)
                tmap[m + r * 32 + c] = new_tiles[item][cell]
                tattr[m + r * 32 + c] = ATTR[state]

        tiles_blob = b"".join(new_tiles)
        for t_off, a_off, state in ((NORM_T, NORM_A, "normal"), (SEL_T, SEL_A, "selected")):
            patches.append((t_off, tiles_blob))
            patches.append((a_off, bytes([ATTR[state]]) * (ITEMS * CELLS)))
        print(f"[gfx] menu items: {len(seen)} tiles used of {len(self.pool)}")
        return patches
