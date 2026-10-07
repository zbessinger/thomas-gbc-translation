"""LZSS codec used by the game's graphics loader ($00:18A4).

Stream layout:
  u16 header0 (meaning TBD; not used by the decoder), u16 n = number of data bytes that follow.
  Flag byte, LSB first: 1 = literal byte; 0 = back-reference of two bytes lo, hi:
     length   = (hi & 0x0F) + 3            (3..18)
     distance = ((hi >> 4) << 8 | lo) + 1  (1..4096 bytes back in the output)
  Decoding stops once n data bytes (flags included) have been consumed.
"""


def decompress(rom, offset, prefix=0x1000):
    """Returns (data, total_stream_length, header0). The game decodes straight into VRAM, so
    references may reach before the destination; `prefix` zero bytes stand in for that."""
    h0 = rom[offset] | rom[offset + 1] << 8
    n = rom[offset + 2] | rom[offset + 3] << 8
    src, end = offset + 4, offset + 4 + n
    out = bytearray(prefix)
    flags, bits = 0, 0
    while src < end:
        if bits == 0:
            flags, bits = rom[src], 8
            src += 1
            continue
        bit = flags & 1
        flags >>= 1
        bits -= 1
        if bit:
            if src >= end:
                break
            out.append(rom[src]); src += 1
        else:
            if src + 1 >= end:
                break
            lo, hi = rom[src], rom[src + 1]; src += 2
            length, dist = (hi & 0x0F) + 3, ((hi >> 4) << 8 | lo) + 1
            for _ in range(length):
                out.append(out[-dist])
    return bytes(out[prefix:]), 4 + n, h0


def compress(data, header0=None):
    """Greedy LZSS encoder (hash chains on 3-byte prefixes) the game's decoder accepts."""
    from collections import defaultdict
    chains = defaultdict(list)
    out, i, n = bytearray(), 0, len(data)

    def longest(i):
        best_len = best_dist = 0
        limit = min(18, n - i)
        if limit < 3:
            return 0, 0
        for j in reversed(chains.get(data[i:i + 3], ())):
            if i - j > 4096:
                break
            k = 3
            while k < limit and data[j + k] == data[i + k]:
                k += 1
            if k > best_len:
                best_len, best_dist = k, i - j
                if k == limit:
                    break
        return best_len, best_dist

    def advance(i, count):
        for k in range(i, i + count):
            if k + 3 <= n:
                chains[data[k:k + 3]].append(k)
        return i + count

    while i < n:
        flag_pos = len(out); out.append(0); flags = 0
        for bit in range(8):
            if i >= n:
                break
            length, dist = longest(i)
            if length >= 3:
                d = dist - 1
                out += bytes([d & 0xFF, ((d >> 8) << 4) | (length - 3)])
                i = advance(i, length)
            else:
                flags |= 1 << bit
                out.append(data[i])
                i = advance(i, 1)
        out[flag_pos] = flags
    h0 = len(data) if header0 is None else header0
    return bytes([h0 & 0xFF, h0 >> 8, len(out) & 0xFF, len(out) >> 8]) + bytes(out)
