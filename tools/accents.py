"""Add the missing pt-BR accented letters to the game font.

The English patch draws accented letters as glyphs bound to unused control
bytes (see fatetext.ACCENTS). This builds the letters Portuguese still needs
by combining the font's own letterforms with diacritics lifted from the
glyphs that already exist, so the new characters match the original style.

New glyphs are written into glyph cells past the end of kanzi.bin's declared
table (those cells hold unreferenced leftovers), and one table entry is
appended per character.

Usage:  python tools/accents.py            # build patched font + report
        python tools/accents.py --preview  # also write a PNG to eyeball
"""
import os
import sys
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fatetext
from tex import Txb
from kanzi import KanziTable, cell_rect, CELL

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAK = os.path.join(ROOT, 'work', 'pak')
OUT = os.path.join(ROOT, 'work', 'font-ptbr')

# --- glyph cells of the source characters (verified against the rendered atlas) ---
BASE = {'a': 58, 'e': 62, 'i': 66, 'o': 72, 'u': 78, 'c': 60, 'n': 71,
        'A': 28, 'C': 30, 'E': 32, 'I': 36, 'O': 42, 'U': 48}
DONOR_ACUTE = 153      # a with acute
DONOR_GRAVE = 157      # e with grave
DONOR_CEDILLA = 161    # C with cedilla
DONOR_TILDE = 107      # full width tilde
DONOR_BASE_ACUTE = 'a'
DONOR_BASE_GRAVE = 'e'
DONOR_BASE_CEDILLA = 'C'

# How to draw each new letter. The control byte each one binds to comes from
# fatetext.PTBR_ACCENTS so the font and the text codec can never disagree.
RECIPES = {
    'ç': ('cedilla', 'c'), 'ã': ('tilde', 'a'), 'õ': ('tilde', 'o'),
    'â': ('circumflex', 'a'), 'ê': ('circumflex', 'e'), 'ô': ('circumflex', 'o'),
    'ú': ('acute', 'u'), 'à': ('grave', 'a'), 'Á': ('acute', 'A'),
    'Í': ('acute', 'I'), 'Ó': ('acute', 'O'), 'Ú': ('acute', 'U'),
    'À': ('grave', 'A'),
}
NEW_CHARS = [(ch, ord(code), RECIPES[ch])
             for code, ch in sorted(fatetext.PTBR_ACCENTS.items())]
_missing = set(RECIPES) - set(fatetext.PTBR_ACCENTS.values())
if _missing:
    raise SystemExit('sem byte de controle para: %s' % ' '.join(sorted(_missing)))

# Glyph cells taken over for the new letters.
#
# kanzi.bin CANNOT change size: it sits in PRELOAD.pak, and the English patch
# loads its native code immediately after PRELOAD's contents, at an address
# baked into the EBOOT's assembly patches. Appending entries shifts that code
# and the game dies on boot with null pointer reads. So instead of adding
# entries we take over existing ones.
#
# These indices are obscure kanji that no text in the game uses - found with
# tools/unusedglyphs.py, which reports 433 such entries.
REUSE_CELLS = [2927, 2928, 2929, 2930, 2931, 2933, 2962,
               2983, 2986, 2991, 3002, 3007, 3038]


def bbox(cell):
    ys, xs = np.nonzero(cell)
    if len(ys) == 0:
        return None
    return ys.min(), ys.max(), xs.min(), xs.max()


class FontEditor:
    def __init__(self):
        self.txb = Txb(open(os.path.join(PAK, 'font.txb'), 'rb').read())
        self.kt = KanziTable(open(os.path.join(PAK, 'kanzi.bin'), 'rb').read())
        self._planes = {i: t.indices() for i, t in self.txb.textures.items()}

    def cell(self, index):
        t, x, y = cell_rect(index)
        return self._planes[t][y:y + CELL, x:x + CELL]

    def write_cell(self, index, data):
        t, x, y = cell_rect(index)
        self._planes[t][y:y + CELL, x:x + CELL] = data

    # --- diacritic extraction -------------------------------------------------

    def extract_diacritics(self):
        """Lift each mark off the glyph that already carries it."""
        marks = {}

        def top_mark(donor_cell, base_cell):
            """Rows above the base letter = the mark, plus its x offset."""
            d = self.cell(donor_cell)
            b = self.cell(base_cell)
            bb = bbox(b)
            top_rows = d[:bb[0], :]          # everything above the base letter
            mb = bbox(top_rows)
            if mb is None:
                raise ValueError('no mark found above base')
            mark = top_rows[mb[0]:mb[1] + 1, mb[2]:mb[3] + 1]
            base_cx = (bbox(b)[2] + bbox(b)[3]) / 2.0
            mark_cx = (mb[2] + mb[3]) / 2.0
            return mark, mark_cx - base_cx

        marks['acute'] = top_mark(DONOR_ACUTE, BASE[DONOR_BASE_ACUTE])
        marks['grave'] = top_mark(DONOR_GRAVE, BASE[DONOR_BASE_GRAVE])

        # cedilla: the part that hangs below the base letter
        d = self.cell(DONOR_CEDILLA)
        b = self.cell(BASE[DONOR_BASE_CEDILLA])
        bb = bbox(b)
        below = d[bb[1] + 1:, :]
        mb = bbox(below)
        ced = below[mb[0]:mb[1] + 1, mb[2]:mb[3] + 1]
        marks['cedilla'] = (ced, (mb[2] + mb[3]) / 2.0 - (bb[2] + bb[3]) / 2.0)

        # tilde: reuse the game's own full-width tilde, squeezed horizontally
        # only. Scaling it in both directions flattens the wave until it reads
        # as a macron, so the height is reduced by merging the two middle rows
        # instead, which keeps the crest and the trough.
        # Both marks are drawn by hand. Scaling the game's full-width tilde down
        # flattens it into a macron, and mirroring the acute gives a caret as
        # wide as the letter, so neither shortcut works at this size.
        F, S, f = 15, 9, 5

        # tilde: três linhas, mas com um pixel de traço por coluna. Em duas
        # linhas a onda some e vira uma barra; com o traço encorpado a onda
        # aparece mas o acento fica pesado demais para a letra. Esparso resolve
        # os dois: crista à esquerda, vale à direita, metade da tinta.
        marks['tilde'] = (np.array([
            [0, F, F, 0, 0, 0, 0],
            [F, 0, 0, F, 0, 0, F],
            [0, 0, 0, 0, F, F, 0],
        ], dtype=np.uint8), 0.0)

        # circumflex: a low, compact apex rather than a tall spike.
        marks['circumflex'] = (np.array([
            [0, f, F, f, 0],
            [F, S, f, S, F],
        ], dtype=np.uint8), 0.0)
        return marks

    # --- composition ----------------------------------------------------------

    def compose(self, mark_name, base_char, marks):
        mark, dx = marks[mark_name]
        base = self.cell(BASE[base_char]).copy()
        bb = bbox(base)

        # Capitals fill y=1..12 and leave only one row of headroom, so the mark
        # would sit on top of the letter. Squeeze the capital just enough to
        # clear the mark while keeping its baseline, which reads far better than
        # letting the two collide.
        if base_char.isupper() and mark_name != 'cedilla':
            need = mark.shape[0]
            baseline = bb[1]
            new_h = baseline - need + 1
            if new_h < bb[1] - bb[0] + 1:
                letter = base[bb[0]:bb[1] + 1, bb[2]:bb[3] + 1]
                img = Image.fromarray((letter.astype(np.float32) / 15 * 255).astype(np.uint8))
                img = img.resize((letter.shape[1], new_h), Image.LANCZOS)
                squeezed = np.clip(np.round(np.array(img) / 255.0 * 15), 0, 15).astype(np.uint8)
                base[:] = 0
                base[baseline - new_h + 1:baseline + 1, bb[2]:bb[3] + 1] = squeezed
                bb = bbox(base)
        out = base

        if mark_name == 'cedilla':
            cx = (bb[2] + bb[3]) / 2.0 + dx
            x0 = int(round(cx - mark.shape[1] / 2.0))
            y0 = bb[1] + 1
        else:
            cx = (bb[2] + bb[3]) / 2.0 + dx
            x0 = int(round(cx - mark.shape[1] / 2.0))
            # sit right on top of the letter; uppercase has less headroom so the
            # mark is allowed to touch it, which is how the stock É is drawn
            y0 = bb[0] - mark.shape[0]
            if y0 < 0:
                y0 = 0

        x0 = max(0, min(CELL - mark.shape[1], x0))
        y0 = max(0, min(CELL - mark.shape[0], y0))
        region = out[y0:y0 + mark.shape[0], x0:x0 + mark.shape[1]]
        np.maximum(region, mark[:region.shape[0], :region.shape[1]], out=region)
        return out

    def build(self):
        marks = self.extract_diacritics()
        if len(REUSE_CELLS) < len(NEW_CHARS):
            raise SystemExit('faltam celulas: %d livres para %d letras'
                             % (len(REUSE_CELLS), len(NEW_CHARS)))
        added = []
        for (ch, code, (mark_name, base_char)), index in zip(NEW_CHARS, REUSE_CELLS):
            glyph = self.compose(mark_name, base_char, marks)
            self.kt.set_single_byte(index, code)
            self.write_cell(index, np.zeros((CELL, CELL), dtype=np.uint8))
            self.write_cell(index, glyph)
            added.append((ch, code, index, mark_name, base_char))
        # push the edited pixel planes back into the textures
        for i, plane in self._planes.items():
            self.txb.textures[i].set_indices(plane)
            self.txb.save_texture(i)
        return added

    def save(self, outdir):
        os.makedirs(outdir, exist_ok=True)
        font = self.txb.build()
        kanzi = self.kt.build()

        # Both files live in PRELOAD.pak and their sizes are load-bearing: the
        # native code is placed right after PRELOAD's contents at an address
        # hardcoded in the EBOOT. One byte of growth crashes the game on boot.
        for name, built in (('font.txb', font), ('kanzi.bin', kanzi)):
            original = os.path.getsize(os.path.join(PAK, name))
            if len(built) != original:
                raise SystemExit(
                    '%s mudou de tamanho (%d -> %d). PRELOAD.pak precisa manter '
                    'o tamanho exato ou o jogo trava no boot.'
                    % (name, original, len(built)))

        with open(os.path.join(outdir, 'font.txb'), 'wb') as f:
            f.write(font)
        with open(os.path.join(outdir, 'kanzi.bin'), 'wb') as f:
            f.write(kanzi)
        print('tamanhos preservados: font.txb e kanzi.bin identicos ao original')


def preview(editor, added, path):
    SC = 12
    n = len(added)
    canvas = Image.new('RGB', (n * CELL * SC, CELL * SC), (24, 24, 32))
    tex = editor.txb.textures[cell_rect(added[0][2])[0]]
    pal = tex.palette_rgba()
    for k, (ch, code, index, _, _) in enumerate(added):
        sub = pal[editor.cell(index)]
        im = Image.fromarray(sub, 'RGBA')
        bg = Image.new('RGBA', im.size, (24, 24, 32, 255))
        im = Image.alpha_composite(bg, im).convert('RGB')
        canvas.paste(im.resize((CELL * SC, CELL * SC), Image.NEAREST), (k * CELL * SC, 0))
    px = canvas.load()
    for k in range(1, n):
        for y in range(canvas.height):
            px[k * CELL * SC, y] = (200, 40, 40)
    canvas.save(path)


def main():
    ed = FontEditor()
    print('tabela original: %d glifos' % ed.kt.count)
    added = ed.build()
    ed.save(OUT)
    print('tabela nova    : %d glifos' % ed.kt.count)
    print()
    print('%-4s %-6s %-7s %s' % ('char', 'byte', 'celula', 'receita'))
    for ch, code, index, mark, base in added:
        print('%-4s 0x%02X   %-7d %s + %s' % (ch, code, index, base, mark))
    print()
    print('gravado em: %s' % OUT)
    if '--preview' in sys.argv:
        p = os.path.join(ROOT, 'work', 'accents_preview.png')
        preview(ed, added, p)
        print('preview   : %s' % p)


if __name__ == '__main__':
    main()
