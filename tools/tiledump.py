"""Render ROM regions as 2bpp or 1bpp tile sheets (PNG) for visual inspection."""
import sys
from PIL import Image

def tile2bpp(d, o):
    px = []
    for r in range(8):
        lo, hi = d[o + 2 * r], d[o + 2 * r + 1]
        px.append([((lo >> (7 - c)) & 1) | (((hi >> (7 - c)) & 1) << 1) for c in range(8)])
    return px

def tile1bpp(d, o):
    return [[((d[o + r] >> (7 - c)) & 1) * 3 for c in range(8)] for r in range(8)]

def sheet(d, start, length, bpp, cols=32, scale=2):
    size = 16 if bpp == 2 else 8
    n = length // size
    rows = (n + cols - 1) // cols
    img = Image.new("L", (cols * 8, rows * 8), 255)
    pal = [255, 170, 85, 0]
    for t in range(n):
        o = start + t * size
        if o + size > len(d):
            break
        px = (tile2bpp if bpp == 2 else tile1bpp)(d, o)
        for y in range(8):
            for x in range(8):
                img.putpixel(((t % cols) * 8 + x, (t // cols) * 8 + y), pal[px[y][x]])
    return img.resize((img.width * scale, img.height * scale), Image.NEAREST)

if __name__ == "__main__":
    rom, out, start, length, bpp = sys.argv[1], sys.argv[2], int(sys.argv[3], 0), int(sys.argv[4], 0), int(sys.argv[5])
    d = open(rom, "rb").read()
    sheet(d, start, length, bpp).save(out)
