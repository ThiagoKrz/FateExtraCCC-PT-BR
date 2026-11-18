"""Text stored directly inside EBOOT.BIN.

The offsets come from the CCC team's own dump (tools/data/eboot-pointers.json,
taken from ccc-tl/toolkit-template). Each entry is a string slot of a fixed
size: the English patch overwrote these in place, so the offsets still line up
with the patched EBOOT we build on.

The official tools can relocate a string that outgrows its slot by allocating
from spare blocks and rewriting the MIPS instructions that load its address.
We do not do that: a translation that does not fit is reported and that one
entry stays in English, which is safe and needs no assembler.
"""
import os
import json

from fatetext import decode, encode

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data',
                    'eboot-pointers.json')


def load_pointers():
    return [e for e in json.load(open(DATA, encoding='utf-8')) if e]


def parse(data):
    """Return [(index, text, max_bytes)] for every slot."""
    out = []
    for i, e in enumerate(load_pointers()):
        p, s = e['p'], e['s']
        if p + s > len(data):
            continue
        raw = data[p:p + s]
        z = raw.find(b'\0')
        body = raw[:z] if z >= 0 else raw
        out.append((i, decode(body), s))
    return out


def build(data, translations):
    """Apply {index: text}; returns (new_bytes, skipped) with the same length."""
    buf = bytearray(data)
    ptrs = load_pointers()
    skipped = []
    for i, text in translations.items():
        if i >= len(ptrs):
            skipped.append((i, 'indice inexistente'))
            continue
        p, s = ptrs[i]['p'], ptrs[i]['s']
        b = encode(text)
        if len(b) > s - 1:          # keep room for the NUL terminator
            skipped.append((i, 'precisa de %d bytes, cabe %d' % (len(b) + 1, s)))
            continue
        buf[p:p + s] = b + b'\0' * (s - len(b))
    return bytes(buf), skipped
