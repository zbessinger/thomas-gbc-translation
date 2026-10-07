"""Build the English ROM: install the English font and repack the bank-18 dialogue script.

English text in script/dialogue.yaml (`en` field) is plain prose. The tool word-wraps it to
the text box width and paginates every `lines` lines. Explicit breaks are also honoured:
  "\n"      -> forced line break
  "<PAGE>"  -> forced page break (wait for button, clear box)
Untranslated entries keep a short placeholder so the game stays playable.
"""
import argparse
import hashlib
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from dump_text import BANK_BASE, PTR_COUNT, PTR_TABLE

CLEAN_SHA1 = "8abd4406ec19bfecd6d675285fa73ef2d5ea622e"
FONT_BASE = 0x61F20           # glyph for code N lives at FONT_BASE + N*16 (bank 0x18)
TEXT_START = 0x49A50          # first byte of the original script block
TEXT_END = 0x4C000            # end of bank 0x12 (original text + trailing free space)
MAX_GLYPHS = 0x100 - 0xA7     # VRAM slots the loader can allocate per message (hangs beyond this)
FIRST_CODE = 0x0B             # first code reused for English glyphs (after space + digits)
RESERVED = {0x79, 0x7A}       # mark codes: the printer draws them on the row above

# Text starts at screen column 2. Lines 1-2 may use 17 columns; the last line of a page
# stops at 15 because the blinking "next" arrow sprite covers columns 17-18 of that row.
DEFAULT_WIDTHS = [17, 17, 15]


# ---------------------------------------------------------------- font

def load_font(path):
    """Parse gfx/font_en.txt -> {char: [7 row strings]}"""
    glyphs, cur, rows = {}, None, []
    for line in Path(path).read_text().splitlines():
        if line.startswith("//") or not line.strip():
            continue
        if line.startswith("== "):
            if cur is not None:
                glyphs[cur] = rows
            name = line[3:]
            cur, rows = (" " if name == "space" else name), []
        else:
            rows.append(line.ljust(8, ".")[:8])
    if cur is not None:
        glyphs[cur] = rows
    for ch, r in glyphs.items():
        if len(r) != 8:
            raise ValueError(f"glyph {ch!r} has {len(r)} rows, expected 8")
    return glyphs


def glyph_to_2bpp(rows):
    """'#'=1, '+'=2, '.'=3 (background), matching the original font's colour use."""
    value = {".": 3, "#": 1, "+": 2}
    out = bytearray()
    for r in rows:
        lo = hi = 0
        for x, ch in enumerate(r):
            v = value[ch]
            lo |= (v & 1) << (7 - x)
            hi |= (v >> 1) << (7 - x)
        out += bytes([lo, hi])
    return bytes(out)


def build_table(glyphs):
    """Map characters to byte codes. Space=00, digits keep 01-0A, the rest from 0x0B up."""
    table = {" ": 0x00}
    code = FIRST_CODE
    for ch in glyphs:
        if ch in table:
            continue
        if ch.isdigit():
            table[ch] = 0x01 + int(ch)
            continue
        while code in RESERVED:
            code += 1
        table[ch] = code
        code += 1
    if code > 0x84:
        raise ValueError("too many glyphs for the font area")
    return table


# ---------------------------------------------------------------- text layout

def wrap(text, widths):
    """Word-wrap plain English into pages. `widths` gives the max length of each line on a
    page (its length is the number of lines per page). Returns list[list[str]]."""
    pages = []
    for raw_page in text.split("<PAGE>"):
        page = []
        forced = raw_page.strip("\n").split("\n")
        for pi, para in enumerate(forced):
            words = para.split()
            cur = ""
            while words:
                width = widths[len(page)]
                w = words[0]
                if len(w) > min(widths):
                    raise ValueError(f"word longer than box width: {w!r}")
                cand = f"{cur} {w}" if cur else w
                if len(cand) <= width:
                    cur = cand
                    words.pop(0)
                    continue
                page.append(cur)
                cur = ""
                if len(page) == len(widths):
                    pages.append(page)
                    page = []
            page.append(cur)
            if len(page) == len(widths) and (pi < len(forced) - 1):
                pages.append(page)
                page = []
        if page:
            pages.append(page)
    return pages


def encode_pages(pages, table):
    out = bytearray()
    for pi, page in enumerate(pages):
        for li, line in enumerate(page):
            for ch in line:
                if ch not in table:
                    raise ValueError(f"no glyph for {ch!r}")
                out.append(table[ch])
            if li < len(page) - 1:
                out += b"\xff\x00"
        out += b"\xff\x01" if pi < len(pages) - 1 else b"\xff\x02"
    return bytes(out)


# ---------------------------------------------------------------- build

def build(rom, entries, glyphs, check_only=False):
    table = build_table(glyphs)
    rom = bytearray(rom)
    errors, blobs = [], []

    for e in entries:
        en = (e.get("en") or "").strip()
        if e["len"] == 0:                 # unused slot (ids 253-255)
            blobs.append((e, None))
            continue
        if not en:
            en = "..." if e["jp"] == "<END>" else f"(untranslated {e['addr']})"
        widths = e.get("widths", DEFAULT_WIDTHS)
        try:
            pages = wrap(en, widths) if e["jp"] != "<END>" else []
            blob = encode_pages(pages, table) if pages else b"\xff\x02"
        except ValueError as exc:
            errors.append(f"{e['addr']}: {exc}")
            continue
        uniq = len(set(b for b in blob if b != 0xFF) | {0})
        if uniq > MAX_GLYPHS:
            errors.append(f"{e['addr']}: {uniq} distinct glyphs > {MAX_GLYPHS}")
        blobs.append((e, blob))

    # pack
    pos, new_addr = TEXT_START, {}
    for e, blob in blobs:
        if blob is None:
            continue
        new_addr[e["addr"]] = pos - BANK_BASE + 0x4000
        rom[pos:pos + len(blob)] = blob
        pos += len(blob)
    used, budget = pos - TEXT_START, TEXT_END - TEXT_START
    if pos > TEXT_END:
        errors.append(f"script is {used} bytes, budget {budget} (over by {pos - TEXT_END})")
    rom[pos:TEXT_END] = b"\xff" * max(0, TEXT_END - pos)

    # pointers (unused ids -> message 0, which is an empty <END>)
    first = new_addr[entries[0]["addr"]]
    ptrs = [first] * PTR_COUNT
    for e in entries:
        for i in e["ids"]:
            ptrs[i] = new_addr.get(e["addr"], first)
    for i, p in enumerate(ptrs):
        rom[PTR_TABLE + 2 * i:PTR_TABLE + 2 * i + 2] = bytes([p & 0xFF, p >> 8])

    # font
    for ch, code in table.items():
        rom[FONT_BASE + code * 16:FONT_BASE + code * 16 + 16] = glyph_to_2bpp(glyphs[ch] if ch != " " else ["." * 8] * 8)

    return bytes(rom), errors, used, budget


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rom", default="rom/thomas-jp.gbc")
    ap.add_argument("--script", default="script/dialogue.yaml")
    ap.add_argument("--font", default="gfx/font_en.txt")
    ap.add_argument("--out", default="out/thomas-en.gbc")
    ap.add_argument("--check", action="store_true", help="validate only, do not write")
    args = ap.parse_args()

    rom = Path(args.rom).read_bytes()
    if hashlib.sha1(rom).hexdigest() != CLEAN_SHA1:
        sys.exit(f"{args.rom} is not the expected clean ROM (SHA-1 {CLEAN_SHA1})")
    entries = yaml.safe_load(Path(args.script).read_text())
    out, errors, used, budget = build(rom, entries, load_font(args.font))
    done = sum(1 for e in entries if (e.get("en") or "").strip())
    print(f"translated {done}/{len(entries)} messages; script {used}/{budget} bytes ({100 * used // budget}%)")
    for err in errors:
        print("ERROR", err)
    if errors:
        sys.exit(1)
    if not args.check:
        Path(args.out).parent.mkdir(exist_ok=True)
        Path(args.out).write_bytes(out)
        print("wrote", args.out)


if __name__ == "__main__":
    main()
