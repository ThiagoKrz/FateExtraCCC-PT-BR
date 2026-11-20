"""Medição de largura de linha, em pixels, igual à do jogo.

Porte de `TextMeasure`, `CccWidthLimit` e `replaceControlCodesForTextMeasure`
do toolkit oficial (ccc-tl/translation-tools).

A caixa de diálogo tem largura fixa e o jogo não quebra linha sozinho: o que
passar do limite é cortado na tela. Por isso a quebra de linha é
responsabilidade da tradução, e este módulo é a régua.

Uso:  python tools/medida.py            # varre tudo que está traduzido
      python tools/medida.py historia/007
"""
import glob
import os
import re
import sys

ASCII_W = 7      # ASCII e bytes de controle (acentos) medem 7px
WIDE_W = 15      # caracteres de largura cheia medem 15px

# CccWidthLimit.kt
LIMITS = {
    'choice': 350,
    'dialog': 338,
    'dialog_last': 319,
    'inDungeon': 396,
    'infomatrix': 423,
    'narration': 458,
    'narration_last': 442,
    'sg': 415,
}

# quantas linhas cabem na caixa
MAX_LINES = {'dialog': 3, 'choice': 1, 'inDungeon': 2}

# largura cheia: os mesmos caracteres que o TextMeasure oficial trata como 0xF
WIDE_CHARS = set('　—～…お―鷙薗☆♪⑥□△○×人◆→「」※')


def strip_for_measure(text):
    """Remove os códigos de controle, como o jogo faz antes de desenhar."""
    def longest(m):
        return max((g for g in m.groups() if g is not None), key=len, default='')

    t = text
    t = re.sub(r'#SP1[3456]', '～', t)
    t = re.sub(r'#C\d{8}#', '', t)
    t = re.sub(r'#C\d{8,9}', '', t)
    t = re.sub(r'#\[(.*?)\]\[(.*?)\]#', longest, t)
    t = t.replace('#CDEF', '')
    t = re.sub(r'#RUBS.*?#RUBE', '', t)
    t = t.replace('#REND', '')
    t = re.sub(r'#ROFS[-\d]\d{3}', '', t)
    t = re.sub(r'#VAL\d{3}', '_V', t)
    # nomes variáveis são medidos no pior caso, como no toolkit oficial
    t = t.replace('#FAMILY', 'LONG_FAMILY')
    t = t.replace('#GIVEN', 'LONG__GIVEN')
    t = t.replace('#NICK', 'LONG___NICK')
    t = re.sub(r'#SVT\[(.*?)\]\[(.*?)\]\[(.*?)\]\[(.*?)\]#', longest, t)
    t = re.sub(r'#SVT\[(.*?)\]\[(.*?)\]\[(.*?)\]#', longest, t)
    t = t.replace('#SVT', 'LONG__SVT')
    t = re.sub(r'#T\d', '_T__', t)
    t = re.sub(r'#SP\d{2}', '_SP__', t)
    t = re.sub(r'#TITM\d{4}', 'TITM', t)
    t = re.sub(r'#TVAL\d{2}', 'TVAL', t)
    return t.rstrip()


def measure(line):
    """Largura da linha em pixels."""
    return sum(WIDE_W if ch in WIDE_CHARS else ASCII_W for ch in line)


def kind_for(types, rel='', ctx=''):
    """Qual limite aplicar, a partir do comentário `#.` ou do caminho do .po."""
    t = types or ''
    if 'choice' in t:
        return 'choice'
    if 'inDungeon' in t:
        return 'inDungeon'
    if 'text' in t or 'backlog' in t or 'motion' in t:
        return 'dialog'
    if 'infomatrix_t_' in rel and 'max 6143 bytes' in t:
        return 'infomatrix'
    if rel.startswith('sg/interface__sg__sg_') and '_text' in rel and str(ctx) == '1':
        return 'sg'
    if rel == 'menus/interface__dungeon__msg':
        return 'inDungeon'
    if rel == 'menus/interface__osioki__msg':
        return 'choice'
    return None


def check(text, kind):
    """Retorna lista de problemas: (n_linha, largura, limite, motivo)."""
    if kind is None:
        return []
    problems = []
    lines = strip_for_measure(text).split('\n')
    max_lines = MAX_LINES.get(kind)
    if max_lines and len(lines) > max_lines:
        problems.append((0, len(lines), max_lines, 'linhas demais'))
    for i, line in enumerate(lines):
        last = (i == len(lines) - 1)
        if kind == 'dialog':
            limit = LIMITS['dialog_last'] if last and len(lines) > 1 else LIMITS['dialog']
        else:
            limit = LIMITS[kind]
        w = measure(line)
        if w > limit:
            problems.append((i + 1, w, limit, 'linha larga'))
    return problems


def _entries(path):
    txt = open(path, encoding='utf-8').read()
    return re.findall(r'(?:#\. ([^\n]*)\n)?msgctxt "([^"]+)"\nmsgid "(.*)"\nmsgstr "(.*)"', txt)


def _unescape(s):
    return (s.replace('\\n', '\n').replace('\\"', '"')
             .replace('\\t', '\t').replace('\\\\', '\\'))


def sweep(target=None):
    root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ptbr')
    pattern = os.path.join(root, target + '.po') if target else os.path.join(root, '*', '*.po')
    total = 0
    bad = 0
    for path in sorted(glob.glob(pattern)):
        rel = os.path.relpath(path, root).replace(os.sep, '/')[:-3]
        for types, ctx, src, tr in _entries(path):
            if not tr:
                continue
            total += 1
            kind = kind_for(types, rel, ctx)
            problems = check(_unescape(tr), kind)
            if not problems:
                continue
            bad += 1
            print('%s [%s] (%s)' % (rel, ctx, kind))
            for ln, w, limit, why in problems:
                if why == 'linhas demais':
                    print('   %s: %d linhas, cabem %d' % (why, w, limit))
                else:
                    over = (w - limit + ASCII_W - 1) // ASCII_W
                    print('   linha %d: %dpx > %dpx (corte ~%d caractere(s))'
                          % (ln, w, limit, over))
            for i, line in enumerate(_unescape(tr).split('\n')):
                print('      | %s' % line)
    print()
    print('verificados: %d traduzidos | com problema: %d' % (total, bad))
    return bad


if __name__ == '__main__':
    sys.exit(1 if sweep(sys.argv[1] if len(sys.argv) > 1 else None) else 0)
