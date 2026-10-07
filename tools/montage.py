"""Tile several screenshots into one labelled contact sheet."""
import sys
from PIL import Image, ImageDraw

def montage(paths, out, cols=4):
    ims = [Image.open(p).convert("RGB") for p in paths]
    w, h = ims[0].size
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * w, rows * (h + 12)), "white")
    dr = ImageDraw.Draw(sheet)
    for i, (p, im) in enumerate(zip(paths, ims)):
        x, y = (i % cols) * w, (i // cols) * (h + 12)
        sheet.paste(im, (x, y + 12))
        dr.text((x + 2, y), p.rsplit("/", 1)[-1], fill="black")
    sheet.save(out)

if __name__ == "__main__":
    montage(sys.argv[2:], sys.argv[1])
