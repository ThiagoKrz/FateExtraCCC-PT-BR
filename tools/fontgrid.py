"""Render a font.txb texture as a PNG so glyph cells can be inspected."""
import sys
import os
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tex import Txb

CELL = 16


def render(txb_path, tex_index, out_png, scale=3, grid=True):
    t = Txb(open(txb_path, 'rb').read())
    tex = t.textures[tex_index]
    idx = tex.indices()
    pal = tex.palette_rgba()
    rgba = pal[idx]
    img = Image.fromarray(rgba, 'RGBA')

    # flatten onto a dark background so anti-aliased white glyphs are visible
    bg = Image.new('RGBA', img.size, (24, 24, 32, 255))
    img = Image.alpha_composite(bg, img).convert('RGB')
    img = img.resize((img.width * scale, img.height * scale), Image.NEAREST)

    if grid:
        px = img.load()
        step = CELL * scale
        for gx in range(0, img.width, step):
            for y in range(img.height):
                px[gx, y] = (200, 40, 40)
        for gy in range(0, img.height, step):
            for x in range(img.width):
                px[x, gy] = (200, 40, 40)
    img.save(out_png)
    print('%s -> %s (%dx%d)' % (txb_path, out_png, img.width, img.height))


if __name__ == '__main__':
    render(sys.argv[1], int(sys.argv[2]), sys.argv[3],
           scale=int(sys.argv[4]) if len(sys.argv) > 4 else 3)
