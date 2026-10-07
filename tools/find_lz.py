"""Scan the ROM for valid LZSS streams (decoded size == header size, stays inside its bank,
no references before the start). Writes notes/lz_streams.tsv."""
import sys
from pathlib import Path


def try_stream(d, o):
    size = d[o] | d[o + 1] << 8
    n = d[o + 2] | d[o + 3] << 8
    if not (32 <= size <= 0x2000) or not (4 <= n <= size + size // 8 + 2):
        return None
    end = o + 4 + n
    if end > len(d) or (o // 0x4000) != ((end - 1) // 0x4000):
        return None
    out, src, flags, bits = 0, o + 4, 0, 0
    while src < end:
        if bits == 0:
            flags, bits = d[src], 8; src += 1; continue
        bit = flags & 1; flags >>= 1; bits -= 1
        if bit:
            src += 1; out += 1
        else:
            if src + 1 >= end:
                break
            lo, hi = d[src], d[src + 1]; src += 2
            if ((hi >> 4) << 8 | lo) + 1 > out:
                return None
            out += (hi & 0x0F) + 3
        if out > size:
            return None
    return (size, 4 + n) if out == size else None


if __name__ == "__main__":
    d = Path(sys.argv[1] if len(sys.argv) > 1 else "rom/thomas-jp.gbc").read_bytes()
    found, o = [], 0
    while o < len(d) - 4:
        r = try_stream(d, o)
        if r:
            found.append((o, *r)); o += r[1]
        else:
            o += 1
    Path("notes/lz_streams.tsv").write_text("offset\tbank\tgb_addr\tsize\tstream_len\n" + "".join(
        f"{o:#07x}\t{o // 0x4000:#04x}\t{0x4000 + o % 0x4000 if o >= 0x4000 else o:#06x}\t{s}\t{n}\n" for o, s, n in found))
    print(len(found), "streams")
