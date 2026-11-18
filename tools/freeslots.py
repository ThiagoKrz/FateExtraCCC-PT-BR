"""Which low bytes actually occur inside real game strings?

Only looks at bytes that sit inside extracted text, so the result tells us
which control codes are genuinely free to repurpose as accented letters.
"""
import sys
import os
import glob
from collections import Counter

sys.path.insert(0, 'tools')
import fatetext
import binfile

counts = Counter()
samples = {}

# story scripts: inspect the raw bytes of every string the scanner finds
for p in sorted(glob.glob(os.path.join('work', 'pak', 'field_new', '*', '*.dat'))):
    data = open(p, 'rb').read()
    for e in fatetext.scan_dat(data, p):
        raw, _ = fatetext.read_dat_string(data, e['textLoc'])
        for b in raw:
            if b < 0x20:
                counts[b] += 1
                if b not in samples:
                    samples[b] = (os.path.basename(os.path.dirname(p)), raw[:40])

# menu bins
for root, _, names in os.walk(os.path.join('work', 'pak')):
    for nm in names:
        if not nm.endswith('.bin'):
            continue
        p = os.path.join(root, nm)
        d = open(p, 'rb').read()
        ents = binfile.parse(d)
        if not ents or not binfile.looks_like_text(ents):
            continue
        for _, t in ents:
            for b in fatetext.encode(t):
                if b < 0x20:
                    counts[b] += 1
                    if b not in samples:
                        samples[b] = (nm, t[:30].encode('utf-8', 'replace'))

print('bytes < 0x20 encontrados em texto real:')
print()
ACC = fatetext.ACCENTS
for b in range(0x01, 0x20):
    n = counts.get(b, 0)
    who = ACC.get(chr(b))
    tag = ('acento %s' % who) if who else ('LIVRE' if n == 0 else 'EM USO')
    print('  0x%02X  %-9d %-12s %s' % (b, n, tag, samples.get(b, ('', b''))[0]))

free = [b for b in range(0x01, 0x20)
        if counts.get(b, 0) == 0 and chr(b) not in ACC and b not in (0x0A, 0x0D)]
print()
print('slots realmente livres (%d): %s' % (len(free), ' '.join('0x%02X' % b for b in free)))
