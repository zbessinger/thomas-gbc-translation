"""Full-screen graphics round-trip for LZSS-packed screens (title, menus, ...).

A screen is described by an asset list in bank 0: 6-byte entries
    ptr(LE16), rom_bank, vram_dest(LE16), vram_bank      terminated by FF FF FF
Each entry is an LZSS stream (tools/lz.py) decompressed straight to VRAM.

export: decode a screen to gfx/screens/<name>/screen.png (+ meta.json with palettes and layout)
import: re-tile an edited screen.png into tiles/map/attributes, compress, and return the
        new streams for the build to place (see build_screen()).
"""
import json
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from lz import compress, decompress

# Screens we edit. `list` = ROM offset of the asset list in bank 0.
# `palettes` are the 8 BG palettes (64 bytes BGR555) captured in-game (palette data is
# loaded separately and does not change). `rows` = visible map rows to export.
SCREENS = {
    "title": {"list": 0x1360},
    "menu": {"list": 0x13F3},
}


def read_list(rom, off):
    entries = []
    while rom[off:off + 3] != b"\xff\xff\xff":
        ptr, bank = rom[off] | rom[off + 1] << 8, rom[off + 2]
        dest, vbank = rom[off + 3] | rom[off + 4] << 8, rom[off + 5]
        entries.append({"entry": off, "ptr": ptr, "bank": bank, "dest": dest, "vbank": vbank,
                        "rom": bank * 0x4000 + ptr - 0x4000})
        off += 6
    return entries


def load_vram(rom, entries):
    vram = [bytearray(0x2000), bytearray(0x2000)]
    for e in entries:
        data, length, _ = decompress(rom, e["rom"])
        e["size"], e["stream_len"] = len(data), length
        start = e["dest"] - 0x8000
        vram[e["vbank"]][start:start + len(data)] = data
    return vram


def bgr555_to_rgb(lo, hi):
    v = lo | hi << 8
    r, g, b = v & 31, (v >> 5) & 31, (v >> 10) & 31
    return (r << 3, g << 3, b << 3)  # same expansion as the PyBoy screen buffer


def palettes_rgb(pal_bytes):
    return [[bgr555_to_rgb(pal_bytes[p * 8 + c * 2], pal_bytes[p * 8 + c * 2 + 1]) for c in range(4)]
            for p in range(8)]


def tile_addr(index, signed=True):
    """LCDC.4 = 0 (as on these screens): 0-127 -> $9000+, 128-255 -> $8800+."""
    if signed:
        return 0x9000 + index * 16 if index < 128 else 0x8800 + (index - 128) * 16
    return 0x8000 + index * 16


def tile_pixels(vram, vbank, index, xflip=False, yflip=False):
    a = tile_addr(index) - 0x8000
    t = vram[vbank][a:a + 16]
    rows = []
    for y in range(8):
        lo, hi = t[2 * y], t[2 * y + 1]
        rows.append([((lo >> (7 - x)) & 1) | (((hi >> (7 - x)) & 1) << 1) for x in range(8)])
    if yflip:
        rows.reverse()
    if xflip:
        rows = [r[::-1] for r in rows]
    return rows


def render(vram, pal_bytes, rows=18, cols=32, map_base=0x9800):
    pals = palettes_rgb(pal_bytes)
    img = Image.new("RGB", (cols * 8, rows * 8))
    px = img.load()
    for ty in range(rows):
        for tx in range(cols):
            m = map_base - 0x8000 + ty * 32 + tx
            idx, attr = vram[0][m], vram[1][m]
            pix = tile_pixels(vram, (attr >> 3) & 1, idx, bool(attr & 0x20), bool(attr & 0x40))
            pal = pals[attr & 7]
            for y in range(8):
                for x in range(8):
                    px[tx * 8 + x, ty * 8 + y] = pal[pix[y][x]]
    return img


# ------------------------------------------------------------------ import

def _encode_tile(rows):
    out = bytearray()
    for r in rows:
        lo = hi = 0
        for x, v in enumerate(r):
            lo |= (v & 1) << (7 - x)
            hi |= (v >> 1) << (7 - x)
        out += bytes([lo, hi])
    return bytes(out)


def retile(img, pal_bytes, vram, orig_map, orig_attr, rows, slots, cols=20):
    """Re-tile an edited screen image.

    Cells whose pixels match the original render keep their original map/attribute entries
    untouched (and their tiles are pinned). Edited cells are matched to a BG palette
    containing all their colours (original palette preferred), de-duplicated against existing
    and new tiles (with X/Y flips), and new tiles go into `slots` not pinned by any
    unchanged cell. Returns (new_tiles {(vbank, index): bytes}, map, attr, changed_cells)."""
    pals = palettes_rgb(pal_bytes)
    px = img.convert("RGB").load()
    tmap, tattr = bytearray(orig_map), bytearray(orig_attr)

    def orig_cell(i):
        a = orig_attr[i]
        return tile_pixels(vram, (a >> 3) & 1, orig_map[i], bool(a & 0x20), bool(a & 0x40))

    changed = []
    for ty in range(rows):
        for tx in range(cols):
            i = ty * 32 + tx
            cell = [[px[tx * 8 + x, ty * 8 + y] for x in range(8)] for y in range(8)]
            o, pal = orig_cell(i), pals[orig_attr[i] & 7]
            if any(pal[o[y][x]] != cell[y][x] for y in range(8) for x in range(8)):
                changed.append((i, cell))
    changed_idx = {i for i, _ in changed}
    pinned = {((orig_attr[i] >> 3) & 1, orig_map[i]) for i in range(len(orig_map)) if i not in changed_idx}
    free = [sl for sl in slots if sl not in pinned]

    known = {}                               # tile bytes -> (vbank, index), existing pinned tiles
    for vb, ti in pinned:
        a = tile_addr(ti) - 0x8000
        known.setdefault(bytes(vram[vb][a:a + 16]), (vb, ti))
    new_tiles = {}
    for i, cell in changed:
        a0 = orig_attr[i]
        colours = {c for r in cell for c in r}
        for p in [a0 & 7] + [q for q in range(8) if q != (a0 & 7)]:
            if colours <= set(pals[p]):
                break
        else:
            raise ValueError(f"cell ({i % 32},{i // 32}) colours {colours} fit no palette")
        index = [[pals[p].index(c) for c in r] for r in cell]
        hit = None
        for xf in (False, True):
            for yf in (False, True):
                v = [r[::-1] if xf else r for r in (index[::-1] if yf else index)]
                key = _encode_tile(v)
                if key in known:
                    hit = (known[key], xf, yf)
                    break
            if hit:
                break
        if not hit:
            if not free:
                raise ValueError(f"out of tile slots ({len(new_tiles)} new tiles placed)")
            sl = free.pop(0)
            key = _encode_tile(index)
            known[key] = sl
            new_tiles[sl] = key
            hit = (sl, False, False)
        (vb, ti), xf, yf = hit
        tmap[i] = ti
        tattr[i] = (a0 & 0x80) | (0x40 if yf else 0) | (0x20 if xf else 0) | (vb << 3) | p
    return new_tiles, tmap, tattr, len(changed)


def build_screen(rom, name, png_path, meta, hook=None):
    """Return ([(asset_entry, new_stream_bytes)], rom_patches, stats) for an edited screen.

    `hook(rom, vram, tmap, tattr, reserved)` may further edit VRAM/maps (e.g. the main menu's
    highlight tiles) and returns a list of (rom_offset, bytes) patches. `reserved` is the set
    of (vbank, tile) slots the hook owns; the retiler will not allocate into them."""
    entries = read_list(rom, SCREENS[name]["list"])
    vram = load_vram(rom, entries)
    original = [bytes(v) for v in vram]
    map_e = next(e for e in entries if e["dest"] == 0x9800 and e["vbank"] == 0)
    attr_e = next(e for e in entries if e["dest"] == 0x9800 and e["vbank"] == 1)
    orig_map = bytes(vram[0][0x1800:0x1800 + map_e["size"]])
    orig_attr = bytes(vram[1][0x1800:0x1800 + attr_e["size"]])
    tile_es = [e for e in entries if 0x8800 <= e["dest"] < 0x9800]
    slots = []
    for e in tile_es:
        for a in range(e["dest"], e["dest"] + e["size"], 16):
            slots.append((e["vbank"], (a - 0x9000) // 16 if a >= 0x9000 else 128 + (a - 0x8800) // 16))
    # never touch tiles the original map doesn't show (sprites / runtime-drawn graphics)
    visible = {((orig_attr[i] >> 3) & 1, orig_map[i]) for i in range(len(orig_map))}
    reserved = set(hook.reserved(rom)) if hook else set()
    slots = [sl for sl in slots if sl in visible and sl not in reserved]
    new_tiles, tmap, tattr, nchanged = retile(Image.open(png_path), bytes.fromhex(meta["palettes"]),
                                              vram, orig_map, orig_attr, meta["rows"], slots)
    for (vb, ti), data in new_tiles.items():
        a = tile_addr(ti) - 0x8000
        vram[vb][a:a + 16] = data
    patches = hook(rom, vram, tmap, tattr) if hook else []
    out = []
    for e in tile_es:
        start = e["dest"] - 0x8000
        cur = bytes(vram[e["vbank"]][start:start + e["size"]])
        if cur != original[e["vbank"]][start:start + e["size"]]:
            out.append((e, compress(cur)))
    if tmap != orig_map:
        out.append((map_e, compress(bytes(tmap))))
    if tattr != orig_attr:
        out.append((attr_e, compress(bytes(tattr))))
    return out, patches, {"changed_cells": nchanged, "new_tiles": len(new_tiles), "free_slots": len(slots)}


def export(rom, name, outdir, pal_hex, rows=18):
    entries = read_list(rom, SCREENS[name]["list"])
    vram = load_vram(rom, entries)
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    render(vram, bytes.fromhex(pal_hex), rows=rows).save(outdir / "original.png")
    meta = {"palettes": pal_hex, "rows": rows,
            "assets": [{k: (hex(v) if isinstance(v, int) and k != "vbank" else v) for k, v in e.items()}
                       for e in entries]}
    (outdir / "meta.json").write_text(json.dumps(meta, indent=2))
    return entries
