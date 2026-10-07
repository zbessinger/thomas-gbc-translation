"""Code-drawn card labels (stage select, ...): the screen's code copies an 8x3-cell label onto
each card from tables in bank 2:

    pos   : 4 x map address of each card's label (top-left)
    tiles : 4 x 24 tile indices         attrs : 4 x 24 attributes (VRAM bank 1)

The English art is gfx/screens/<name>/labels_<dub>.png: 64 x 96 RGB, one 64x24 label per
card, painted over the card picture. Each cell is matched to a BG palette (the original
label cell's palette first), de-duplicated, and packed into the tiles the original labels used.
"""
import json
from pathlib import Path

from PIL import Image

from screen import SCREENS, _encode_tile, load_vram, palettes_rgb, read_list, tile_addr

ROOT = Path(__file__).resolve().parent.parent
CARDS, CELLS, COLS = 4, 24, 8


class CardLabels:
    def __init__(self, name, pos, tiles, attrs):
        self.name, self.pos, self.tiles, self.attrs = name, pos, tiles, attrs
        self.dub = "uk"

    def _base(self, rom):
        es = read_list(rom, SCREENS[self.name]["list"])
        vram = load_vram(rom, es)
        used = set()
        for e in es:                      # every tilemap this screen loads
            if e["dest"] in (0x9800, 0x9C00) and e["vbank"] == 0:
                o = e["dest"] - 0x8000
                used |= {((vram[1][o + i] >> 3) & 1, vram[0][o + i]) for i in range(e["size"])}
        return used

    def reserved(self, rom):
        self.base_used = self._base(rom)
        cells = {((rom[self.attrs + i] >> 3) & 1, rom[self.tiles + i]) for i in range(CARDS * CELLS)}
        # tiles shared with the card pictures stay untouched; the rest are ours to repaint
        self.pool = sorted(cells - self.base_used)
        return set(self.pool)

    def __call__(self, rom, vram, tmap, tattr):
        d = ROOT / "gfx/screens" / self.name
        png = d / f"labels_{self.dub}.png"
        if not png.exists():
            return []
        pals = palettes_rgb(bytes.fromhex(json.loads((d / "meta.json").read_text())["palettes"]))
        px = Image.open(png).convert("RGB").load()
        known = {}
        for vb, t in self.base_used:          # existing picture tiles may be reused as-is
            a = tile_addr(t) - 0x8000
            known.setdefault(bytes(vram[vb][a:a + 16]), (vb, t))
        free, placed = list(self.pool), 0
        new_t, new_a = bytearray(), bytearray()
        for card in range(CARDS):
            for k in range(CELLS):
                r, c = divmod(k, COLS)
                cell = [[px[c * 8 + x, card * 24 + r * 8 + y] for x in range(8)] for y in range(8)]
                colours = {v for row in cell for v in row}
                a0 = rom[self.attrs + card * CELLS + k]
                for p in [a0 & 7] + [q for q in range(8) if q != a0 & 7]:
                    if colours <= set(pals[p]):
                        break
                else:
                    raise ValueError(f"{self.name} label {card + 1} cell ({c},{r}): {colours} fit no palette")
                data = _encode_tile([[pals[p].index(v) for v in row] for row in cell])
                if data not in known:
                    if not free:
                        raise ValueError(f"{self.name} labels need more than {len(self.pool)} tiles")
                    vb, t = free.pop(0)
                    known[data] = (vb, t)
                    a = tile_addr(t) - 0x8000
                    vram[vb][a:a + 16] = data
                    placed += 1
                vb, t = known[data]
                new_t.append(t)
                new_a.append((vb << 3) | p)
        print(f"[gfx] {self.name} labels ({self.dub}): {placed} new tiles of {len(self.pool)} free")
        return [(self.tiles, bytes(new_t)), (self.attrs, bytes(new_a))]
