"""Zoomed view of a screen PNG with an 8px tile grid and row/column labels."""
import sys
from PIL import Image, ImageDraw


def gridview(src, out, cols=20, rows=18, z=4):
    im = Image.open(src).convert("RGB").crop((0, 0, cols * 8, rows * 8))
    im = im.resize((im.width * z, im.height * z), Image.NEAREST)
    c = Image.new("RGB", (im.width + 24, im.height + 16), "white")
    c.paste(im, (24, 16))
    d = ImageDraw.Draw(c)
    for x in range(cols + 1):
        d.line([(24 + x * 8 * z, 16), (24 + x * 8 * z, c.height)], fill=(255, 0, 255))
        if x < cols:
            d.text((24 + x * 8 * z + 10, 2), str(x), fill="black")
    for y in range(rows + 1):
        d.line([(24, 16 + y * 8 * z), (c.width, 16 + y * 8 * z)], fill=(255, 0, 255))
        if y < rows:
            d.text((4, 16 + y * 8 * z + 10), str(y), fill="black")
    c.save(out)


if __name__ == "__main__":
    gridview(sys.argv[1], sys.argv[2])
