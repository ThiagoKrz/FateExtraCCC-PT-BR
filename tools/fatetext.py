"""Text codec + .dat script scanner for Fate/Extra CCC.

Ported from ccc-tl/translation-tools:
  - tl.util.Util.readDatString / writeDatString
  - tl.extra.ccc.cli.DatScriptJsonDumper
  - tl.extra.ccc.patcher.translation.CccTranslation (accent mapping)
"""
import struct

# The English patch renders accented letters via unused control bytes.
# Source: CccTranslation.getTranslation()
EN_ACCENTS = {
    '': 'Č', '': 'é', '': 'á', '': 'ā',
    '': 'ī', '': 'ä', '': 'è', '': 'ó',
    '': 'ü', '': 'í', '': 'Ç', '': 'ö',
    '': 'É', '	': 'ū', '': 'ṇ',
}

# Letters Portuguese needs that the English font did not have. The glyphs are
# built by tools/accents.py and bound to control bytes that no string in the
# game uses (verified by scanning every extracted text).
# 0x03 is deliberately absent: it does occur in real game strings.
PTBR_ACCENTS = {
    '': 'ç', '': 'ã', '': 'õ', '': 'â',
    '': 'ê', '': 'ô', '': 'ú', '': 'à',
    '': 'Á', '': 'Í', '': 'Ó', '': 'Ú',
    '': 'À',
}

ACCENTS = dict(EN_ACCENTS)
ACCENTS.update(PTBR_ACCENTS)
ACCENTS_REV = {v: k for k, v in ACCENTS.items()}

# Uppercase accents Portuguese still lacks; the encoder degrades these to the
# plain letter rather than emitting a character with no glyph.
FALLBACKS = {'Â': 'A', 'Ã': 'A', 'Ê': 'E', 'Ô': 'O', 'Õ': 'O'}

# Control bytes still unclaimed, if more letters are ever needed.
FREE_CONTROL_BYTES = [b for b in range(0x01, 0x20)
                      if chr(b) not in ACCENTS and b not in (0x03, 0x0A, 0x0D)]


def decode(raw):
    """CP932 bytes -> readable text, with accent control bytes mapped to letters."""
    s = raw.decode('cp932', errors='replace')
    for k, v in ACCENTS.items():
        s = s.replace(k, v)
    return s


def encode(text):
    """Readable text -> CP932 bytes, mapping accented letters back to control bytes."""
    for k, v in FALLBACKS.items():
        text = text.replace(k, v)
    for k, v in ACCENTS_REV.items():
        text = text.replace(k, v)
    return text.encode('cp932')


def read_dat_string(data, at):
    """Read a NUL-terminated, 4-byte-aligned DAT string starting at `at`.

    Mirrors readDatString: consume bytes until a 0x00 lands on a 4-byte
    boundary; interior 0x00 bytes are alignment padding and are dropped.
    """
    pos = at
    out = bytearray()
    n = len(data)
    while True:
        if pos >= n:
            raise EOFError('ran off end reading string at %d' % at)
        ch = data[pos]
        pos += 1
        if ch == 0:
            if pos % 4 == 0:
                break
        else:
            out.append(ch)
    return bytes(out), pos - at


def dat_string_bytes(text):
    """Encode a string the way writeDatString does (payload + 1..4 NUL bytes)."""
    b = encode(text)
    pad = 4 - (len(b) % 4)
    return b + b'\0' * pad


# --- opcode table, ported verbatim from DatScriptJsonDumper.handleOpcode ---
# opcode -> (skip_ints_before_ptr, type, second_ptr_follows)
_SIMPLE = {
    0x00003926: (0, 'text'),
    0x00001530: (0, 'backlog'),
    0x00000126: (2, 'motion'),
    0x00000A26: (1, 'locationOrName'),
    0x00000A30: (4, 'choice'),
    0x00005030: (3, 'inDungeon'),
    0x00005E16: (0, 'popupYesNo'),
    0x00006016: (0, 'popupStd'),
    0x00005316: (0, 'unk_op1653'),
    0x00005016: (0, 'unk_op1650'),
    0x00005916: (1, 'unk_op1659'),
    0x00006316: (1, 'unk_op1663'),
}
_PAIRED = {
    0x00005F16: 'popupYesNo',
    0x00006116: 'popupStd',
    0x00006416: 'popupSaveBeforeQuit',
}
_MEMORY_ACCEPT = ('？？？', '藤村 大河', 'ランサー', 'アーチャー')


def scan_dat(data, dat_name=''):
    """Find every translatable string in a .dat script.

    Returns list of dicts: {type, ptrLoc, textLoc, text}.
    """
    entries = []
    n = len(data)
    pos = 0

    def add(type_, ptr_loc, text_loc, accept_only=None):
        if text_loc == 0 or text_loc % 4 != 0 or text_loc >= n:
            return
        try:
            raw, _ = read_dat_string(data, text_loc)
        except EOFError:
            return
        text = decode(raw)
        if not text.strip() or text == 'TEST':
            return
        if accept_only and text not in accept_only:
            return
        entries.append({'type': type_, 'ptrLoc': ptr_loc,
                        'textLoc': text_loc, 'text': text})

    while pos + 4 <= n:
        op = struct.unpack_from('<I', data, pos)[0]
        pos += 4
        if op in _SIMPLE:
            skip, type_ = _SIMPLE[op]
            pos += 4 * skip
            if pos + 4 > n:
                break
            ptr_loc = pos
            text_loc = struct.unpack_from('<I', data, pos)[0]
            pos += 4
            add(type_, ptr_loc, text_loc)
        elif op in _PAIRED:
            base = _PAIRED[op]
            if pos + 8 > n:
                break
            ptr1 = pos
            loc1 = struct.unpack_from('<I', data, pos)[0]
            pos += 4
            ptr2 = pos
            loc2 = struct.unpack_from('<I', data, pos)[0]
            pos += 4
            add(base + '_line1', ptr1, loc1)
            add(base + '_line2', ptr2, loc2)
        elif op == 0x00000030:
            if pos + 16 > n:
                break
            unk1 = struct.unpack_from('<I', data, pos)[0]
            unk2 = struct.unpack_from('<I', data, pos + 4)[0]
            ptr_loc = pos + 8
            text_loc = struct.unpack_from('<I', data, pos + 8)[0]
            pos += 12
            if unk1 != 0 or unk2 not in (0, 1, 2):
                continue
            # quirk preserved from the original dumper
            if '/068/' in dat_name.replace('\\', '/') and text_loc == 512:
                continue
            add('locationOrName2', ptr_loc, text_loc)
        elif op == 0x00000102:
            if pos + 16 > n:
                break
            mode = struct.unpack_from('<I', data, pos + 8)[0]
            ptr_loc = pos + 12
            text_loc = struct.unpack_from('<I', data, pos + 12)[0]
            pos += 16
            if mode != 0:
                continue
            add('memoryWrite', ptr_loc, text_loc, accept_only=_MEMORY_ACCEPT)
    return entries


def patch_dat(data, patches):
    """Apply {textLoc: new_text} to a .dat, growing the file when needed.

    Strategy from DatTranslationProcessor.patchFile: write in place when the
    new string is no longer than the old one, otherwise append it at the end
    of the file and repoint every pointer that referenced it.
    """
    out = bytearray(data)
    # group pointers by the text location they refer to
    by_loc = {}
    for e in patches['entries']:
        by_loc.setdefault(e['textLoc'], []).append(e['ptrLoc'])

    for text_loc, new_text in sorted(patches['texts'].items()):
        old_raw, old_len = read_dat_string(bytes(out), text_loc)
        new_blob = dat_string_bytes(new_text)
        if len(new_blob) <= old_len:
            out[text_loc:text_loc + len(new_blob)] = new_blob
            # clear any leftover tail of the old string
            for i in range(text_loc + len(new_blob), text_loc + old_len):
                out[i] = 0
        else:
            while len(out) % 4:
                out.append(0)
            new_loc = len(out)
            out += new_blob
            for ptr in by_loc.get(text_loc, []):
                struct.pack_into('<I', out, ptr, new_loc)
    while len(out) % 16:
        out.append(0)
    return bytes(out)
