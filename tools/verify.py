"""Read a built ISO back and confirm what is actually inside it.

Usage: python tools/verify.py output/ccc-ptbr.iso [game/relative/path.bin]
"""
import sys
import os
import struct

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pycdlib
from cpk import Cpk
import pak as pakmod
import binfile
import fatetext

iso_path = sys.argv[1]
target = sys.argv[2] if len(sys.argv) > 2 else 'interface/shop/msg.bin'

tmp = os.path.join('work', '_verify_GAME.DNS')
print('Extraindo GAME.DNS da ISO gerada...')
iso = pycdlib.PyCdlib()
iso.open(iso_path)
with open(tmp, 'wb') as fo:
    iso.get_file_from_iso_fp(fo, iso_path='/PSP_GAME/INSDIR/GAME.DNS')
iso.close()
print('  %d bytes' % os.path.getsize(tmp))

cpk = Cpk(tmp)
by_name = {}
for e in cpk.iter_files():
    by_name.setdefault(e['name'], e)


def read_from_pak(pak_name, member):
    data = cpk.read_file(by_name[pak_name])
    return pakmod.PakFile(data).get(member).data


# --- font table ---
print()
print('--- fonte ---')
kb = read_from_pak('PRELOAD.pak', 'kanzi.bin')
count = struct.unpack_from('<I', kb, 0)[0]
print('kanzi.bin: %d glifos' % count)
codes = {}
for i in range(count):
    e = kb[4 + i * 6: 4 + (i + 1) * 6]
    if e[0] == 0 and e[1] < 0x20:
        codes[e[1]] = i
missing = [c for c in fatetext.PTBR_ACCENTS if ord(c) not in codes]
for code, ch in sorted(fatetext.PTBR_ACCENTS.items()):
    print('  %s  byte 0x%02X  ->  celula %s'
          % (ch, ord(code), codes.get(ord(code), 'AUSENTE')))
print('todos os acentos pt-BR presentes:', not missing)

# --- text ---
print()
print('--- texto de %s ---' % target)
import json
import fixedbin
refs = json.load(open(os.path.join('work', 'pak', 'pak-files.json'), encoding='utf-8'))
holders = refs.get(target)
if not holders:
    print('  arquivo nao mapeado em nenhum pak')
else:
    holder = os.path.basename(holders[0])
    # a .cmp entry is renamed to .pak when we patch it
    if holder.endswith('.cmp'):
        holder = holder[:-4] + '.pak'
    entry = read_from_pak(holder, target)
    fmt = fixedbin.file_format(target)
    if fmt:
        _, (entries, _) = fixedbin.parse(target, entry)
        print('  formato: %s' % fmt)
        rows = [(i, t) for i, t in entries]
    else:
        rows = list(enumerate(t for _, t in binfile.parse(entry)))
    for i, t in rows[:10]:
        flat = t.replace('\n', '\\n')
        if len(flat) > 70:
            flat = flat[:70] + '...'
        print('  [%s] %s' % (i, flat))
cpk.close()
os.remove(tmp)
