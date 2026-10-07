"""Insert edited screens (gfx/screens/<name>/screen.png) into a ROM.

New LZSS streams go into free space in GFX_BANKS; the screen's asset-list entries in bank 0
are repointed. Screens without a screen.png are left untouched."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from menu_items import MenuItems
from screen import SCREENS, build_screen

HOOKS = {"menu": MenuItems()}

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


def insert_screens(rom, root="gfx/screens", log=print):
    alloc = Allocator(rom)
    for name in SCREENS:
        png = Path(root) / name / "screen.png"
        if not png.exists():
            continue
        meta = json.loads((Path(root) / name / "meta.json").read_text())
        hook = HOOKS.get(name)
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
    insert_screens(rom)
    Path(sys.argv[2]).write_bytes(rom)
