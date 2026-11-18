"""Which glyphs in kanzi.bin does no text in the game actually use?

kanzi.bin must keep its exact byte size (the English patch loads its native
code immediately after PRELOAD.pak's contents in memory, at an address baked
into the EBOOT), so new letters have to replace existing entries rather than
be appended. This finds entries that are safe to take over.
"""
import os
import sys
import glob

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fatetext
import binfile
import fixedbin
import eboot
from kanzi import KanziTable

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAK = os.path.join(ROOT, 'work', 'pak')


def collect_used():
    used = set()

    def add(s):
        used.update(s)

    for p in glob.glob(os.path.join(PAK, 'field_new', '*', '*.dat')):
        data = open(p, 'rb').read()
        for e in fatetext.scan_dat(data, p):
            add(e['text'])

    for root, _, names in os.walk(PAK):
        for nm in names:
            if not nm.endswith('.bin'):
                continue
            p = os.path.join(root, nm)
            rel = os.path.relpath(p, PAK).replace(os.sep, '/')
            data = open(p, 'rb').read()
            if fixedbin.file_format(rel):
                try:
                    _, (entries, _) = fixedbin.parse(rel, data)
                    for _, t in entries:
                        add(t)
                except Exception:
                    pass
                continue
            ents = binfile.parse(data)
            if ents and binfile.looks_like_text(ents):
                for _, t in ents:
                    add(t)

    ep = os.path.join(ROOT, 'work', 'iso', 'PSP_GAME', 'SYSDIR', 'EBOOT.BIN')
    if os.path.exists(ep):
        for _, t, _ in eboot.parse(open(ep, 'rb').read()):
            add(t)

    # the native blob holds item text; decode loosely and keep whatever sticks
    hp = os.path.join(PAK, 'hax', 'patch.o')
    if os.path.exists(hp):
        raw = open(hp, 'rb').read()
        cur = bytearray()
        for b in raw:
            if b == 0:
                if len(cur) >= 3:
                    try:
                        add(fatetext.decode(bytes(cur)))
                    except Exception:
                        pass
                cur = bytearray()
            else:
                cur.append(b)
    return used


def main():
    used = collect_used()
    print('caracteres distintos em uso no jogo: %d' % len(used))

    kt = KanziTable(open(os.path.join(PAK, 'kanzi.bin'), 'rb').read())
    unused = []
    for i in range(kt.count):
        ch = kt.code_of(i)
        if ch not in used:
            unused.append((i, ch))
    print('entradas na tabela : %d' % kt.count)
    print('entradas nao usadas: %d' % len(unused))
    print()
    print('as 20 ultimas nao usadas (melhores candidatas, longe do ASCII):')
    for i, ch in unused[-20:]:
        print('   indice %-5d  U+%04X' % (i, ord(ch) if len(ch) == 1 else 0))
    return unused


if __name__ == '__main__':
    main()
