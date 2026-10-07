"""Encyclopedia graphics drawn by code from uncompressed tables:

  intro header   tiles $41-$5D (VRAM bank 1) of the book's tile stream; 12x3 layout at
                 ROM 0x10509, attributes at 0x104E5 (bank 4)
  name plates    bank 5: 27 pointers at $4000 -> raw tiles; the game copies $200 bytes
                 (32 tiles) from the pointer to tile $41+ of VRAM bank 1. 10x3 layouts at
                 0x128F7 (27 x 30) and attributes at 0x12C21 (bank 4). Entry 27 = "???".
  page bar       "ページ" = tiles $2C-$33 (bank 1, 4x2), palette 3; repainted 1:1.

Art: gfx/screens/book/{header.png, plates.png, pagebar.png} (see make.py there).
"""
from pathlib import Path

from PIL import Image

from screen import tile_addr

ROOT = Path(__file__).resolve().parent.parent / "gfx/screens/book"
HDR_LAYOUT, HDR_ATTR = 0x10509, 0x104E5
B5, ENTRIES = 0x14000, 27
PL_LAYOUT, PL_ATTR = 0x128F7, 0x12C21
FIRST, PLATE_TILES = 0x41, 32
PAL_PLATE = 5
PAGEBAR = [[0x2C, 0x2D, 0x2E, 0x2F], [0x30, 0x31, 0x32, 0x33]]


def _tiles_from(img, cols, rows, colour_index):
    """Cut an image into (layout, unique tile list); colour_index maps RGB -> 0..3."""
    px = img.convert("RGB").load()
    uniq, layout = [], []
    for r in range(rows):
        for c in range(cols):
            data = bytearray()
            for y in range(8):
                lo = hi = 0
                for x in range(8):
                    v = colour_index[px[c * 8 + x, r * 8 + y]]
                    lo |= (v & 1) << (7 - x)
                    hi |= (v >> 1) << (7 - x)
                data += bytes([lo, hi])
            data = bytes(data)
            if data not in uniq:
                uniq.append(data)
            layout.append(uniq.index(data))
    return layout, uniq


class BookPlates:
    dub = "uk"

    def reserved(self, rom):
        return set()

    def __call__(self, rom, vram, tmap, tattr):
        if not (ROOT / "plates.png").exists():
            return []
        from screen import palettes_rgb
        import json
        pals = palettes_rgb(bytes.fromhex(json.loads((ROOT / "meta.json").read_text())["palettes"]))
        plate_idx = {c: i for i, c in enumerate(pals[PAL_PLATE])}
        patches = []

        # intro header -> tiles $41.. in the book stream (VRAM bank 1)
        layout, uniq = _tiles_from(Image.open(ROOT / "header.png"), 12, 3, plate_idx)
        header_tiles = len(uniq)
        if len(uniq) > 0x5D - FIRST + 1:
            raise ValueError(f"header needs {len(uniq)} tiles (max {0x5D - FIRST + 1})")
        for i, data in enumerate(uniq):
            a = tile_addr(FIRST + i) - 0x8000
            vram[1][a:a + 16] = data
        patches.append((HDR_LAYOUT, bytes(FIRST + i for i in layout)))
        patches.append((HDR_ATTR, bytes([0x08 | PAL_PLATE]) * 36))

        # name plates -> repacked raw tiles in bank 5
        sheet = Image.open(ROOT / "plates.png")
        n = sheet.height // 24
        ptrs = [rom[B5 + 2 * i] | rom[B5 + 2 * i + 1] << 8 for i in range(ENTRIES)]
        unknown = rom[B5 + ptrs[-1] - 0x4000:B5 + ptrs[-1] - 0x4000 + PLATE_TILES * 16]
        blob, new_ptrs = bytearray(), []
        lay_all, att_all = bytearray(rom[PL_LAYOUT:PL_LAYOUT + 30 * ENTRIES]), bytearray(rom[PL_ATTR:PL_ATTR + 30 * ENTRIES])
        for e in range(n):
            layout, uniq = _tiles_from(sheet.crop((0, 24 * e, 80, 24 * e + 24)), 10, 3, plate_idx)
            if len(uniq) > PLATE_TILES:
                raise ValueError(f"plate {e + 1} needs {len(uniq)} tiles (max {PLATE_TILES})")
            new_ptrs.append(0x4000 + 2 * ENTRIES + len(blob))
            blob += b"".join(uniq)
            lay_all[30 * e:30 * e + 30] = bytes(FIRST + i for i in layout)
            att_all[30 * e:30 * e + 30] = bytes([0x08 | PAL_PLATE]) * 30
        new_ptrs.append(0x4000 + 2 * ENTRIES + len(blob))   # "???" keeps its own tiles
        blob += unknown
        end = 2 * ENTRIES + len(blob) + PLATE_TILES * 16     # loader reads 32 tiles past a pointer
        if end > 0x4000:
            raise ValueError(f"bank 5 overflow ({end:#x})")
        patches.append((B5, b"".join(bytes([p & 0xFF, p >> 8]) for p in new_ptrs) + bytes(blob)))
        patches.append((PL_LAYOUT, bytes(lay_all)))
        patches.append((PL_ATTR, bytes(att_all)))

        # page bar "/26": orange on black, encoded by palette index (2 on 1)
        bar_idx = {(0, 0, 0): 1, (248, 160, 0): 2}
        layout, uniq = _tiles_from(Image.open(ROOT / "pagebar.png"), 4, 2, bar_idx)
        for k, tile in enumerate(t for row in PAGEBAR for t in row):
            a = tile_addr(tile) - 0x8000
            vram[1][a:a + 16] = uniq[layout[k]]
        print(f"[gfx] book: header {header_tiles} tiles, {n} plates, bank 5 used {end:#x} bytes")
        return patches
