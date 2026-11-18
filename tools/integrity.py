"""Compare a built ISO's CPK against the pristine one.

Every file we did not deliberately patch must come out byte-identical. If any
other file differs, the in-place CPK patcher wrote over live data.

Usage: python tools/integrity.py output/ccc-ptbr.iso
"""
import sys
import os
import hashlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pycdlib
from cpk import Cpk

iso_path = sys.argv[1]
tmp = os.path.join('work', '_integrity.dns')

print('Extraindo GAME.DNS da ISO gerada...')


def extract(iso_path, inner, out_path):
    """Pull a file out of an ISO, with or without the ;1 version suffix."""
    iso = pycdlib.PyCdlib()
    iso.open(iso_path)
    try:
        for candidate in (inner, inner + ';1'):
            try:
                with open(out_path, 'wb') as fo:
                    iso.get_file_from_iso_fp(fo, iso_path=candidate)
                return
            except Exception:
                continue
        raise SystemExit('nao encontrei %s dentro de %s' % (inner, iso_path))
    finally:
        iso.close()


extract(iso_path, '/PSP_GAME/INSDIR/GAME.DNS', tmp)

orig = Cpk(os.path.join('work', 'iso', 'PSP_GAME', 'INSDIR', 'GAME.DNS'))
new = Cpk(tmp)
print('arquivos: original=%d  novo=%d' % (orig.files, new.files))

o = {}
for e in orig.iter_files():
    o['%s/%s' % (e['dir'], e['name'])] = e

changed = []
same = 0
errors = []
checked = 0
for e in new.iter_files():
    rel = '%s/%s' % (e['dir'], e['name'])
    key = rel
    if key not in o and rel.endswith('.pak'):
        key = rel[:-4] + '.cmp'      # we rename .cmp -> .pak when patching
    if key not in o:
        errors.append('novo arquivo inesperado: %s' % rel)
        continue
    a = o[key]
    checked += 1
    # Always compare the bytes. Matching offset and size proves nothing: a
    # patched file that kept its size can land back on its own old offset.
    try:
        da = orig.read_file(a)
        db = new.read_file(e)
    except Exception as ex:
        errors.append('%s: falha ao ler (%s)' % (rel, ex))
        continue
    if da != db:
        changed.append((rel, len(da), len(db)))

orig.close()
new.close()
os.remove(tmp)

print()
print('inalterados (mesmo offset/tamanho): %d' % same)
print('conteudo diferente               : %d' % len(changed))
for rel, la, lb in changed:
    print('   %-44s %d -> %d bytes' % (rel, la, lb))
for e in errors:
    print('   ERRO %s' % e)
