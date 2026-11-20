"""Gera ptbr/graficos/lote4-aberturas.json a partir da planilha revisada
Fate_Extra_CCC_Lote4_Aberturas.xlsx (usa a coluna "Sua revisão" quando preenchida).

Uso: python tools/lote4_planilha.py
"""
import sys, json
sys.path.insert(0, 'tools')
import numpy as np
from openpyxl import load_workbook
from pak import PakFile
from ui_labels import open_texture

ws = load_workbook('Fate_Extra_CCC_Lote4_Aberturas.xlsx')['Tradução']
cache = {}
def tex(arq, idx):
    if arq not in cache:
        cache[arq] = PakFile(open(f'work/pak/interface/poem/{arq}.txb', 'rb').read())
    t = open_texture(cache[arq].entries[idx].data)
    return t, t.palette_rgba()[t.canvas()[:t.height, :t.width]][..., 3].astype(int)

def splits(alpha, n):
    """n-1 linhas de corte: a linha com menos tinta perto de cada divisão."""
    ink = (alpha >= 0.5 * alpha.max()).sum(1)
    rows = np.where(ink > 0)[0]
    top, bot = rows[0], rows[-1] + 1
    cuts = []
    for k in range(1, n):
        guess = top + (bot - top) * k // n
        lo, hi = max(top, guess - 6), min(bot, guess + 7)
        cuts.append(int(lo + np.argmin(ink[lo:hi])))
    return cuts

T = {}
for row in ws.iter_rows(min_row=2, values_only=True):
    n, capit, arq, idx, tipo, en, pt, acao, obs, rev = row
    if acao != 'Traduzir':
        continue
    pt = rev or pt
    t, alpha = tex(arq, idx)
    w, h = t.width, t.height
    txb = f'interface/poem/{arq}.txb'
    if tipo == 'Rótulo':
        item = {'en': en, 'pt': pt, 'fonte': 'quadrada'}
    elif tipo.startswith('Título'):
        cut = splits(alpha, 2)[0]
        item = {'partes': [{'en': en, 'pt': pt, 'fonte': 'quadrada_fina', 'area': [0, w, cut, h], 'alinhar': 'esq'}]}
    else:
        el, pl = en.split('\n'), pt.split('\n')
        assert len(el) == len(pl), (arq, idx)
        if len(el) == 1:
            item = {'en': en, 'pt': pt, 'fonte': 'garamond', 'percentil': 90, 'contorno': False, 'brilho': True}
        else:
            cuts = [0] + splits(alpha, len(el)) + [h]
            item = {'partes': [{'en': a, 'pt': b, 'fonte': 'garamond', 'percentil': 90, 'contorno': False, 'brilho': True, 'area': [0, w, cuts[k], cuts[k + 1]],
                                'alinhar': 'centro'} for k, (a, b) in enumerate(zip(el, pl))]}
    T.setdefault(txb, {})[str(idx)] = item
cat = {'descricao': ('Lote 4 de texturas: aberturas de capítulo (cpt_00 a cpt_08), poema final (poem_ex_tex) e '
                     'tradução dos títulos de capítulo. Gerado da planilha aprovada Fate_Extra_CCC_Lote4_Aberturas.xlsx. '
                     'Kanji e subtítulo estilizado dos títulos, - BAD END. - e os títulos de poem.txb ficam como na arte original.'),
       'texturas': T}
json.dump(cat, open('ptbr/graficos/lote4-aberturas.json', 'w', encoding='utf-8', newline=''), ensure_ascii=False, indent=1)
print(sum(len(v) for v in T.values()), 'texturas')
