"""Fixed sprite blocks (e.g. the minigame-menu banner): a grid of 8x16 OBJ tiles shown at a
fixed layout. Rendered to / re-encoded from an image 1:1 (no retiling; colour 0 = transparent)."""
from PIL import Image

from screen import bgr555_to_rgb


def obj_palette(pal_bytes, n):
    return [bgr555_to_rgb(pal_bytes[n * 8 + c * 2], pal_bytes[n * 8 + c * 2 + 1]) for c in range(4)]


def block_tiles(first, cols, rows):
    """8x16 sprites numbered left-to-right, top-to-bottom, 2 tiles each."""
    return [[first + 2 * (r * cols + c) for c in range(cols)] for r in range(rows)]


def render_block(vram_bank, grid, pal):
    rows, cols = len(grid), len(grid[0])
    img = Image.new("RGB", (cols * 8, rows * 16))
    for r, line in enumerate(grid):
        for c, t in enumerate(line):
            for half in (0, 1):
                a = (t + half) * 16
                for y in range(8):
                    lo, hi = vram_bank[a + 2 * y], vram_bank[a + 2 * y + 1]
                    for x in range(8):
                        v = ((lo >> (7 - x)) & 1) | (((hi >> (7 - x)) & 1) << 1)
                        img.putpixel((c * 8 + x, r * 16 + half * 8 + y), pal[v])
    return img


def encode_block(img, vram_bank, grid, pal):
    px = img.convert("RGB").load()
    for r, line in enumerate(grid):
        for c, t in enumerate(line):
            for half in (0, 1):
                a = (t + half) * 16
                for y in range(8):
                    lo = hi = 0
                    for x in range(8):
                        col = px[c * 8 + x, r * 16 + half * 8 + y]
                        if col not in pal:
                            raise ValueError(f"pixel {(c * 8 + x, r * 16 + half * 8 + y)} {col} not in OBJ palette")
                        v = pal.index(col)
                        lo |= (v & 1) << (7 - x)
                        hi |= (v >> 1) << (7 - x)
                    vram_bank[a + 2 * y:a + 2 * y + 2] = bytes([lo, hi])
