"""Validate the official dat/pointers.json against our extracted English files."""
import sys
import os
import json
import struct
from collections import Counter

sys.path.insert(0, 'tools')
from fatetext import read_dat_string, decode, scan_dat

TMPL = os.path.join(os.environ['TEMP'], 'claude',
                    'c--Users-Thiago-Desktop-FateExtraCCC-PT-BR',
                    'cfbb774a-3b20-4ef7-8ea5-3aa973fe44fc', 'scratchpad',
                    'tmpl', 'ccc', 'translation')
PAK = os.path.join('work', 'pak')

ptrs = [e for e in json.load(open(os.path.join(TMPL, 'dat', 'pointers.json'), encoding='utf-8')) if e]
print('ponteiros oficiais:', len(ptrs))
folders = sorted({e['f'] for e in ptrs})
print('pastas citadas:', len(folders), folders[:6], '...')

cache = {}


def load(f):
    if f not in cache:
        p = os.path.join(PAK, 'field_new', f, '0000.dat')
        cache[f] = open(p, 'rb').read() if os.path.exists(p) else None
    return cache[f]


ok = 0
bad = 0
missing_file = 0
texts = []
for e in ptrs:
    d = load(e['f'])
    if d is None:
        missing_file += 1
        continue
    p = e['p']
    if p + 4 > len(d):
        bad += 1
        continue
    loc = struct.unpack_from('<I', d, p)[0]
    if loc == 0 or loc % 4 or loc >= len(d):
        bad += 1
        continue
    try:
        raw, _ = read_dat_string(d, loc)
    except EOFError:
        bad += 1
        continue
    t = decode(raw)
    texts.append(t)
    ok += 1

print()
print('resolvidos OK   :', ok)
print('ponteiros ruins :', bad)
print('arquivo ausente :', missing_file)
print('unicos          :', len(set(texts)))
print()
print('--- amostra (3 primeiros, truncados) ---')
for t in texts[:3]:
    print('   ', repr(t[:60]))

# compare with my scanner's coverage
mine = set()
for f in folders:
    d = load(f)
    if d is None:
        continue
    for x in scan_dat(d, 'field_new/%s/0000.dat' % f):
        mine.add(x['text'])
theirs = set(texts)
print()
print('meu scanner  :', len(mine))
print('oficial      :', len(theirs))
print('so no oficial:', len(theirs - mine))
print('so no meu    :', len(mine - theirs))
