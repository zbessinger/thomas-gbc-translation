"""1:1 tile repaints inside shared LZSS streams (HUD labels, sprite banners, result pictures,
the "おわり" end screen) where the tilemap or sprite layout is fixed by the game's code.

Each region is a grid of tile numbers as they appear on screen. `obj16` regions are rows of
8x16 sprites (each entry is the top tile of a pair). The art for a region lives in
gfx/streams/<name>.png and is drawn in the region's palette (export_originals() writes the
untouched version as <name>.orig.png). Repeated tiles in a layout must stay consistent.

Every edited stream is recompressed into free space and every reference to it is repointed:
asset-list entries in bank 0 and any extra (ptr, bank) tables listed in EXTRA_REFS.
"""
import json
from pathlib import Path

from PIL import Image

from lz import compress, decompress
from screen import bgr555_to_rgb

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "gfx/streams"
CAPTURED = json.loads((ART / "captured.json").read_text()) if (ART / "captured.json").exists() else {}


def _pal(hexstr, n):
    b = bytes.fromhex(hexstr)
    return [bgr555_to_rgb(b[n * 8 + c * 2], b[n * 8 + c * 2 + 1]) for c in range(4)]


def _rows(first, count, step=1):
    return [first + step * i for i in range(count)]


PICTURE_TABLE = 0x487C6          # $12:47C6, 12 x (ptr16, bank, ptr16, bank): tile streams
PIC_MAPS, PIC_ATTRS = 0x422E1, 0x43095   # $10:62E1 / $10:7095: 12 x ptr16 (bank $10) map/attr streams
# text rectangle (rows, cols) of the failure (4-7) and success (8-11) pictures
PIC_RECT = {"fail": (range(2, 7), range(4, 16)), "success": (range(2, 6), range(3, 17))}

REGIONS = {
    # stream 0x722EA: shared minigame sprite banners (tiles from $8000, OBJ palette 0)
    "banner_clear":  dict(stream=0x722EA, base=0x00, mode="obj16", layout=[_rows(0x02, 5, 2)], pal=("junction", "obj", 0)),
    "banner_start":  dict(stream=0x722EA, base=0x00, mode="obj16", layout=[_rows(0x0C, 6, 2)], pal=("junction", "obj", 0)),
    "banner_timeup": dict(stream=0x722EA, base=0x00, mode="obj16", layout=[_rows(0x18, 10, 2)], pal=("junction", "obj", 0)),
    # stream 0x727D4: race win/lose sprites (loaded at $82C0 -> tile $2C)
    "race_win":  dict(stream=0x727D4, base=0x2C, mode="obj16", layout=[_rows(0x58, 4, 2)], pal=("race", "obj", 2)),
    "race_lose": dict(stream=0x727D4, base=0x2C, mode="obj16", layout=[_rows(0x78, 4, 2)], pal=("race", "obj", 2)),
    # HUD tiles loaded at $91D0 (tile $1D), window layer, BG palette 0
    "hud_time":       dict(stream=0x7258C, base=0x1D, mode="bg", layout=[_rows(0x1E, 6), _rows(0x27, 6)], pal=("junction", "bg", 0)),
    "hud_race_time":  dict(stream=0x72668, base=0x1D, mode="bg", layout=[_rows(0x2B, 6), _rows(0x33, 6)], pal=("race", "bg", 0)),
    "hud_race_start": dict(stream=0x72668, base=0x1D, mode="bg", layout=[_rows(0x23, 4)], pal=("race", "bg", 0)),
    "hud_race_goal":  dict(stream=0x72668, base=0x1D, mode="bg", layout=[_rows(0x27, 3)], pal=("race", "bg", 0)),
}
# "おわり" end screen: stream 0x1052D (tiles from $9000) drawn by the raw map at ROM 0x23750
# (bank 8). Rows 6-9, cols 5-14; background tiles $15/$16 are shared and stay fixed.
_END_MAP = 0x23750
REGIONS["owari"] = dict(stream=0x1052D, base=0x00, mode="bg", layout=None, endmap=True,
                        pal=("greys", None, 0))
# result pictures 4-11 (bank $19): text cells of each picture's own tilemap
for _k in range(4, 12):
    REGIONS[f"picture{_k}"] = dict(picture=_k, base=0x00, mode="bg", layout=None,
                                   pal=("picture" if _k < 8 else "success", "bg", 0))


def picture_layout(rom, k):
    """Grid of tile numbers over the picture's text rectangle. Tiles that also appear
    outside it (sky/background) are marked FIXED and must not change."""
    m_off = 0x40000 + (rom[PIC_MAPS + 2 * k] | rom[PIC_MAPS + 2 * k + 1] << 8) - 0x4000
    a_off = 0x40000 + (rom[PIC_ATTRS + 2 * k] | rom[PIC_ATTRS + 2 * k + 1] << 8) - 0x4000
    m, _, _ = decompress(rom, m_off)
    a, _, _ = decompress(rom, a_off)
    rows, cols = PIC_RECT["fail" if k < 8 else "success"]
    count = {}
    for r in range(18):
        for c in range(20):
            count[m[r * 32 + c]] = count.get(m[r * 32 + c], 0) + 1
    grid = []
    for r in rows:
        line = []
        for c in cols:
            t, at = m[r * 32 + c], a[r * 32 + c]
            ok = count[t] == 1 and at & 0x68 == 0          # unique, VRAM bank 0, no flips
            line.append(t if ok else (FIXED, t))
        grid.append(line)
    return grid


def _layout(rom, spec):
    if spec.get("endmap"):
        return end_layout(rom)
    return picture_layout(rom, spec["picture"]) if "picture" in spec else spec["layout"]


GREYS = [(248, 248, 248), (176, 176, 176), (88, 88, 88), (0, 0, 0)]   # index-space editing


def _palette(spec):
    scene, kind, n = spec["pal"]
    if scene == "greys":
        return GREYS
    return _pal(CAPTURED[scene][kind], n)


def end_layout(rom):
    m = rom[_END_MAP:_END_MAP + 576]
    return [[m[r * 32 + c] if m[r * 32 + c] >= 0x1B else (FIXED, m[r * 32 + c]) for c in range(5, 15)]
            for r in range(6, 10)]


def _picture_stream(rom, k):
    o = PICTURE_TABLE + 6 * k
    ptr, bank = rom[o] | rom[o + 1] << 8, rom[o + 2]
    return bank * 0x4000 + ptr - 0x4000


def _stream_of(rom, spec):
    return _picture_stream(rom, spec["picture"]) if "picture" in spec else spec["stream"]


def _tile_pixels(buf, t):
    a = t * 16
    return [[((buf[a + 2 * y] >> (7 - x)) & 1) | (((buf[a + 2 * y + 1] >> (7 - x)) & 1) << 1) for x in range(8)]
            for y in range(8)]


FIXED = "fixed"


def _cells(layout, mode):
    """Yield (x, y, tile, fixed) for each 8x8 cell (obj16 entries are 2 tall)."""
    for r, row in enumerate(layout):
        for c, t in enumerate(row):
            fixed = isinstance(t, tuple)
            t = t[1] if fixed else t
            if mode == "obj16":
                yield c * 8, r * 16, t, fixed
                yield c * 8, r * 16 + 8, t + 1, fixed
            else:
                yield c * 8, r * 8, t, fixed


def render(buf, spec, layout):
    pal = _palette(spec)
    h = 16 if spec["mode"] == "obj16" else 8
    img = Image.new("RGB", (8 * len(layout[0]), h * len(layout)))
    for x0, y0, t, _ in _cells(layout, spec["mode"]):
        px = _tile_pixels(buf, t - spec["base"])
        for y in range(8):
            for x in range(8):
                img.putpixel((x0 + x, y0 + y), pal[px[y][x]])
    return img


def encode(img, buf, spec, layout):
    pal = _palette(spec)
    px = img.convert("RGB").load()
    written = {}
    for x0, y0, t, fixed in _cells(layout, spec["mode"]):
        data = bytearray()
        for y in range(8):
            lo = hi = 0
            for x in range(8):
                c = px[x0 + x, y0 + y]
                if c not in pal:
                    raise ValueError(f"colour {c} at {(x0 + x, y0 + y)} not in palette {pal}")
                v = pal.index(c)
                lo |= (v & 1) << (7 - x)
                hi |= (v >> 1) << (7 - x)
            data += bytes([lo, hi])
        if fixed:
            a = (t - spec["base"]) * 16
            if bytes(data) != bytes(buf[a:a + 16]):
                raise ValueError(f"cell at {(x0, y0)} uses shared tile {t:#x}; it must stay unchanged")
            continue
        if t in written and written[t] != data:
            raise ValueError(f"tile {t:#x} is used twice with different pixels")
        written[t] = bytes(data)
        a = (t - spec["base"]) * 16
        buf[a:a + 16] = data


def export_originals(rom):
    ART.mkdir(parents=True, exist_ok=True)
    for name, spec in REGIONS.items():
        buf, _, _ = decompress(rom, _stream_of(rom, spec))
        render(buf, spec, _layout(rom, spec)).save(ART / f"{name}.orig.png")


def _list_refs(rom, stream_off):
    """Asset-list entries (bank 0, 6 bytes each) pointing at a stream."""
    refs, o = [], 0x10F3
    while o < 0x1460:
        ptr, bank = rom[o] | rom[o + 1] << 8, rom[o + 2]
        if 0x4000 <= ptr < 0x8000 and bank * 0x4000 + ptr - 0x4000 == stream_off and 0x80 <= rom[o + 4] < 0xA0:
            refs.append(o)
        o += 1
    return refs


def apply(rom, alloc, log=print):
    """Re-encode every stream that has edited art; place it with `alloc` and repoint refs."""
    streams = {}
    for name, spec in REGIONS.items():
        png = ART / f"{name}.png"
        if not png.exists():
            continue
        off = _stream_of(rom, spec)
        if off not in streams:
            buf, _, _ = decompress(rom, off)
            streams[off] = (bytearray(buf), [])
        encode(Image.open(png), streams[off][0], spec, _layout(rom, spec))
        streams[off][1].append(name)
    for off, (buf, names) in streams.items():
        bank, ptr = alloc.place(compress(bytes(buf)))
        refs = _list_refs(rom, off)
        for o in refs:
            rom[o:o + 3] = bytes([ptr & 0xFF, ptr >> 8, bank])
        pics = [k for k in range(12) if _picture_stream(rom, k) == off]
        for k in pics:
            o = PICTURE_TABLE + 6 * k
            rom[o:o + 3] = bytes([ptr & 0xFF, ptr >> 8, bank])
        if not refs and not pics:
            raise ValueError(f"no references found for stream {off:#x}")
        log(f"[gfx] stream {off:#07x} ({', '.join(names)}) -> {bank:#04x}:{ptr:04x}, "
            f"{len(refs)} list refs, {len(pics)} picture refs")
    return rom
