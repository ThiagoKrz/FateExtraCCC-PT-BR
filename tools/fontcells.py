import sys
from PIL import Image
sys.path.insert(0, 'tools')
from tex import Txb
from kanzi import cell_rect, CELL

FONT = sys.argv[3] if len(sys.argv) > 3 else 'work/font-ptbr/font.txb'
if not __import__('os').path.exists(FONT):
    FONT = 'work/pak/font.txb'
txb = Txb(open(FONT, 'rb').read())
print('fonte:', FONT)
cells = [int(a) for a in sys.argv[1].split(',')]
SC = 12
canvas = Image.new('RGB', (len(cells) * CELL * SC, CELL * SC), (24, 24, 32))
for n, ci in enumerate(cells):
    t, x, y = cell_rect(ci)
    tex = txb.textures[t]
    sub = tex.palette_rgba()[tex.indices()[y:y + CELL, x:x + CELL]]
    im = Image.fromarray(sub, 'RGBA')
    bg = Image.new('RGBA', im.size, (24, 24, 32, 255))
    im = Image.alpha_composite(bg, im).convert('RGB').resize((CELL * SC, CELL * SC), Image.NEAREST)
    canvas.paste(im, (n * CELL * SC, 0))
# 1px separators
px = canvas.load()
for n in range(1, len(cells)):
    for yy in range(canvas.height):
        px[n * CELL * SC, yy] = (200, 40, 40)
canvas.save(sys.argv[2])
print('cells', cells, '->', sys.argv[2])
