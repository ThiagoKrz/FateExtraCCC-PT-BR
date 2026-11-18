"""Dump every translatable string from the extracted English game into
editable .po files under ptbr/.

An empty msgstr means "keep the English text", so a partially finished
translation always produces a playable, English-where-untranslated ISO.

Usage:  python tools/dump.py
"""
import os
import sys
import glob

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fatetext
import binfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAK = os.path.join(ROOT, 'work', 'pak')
OUT = os.path.join(ROOT, 'ptbr')


def po_escape(s):
    s = s.replace('\\', '\\\\').replace('"', '\\"')
    s = s.replace('\r', '\\r').replace('\n', '\\n').replace('\t', '\\t')
    return s


def write_po(path, title, source_rel, items):
    """items: list of (ctx, comment, source_text)"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    old = read_po(path) if os.path.exists(path) else {}
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write('# %s\n' % title)
        f.write('# Fonte no jogo: %s\n' % source_rel)
        f.write('# Deixe msgstr "" para manter o texto em ingles.\n')
        f.write('# Nao altere as linhas msgctxt nem os codigos de controle (#CDEF, #RUBS, ...).\n')
        f.write('msgid ""\nmsgstr ""\n'
                '"Content-Type: text/plain; charset=UTF-8\\n"\n'
                '"Language: pt_BR\\n"\n\n')
        for ctx, comment, src in items:
            if comment:
                f.write('#. %s\n' % comment)
            f.write('msgctxt "%s"\n' % po_escape(ctx))
            f.write('msgid "%s"\n' % po_escape(src))
            f.write('msgstr "%s"\n\n' % po_escape(old.get(ctx, '')))


def _unescape(s):
    out = []
    i = 0
    while i < len(s):
        c = s[i]
        if c == '\\' and i + 1 < len(s):
            n = s[i + 1]
            out.append({'n': '\n', 'r': '\r', 't': '\t',
                        '"': '"', '\\': '\\'}.get(n, n))
            i += 2
        else:
            out.append(c)
            i += 1
    return ''.join(out)


def read_po(path):
    """Return {msgctxt: msgstr} for non-empty translations."""
    res = {}
    ctx = None
    cur = None
    buf = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith('msgctxt "'):
                ctx = _unescape(line[9:-1])
                cur = None
            elif line.startswith('msgid "'):
                cur = None
            elif line.startswith('msgstr "'):
                cur = 'str'
                buf = [_unescape(line[8:-1])]
            elif line.startswith('"') and cur == 'str':
                buf.append(_unescape(line[1:-1]))
            elif not line:
                if cur == 'str' and ctx is not None:
                    val = ''.join(buf)
                    if val:
                        res[ctx] = val
                cur = None
                ctx = None
    if cur == 'str' and ctx is not None:
        val = ''.join(buf)
        if val:
            res[ctx] = val
    return res


def dump_story():
    n_files = 0
    n_slots = 0
    index = []
    paths = sorted(glob.glob(os.path.join(PAK, 'field_new', '*', '0000.dat'))) + \
        sorted(glob.glob(os.path.join(PAK, 'field_new', '*', '1000.dat')))
    for p in paths:
        rel = os.path.relpath(p, PAK).replace(os.sep, '/')
        scene = rel.split('/')[1]
        stem = scene if os.path.basename(p) == '0000.dat' else scene + '-1000'
        data = open(p, 'rb').read()
        entries = fatetext.scan_dat(data, rel)
        if not entries:
            continue
        by_loc = {}
        for e in entries:
            by_loc.setdefault(e['textLoc'], []).append(e)
        items = []
        for loc in sorted(by_loc):
            group = by_loc[loc]
            types = ','.join(sorted({g['type'] for g in group}))
            items.append((str(loc), types, group[0]['text']))
        names = [g[2] for g in items if 'locationOrName' in g[1]][:6]
        write_po(os.path.join(OUT, 'historia', stem + '.po'),
                 'Historia - cena %s' % stem, rel, items)
        n_files += 1
        n_slots += len(items)
        index.append((stem, len(items), names))
    return n_files, n_slots, index


def dump_menus():
    n_files = 0
    n_slots = 0
    index = []
    for root, _, names in os.walk(PAK):
        for nm in sorted(names):
            if not nm.endswith('.bin'):
                continue
            p = os.path.join(root, nm)
            rel = os.path.relpath(p, PAK).replace(os.sep, '/')
            data = open(p, 'rb').read()
            entries = binfile.parse(data, utf8=rel in binfile.UTF8_FILES)
            if not entries or not binfile.looks_like_text(entries):
                continue
            items = [(str(i), None, t) for i, (_, t) in enumerate(entries)]
            stem = rel.replace('/', '__')[:-4]
            write_po(os.path.join(OUT, 'menus', stem + '.po'),
                     'Menu / interface - %s' % rel, rel, items)
            n_files += 1
            n_slots += len(items)
            index.append((stem, len(items), [t for _, _, t in items[:3]]))
    return n_files, n_slots, index


def dump_fixed():
    """Fixed-width .bin formats: Secret Gardens, Info Matrix, name entry..."""
    import fixedbin
    # item_param_* is skipped on purpose: the English patch moved its text out
    # into compiled relocation space, so there is no English source to show and
    # no room in the file to put a translation.
    SKIP = {'cmn/item_param_01.bin', 'cmn/item_param_04.bin'}
    GROUP = [
        ('interface/infomatrixex/', 'lore'),
        ('interface/sg/', 'sg'),
    ]
    n_files = 0
    n_slots = 0
    index = []
    for root, _, names in os.walk(PAK):
        for nm in sorted(names):
            if not nm.endswith('.bin'):
                continue
            p = os.path.join(root, nm)
            rel = os.path.relpath(p, PAK).replace(os.sep, '/')
            if rel in SKIP or not fixedbin.file_format(rel):
                continue
            data = open(p, 'rb').read()
            try:
                fmt, (entries, layout) = fixedbin.parse(rel, data)
            except Exception as ex:
                print('  ERRO em %s: %s' % (rel, ex))
                continue
            widths = layout.get('widths', [])
            items = []
            for k, (_, text) in enumerate(entries):
                w = widths[k] if k < len(widths) else None
                note = 'max %d bytes' % (w - 1) if w else None
                items.append((str(k), note, text))
            if not any(t.strip() for _, _, t in items):
                continue
            group = 'menus'
            for prefix, g in GROUP:
                if rel.startswith(prefix):
                    group = g
            stem = rel.replace('/', '__')[:-4]
            write_po(os.path.join(OUT, group, stem + '.po'),
                     'Texto de largura fixa (%s) - %s' % (fmt, rel), rel, items)
            n_files += 1
            n_slots += len(items)
            index.append((group, stem, len(items)))
    return n_files, n_slots, index


def dump_eboot():
    """Strings that live inside EBOOT.BIN itself."""
    import eboot
    p = os.path.join(ROOT, 'work', 'iso', 'PSP_GAME', 'SYSDIR', 'EBOOT.BIN')
    if not os.path.exists(p):
        return 0, 0
    entries = eboot.parse(open(p, 'rb').read())
    items = [(str(i), 'max %d bytes' % (s - 1), t)
             for i, t, s in entries if t.strip()]
    if not items:
        return 0, 0
    write_po(os.path.join(OUT, 'sistema', 'eboot.po'),
             'Textos dentro do executavel (EBOOT.BIN)',
             'PSP_GAME/SYSDIR/EBOOT.BIN', items)
    return 1, len(items)


def main():
    print('Lendo textos de historia (.dat)...')
    sf, ss, sidx = dump_story()
    print('  %d arquivos, %d falas/textos' % (sf, ss))
    print('Lendo textos de menu (.bin)...')
    mf, ms, midx = dump_menus()
    print('  %d arquivos, %d textos' % (mf, ms))
    print('Lendo textos de largura fixa (SG, Info Matrix, ...)...')
    ff, fs, fidx = dump_fixed()
    print('  %d arquivos, %d textos' % (ff, fs))
    print('Lendo textos do executavel (EBOOT.BIN)...')
    ef, es = dump_eboot()
    print('  %d arquivo, %d textos' % (ef, es))

    with open(os.path.join(OUT, '_INDICE.md'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('# Indice da traducao\n\n')
        f.write('Gerado por `tools/dump.py`. Nao edite este arquivo a mao.\n\n')
        f.write('| Grupo | Arquivos | Textos |\n|---|---|---|\n')
        f.write('| historia | %d | %d |\n' % (sf, ss))
        f.write('| menus | %d | %d |\n' % (mf, ms))
        for g in sorted({x[0] for x in fidx}):
            gf = sum(1 for x in fidx if x[0] == g)
            gs = sum(x[2] for x in fidx if x[0] == g)
            f.write('| %s | %d | %d |\n' % (g, gf, gs))
        if ef:
            f.write('| sistema | %d | %d |\n' % (ef, es))
        f.write('| **total** | **%d** | **%d** |\n\n'
                % (sf + mf + ff + ef, ss + ms + fs + es))
        f.write('## menus/\n\n| Arquivo | Textos | Exemplo |\n|---|---|---|\n')
        for stem, cnt, sample in sorted(midx):
            ex = (sample[0] if sample else '').replace('\n', ' ')[:48]
            f.write('| `%s.po` | %d | %s |\n' % (stem, cnt, ex.replace('|', '\\|')))
        f.write('\n## historia/\n\n| Arquivo | Textos | Personagens/locais citados |\n|---|---|---|\n')
        for stem, cnt, names in sorted(sidx):
            f.write('| `%s.po` | %d | %s |\n'
                    % (stem, cnt, ', '.join(n.replace('|', '\\|') for n in names[:5])))
    print('\nIndice: ptbr/_INDICE.md')
    print('Total: %d arquivos, %d textos'
          % (sf + mf + ff + ef, ss + ms + fs + es))


if __name__ == '__main__':
    main()
