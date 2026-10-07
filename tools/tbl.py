"""Character table for Kikansha Thomas (GBC). Codes verified against the ROM font at 0x61F20."""
import re
import unicodedata

HIRA = "あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん"
HIRA_SMALL = "ぁぃぅぇぉゃゅょっ"
KATA = "アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン"
KATA_SMALL = "ァィゥェォャュョッ"
PUNCT = "゜゛、。!「」ー♪?・"

DECODE = {0x00: " "}
for i in range(10):
    DECODE[0x01 + i] = str(i)
for base, chars in ((0x0B, HIRA), (0x39, HIRA_SMALL), (0x42, KATA), (0x70, KATA_SMALL), (0x79, PUNCT)):
    for i, c in enumerate(chars):
        DECODE[base + i] = c

DAKUTEN, HANDAKUTEN = 0x7A, 0x79
CONTROL = {0x00: "<NL>", 0x01: "<PAGE>", 0x02: "<END>"}  # FF xx; meanings to confirm in-game

COMBINING = {"゛": "゙", "゜": "゚"}
SPACING = {v: k for k, v in COMBINING.items()}


def _combine(text):
    """Fold a ゛/゜ mark into the kana that FOLLOWS it (゛か -> が). The game draws the
    mark in the row above the next character, so it is stored before that character."""
    out, i = [], 0
    while i < len(text):
        ch = text[i]
        if ch in COMBINING and i + 1 < len(text):
            merged = unicodedata.normalize("NFC", text[i + 1] + COMBINING[ch])
            if len(merged) == 1:
                out.append(merged)
                i += 2
                continue
        out.append(ch)
        i += 1
    return "".join(out)


def _split(text):
    """Inverse of _combine: が -> ゛か."""
    out = []
    for ch in text:
        nfd = unicodedata.normalize("NFD", ch)
        if len(nfd) == 2 and nfd[1] in SPACING:
            out.append(SPACING[nfd[1]] + nfd[0])
        else:
            out.append(ch)
    return "".join(out)

def decode(data, start, end=None, max_len=0x400):
    """Decode a string starting at `start` until FF 02 (or end). Returns (text, end_offset)."""
    out, o = [], start
    limit = end if end is not None else start + max_len
    while o < limit:
        b = data[o]
        if b == 0xFF:
            arg = data[o + 1]
            if arg == 0xFF:  # unused slot pointing at empty fill
                break
            out.append(CONTROL.get(arg, "<FF:%02X>" % arg))
            o += 2
            if arg == 0x02 and end is None:
                break
            continue
        out.append(DECODE.get(b, "<%02X>" % b))
        o += 1
    return _combine("".join(out)), o


_TAG = re.compile(r"<(NL|PAGE|END|FF:[0-9A-F]{2}|[0-9A-F]{2})>")
_TAG_CODES = {v: k for k, v in CONTROL.items()}


def encode(text, table=None):
    """Encode tagged text (as produced by decode) back to bytes."""
    table = table or {v: k for k, v in DECODE.items()}
    out = bytearray()
    pos = 0
    for m in _TAG.finditer(text):
        for ch in _split(text[pos:m.start()]):
            out.append(table[ch])
        tag = m.group(1)
        if tag in ("NL", "PAGE", "END"):
            out += bytes([0xFF, _TAG_CODES["<%s>" % tag]])
        elif tag.startswith("FF:"):
            out += bytes([0xFF, int(tag[3:], 16)])
        else:
            out.append(int(tag, 16))
        pos = m.end()
    for ch in _split(text[pos:]):
        out.append(table[ch])
    return bytes(out)
