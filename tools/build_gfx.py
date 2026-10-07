"""Insert edited screens (gfx/screens/<name>/screen.png) into a ROM.

New LZSS streams go into free space in GFX_BANKS; the screen's asset-list entries in bank 0
are repointed. Screens without a screen.png are left untouched."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from menu_items import MenuItems
from minigame_banner import MinigameBanner
from card_labels import CardLabels
from book_plates import BookPlates
from screen import SCREENS, build_screen

class Hooks:
    """Several hooks acting on one screen."""
    def __init__(self, *hooks):
        self.hooks = hooks

    @property
    def dub(self):
        return self.hooks[0].dub

    @dub.setter
    def dub(self, value):
        for h in self.hooks:
            h.dub = value

    def reserved(self, rom):
        return set().union(*(h.reserved(rom) for h in self.hooks))

    def __call__(self, rom, vram, tmap, tattr):
        return [p for h in self.hooks for p in h(rom, vram, tmap, tattr)]


HOOKS = {
    "menu": MenuItems(),
    "minigame": Hooks(MinigameBanner(), CardLabels("minigame", pos=0x913B, tiles=0x9143, attrs=0x91A3)),
    "stages": CardLabels("stages", pos=0x8D25, tiles=0x8D2D, attrs=0x8D8D),
    "book": BookPlates(),
}

GFX_BANKS = [0x09, 0x0A, 0x0B, 0x0C, 0x0D]   # entirely free (0xFF) in the original ROM


class Allocator:
    def __init__(self, rom):
        self.rom = rom
        self.cursor = [(b, 0) for b in GFX_BANKS]

    def place(self, blob):
        for i, (bank, used) in enumerate(self.cursor):
            if used + len(blob) <= 0x4000:
                off = bank * 0x4000 + used
                self.rom[off:off + len(blob)] = blob
                self.cursor[i] = (bank, used + len(blob))
                return bank, 0x4000 + used
        raise ValueError("out of graphics space")


def insert_screens(rom, root="gfx/screens", log=print, dub="uk"):
    alloc = Allocator(rom)
    for name in SCREENS:
        png = Path(root) / name / "screen.png"
        if not png.exists():
            continue
        meta = json.loads((Path(root) / name / "meta.json").read_text())
        hook = HOOKS.get(name)
        if hook is not None:
            hook.dub = dub
        streams, patches, stats = build_screen(bytes(rom), name, png, meta, hook)
        for off, data in patches:
            rom[off:off + len(data)] = data
        for e, blob in streams:
            bank, ptr = alloc.place(blob)
            o = e["entry"]
            rom[o:o + 3] = bytes([ptr & 0xFF, ptr >> 8, bank])
        log(f"[gfx] {name}: {stats['changed_cells']} cells changed, {stats['new_tiles']} new tiles, "
            f"{len(streams)} streams rewritten ({sum(len(b) for _, b in streams)} bytes)")
    return rom


if __name__ == "__main__":
    rom = bytearray(Path(sys.argv[1]).read_bytes())
    insert_screens(rom, dub=sys.argv[3] if len(sys.argv) > 3 else "uk")
    Path(sys.argv[2]).write_bytes(rom)
