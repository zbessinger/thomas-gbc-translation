"""Build the English ROM: install the English font and repack the bank-18 dialogue script.

English text in script/dialogue.yaml (`en` field) is plain prose. The tool word-wraps it to
the text box width and paginates every `lines` lines. Explicit breaks are also honoured:
  "\n"      -> forced line break
  "<PAGE>"  -> forced page break (wait for button, clear box)
Untranslated entries keep a short placeholder so the game stays playable.
"""
import argparse
import hashlib
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from build_gfx import insert_screens
from dump_text import BANK_BASE, PTR_COUNT, PTR_TABLE

CLEAN_SHA1 = "8abd4406ec19bfecd6d675285fa73ef2d5ea622e"
FONT_BASE = 0x61F20           # glyph for code N lives at FONT_BASE + N*16 (bank 0x18)
TEXT_START = 0x49A50          # first byte of the original script block
TEXT_END = 0x4C000            # end of bank 0x12 (original text + trailing free space)
MAX_GLYPHS = 0x100 - 0xA7     # VRAM slots the loader can allocate per message (hangs beyond this)
FIRST_CODE = 0x0B             # first code reused for English glyphs (after space + digits)
RESERVED = {0x79, 0x7A}       # mark codes: the printer draws them on the row above

# Text box layouts (measured in-game). `widths` = max chars per line on one page.
#  dialogue    any story message. The same message can appear in the cutscene box (text
#              from column 2) or the in-stage portrait box (window layer, columns 7-18,
#              arrow on columns 18-19 of row 3), so everything is wrapped for the narrower
#              one: 12/12/11 (the Japanese also never exceeds 12 per line). Pages allowed.
#  zukan       encyclopedia entry box (column 8-18). FF 01 pages HANG this printer.
#  zukan_intro encyclopedia intro box (column 2-17).
#  system      framed menu-message box; lines are centred like the Japanese.
BOXES = {
    "dialogue":    {"widths": [12, 12, 11], "pages": True,  "center": False},
    "zukan":       {"widths": [11, 11, 11, 11], "pages": False, "center": False},
    "zukan_intro": {"widths": [16, 16, 16], "pages": False, "center": False},
    "system":      {"widths": [16, 16, 16], "pages": False, "center": True},
}


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


def balanced_wrap(text, widths):
    """Like wrap(), but avoid a lonely last line: for each <PAGE> segment, also try
    fewer lines per box and keep that layout if it needs no extra boxes."""
    pages = []
    for segment in text.split("<PAGE>"):
        best = wrap(segment, widths)
        for k in range(len(widths) - 1, 1, -1):
            if len(best) < 2 or len(best[-1]) > 1:
                break
            alt = wrap(segment, widths[:k])
            if len(alt) == len(best):
                best = alt
        pages += best
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


# ---------------------------------------------------------------- dubs

DUBS = ("uk", "us")
_VARIANT = re.compile(r"\{([^{}|]+)\|([^{}|]*)\}|\{(\w+)\}")


def resolve(text, dub, glossary):
    """Pick the UK or US wording: `{uk|us}` inline, or `{token}` from script/glossary.yaml.
    A token written with a capital first letter ({Trucks}) is capitalised."""
    def sub(m):
        if m.group(3) is None:
            return m.group(1) if dub == "uk" else m.group(2)
        key = m.group(3)
        if key in glossary:
            return glossary[key][dub]
        if key.lower() in glossary:  # {Trucks} -> capitalised form of {trucks}
            word = glossary[key.lower()][dub]
            return word[0].upper() + word[1:]
        raise ValueError(f"unknown glossary token {{{key}}}")
    return _VARIANT.sub(sub, text)


# ---------------------------------------------------------------- build

def build(rom, entries, glyphs, dub="uk", glossary=None):
    table = build_table(glyphs)
    rom = bytearray(rom)
    errors, blobs = [], []
    glossary = glossary or {}

    for e in entries:
        try:
            en = resolve((e.get("en") or "").strip(), dub, glossary)
        except ValueError as exc:
            errors.append(f"{e['addr']}: {exc}")
            continue
        if e["len"] == 0:                 # unused slot (ids 253-255)
            blobs.append((e, None))
            continue
        if not en:
            en = "..." if e["jp"] == "<END>" else "TODO"
        box = BOXES[e.get("box", "dialogue")]
        widths = e.get("widths", box["widths"])
        try:
            if e["jp"] == "<END>":
                pages = []
            elif e.get("raw"):          # exact spacing, e.g. the Yes/No prompt
                pages = [en.split("\n")]
                for line in pages[0]:
                    if len(line) > max(widths):
                        raise ValueError(f"raw line too long: {line!r}")
            elif box["pages"]:
                pages = balanced_wrap(en, widths)
            else:
                pages = wrap(en, widths)
            if len(pages) > 1 and not box["pages"]:
                raise ValueError(f"{len(pages)} pages, but the {e.get('box')} box cannot page "
                                 f"(max {len(widths)} lines of {widths[0]})")
            if box["center"] and not e.get("raw"):
                pages = [[l.center(widths[i]).rstrip() for i, l in enumerate(pg)] for pg in pages]
            blob = encode_pages(pages, table) if pages else b"\xff\x02"
        except ValueError as exc:
            errors.append(f"{e['addr']} [{dub}]: {exc}")
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
    ap.add_argument("--glossary", default="script/glossary.yaml")
    ap.add_argument("--dub", choices=DUBS + ("all",), default="all")
    ap.add_argument("--out", default="out/thomas-en-{dub}.gbc", help="{dub} is substituted")
    ap.add_argument("--check", action="store_true", help="validate only, do not write")
    args = ap.parse_args()

    rom = Path(args.rom).read_bytes()
    if hashlib.sha1(rom).hexdigest() != CLEAN_SHA1:
        sys.exit(f"{args.rom} is not the expected clean ROM (SHA-1 {CLEAN_SHA1})")
    entries = yaml.safe_load(Path(args.script).read_text())
    glossary = yaml.safe_load(Path(args.glossary).read_text()) or {}
    glyphs = load_font(args.font)
    done = sum(1 for e in entries if (e.get("en") or "").strip())
    print(f"translated {done}/{len(entries)} messages")
    failed = False
    for dub in (DUBS if args.dub == "all" else (args.dub,)):
        out, errors, used, budget = build(rom, entries, glyphs, dub, glossary)
        print(f"[{dub}] script {used}/{budget} bytes ({100 * used // budget}%)")
        for err in errors:
            print("ERROR", err)
        failed |= bool(errors)
        if not errors and not args.check:
            out = bytes(insert_screens(bytearray(out), dub=dub))
            path = Path(args.out.format(dub=dub))
            path.parent.mkdir(exist_ok=True)
            path.write_bytes(out)
            print("wrote", path)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
