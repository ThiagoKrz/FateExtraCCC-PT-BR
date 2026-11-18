"""Fixed-width .bin text formats (items, SG, Info Matrix, dungeon select...).

Ported from the matching *BinFilePatcher classes in ccc-tl/translation-tools.
Every one of these stores strings in slots of a fixed byte size, so a
translation that does not fit is rejected instead of corrupting the file.
"""
import struct

from fatetext import decode, encode


class TooLong(ValueError):
    pass


def _read_field(data, off, width):
    raw = data[off:off + width]
    i = raw.find(b'\0')
    if i >= 0:
        raw = raw[:i]
    return decode(raw)


def _write_field(text, width):
    b = encode(text)
    pad = 4 - (len(b) % 4)          # writeDatString always emits 1..4 NULs
    if len(b) + pad > width:
        raise TooLong('%d > %d bytes' % (len(b) + pad, width))
    return b + b'\0' * (width - len(b))


def _align16(buf):
    while len(buf) % 16:
        buf += b'\0'
    return buf


# --- format descriptions -------------------------------------------------
# Each parser returns (entries, layout) where entries is [(slot_id, text)] and
# layout is whatever the writer needs to put the file back together.

def parse_extended(data):
    """u32 count, u32 unk, then count * [u32 index][0x40 text]."""
    count, unk = struct.unpack_from('<2I', data, 0)
    out = []
    pos = 8
    for i in range(count):
        out.append((i, _read_field(data, pos + 4, 0x40)))
        pos += 4 + 0x40
    return out, {'count': count, 'unk': unk, 'raw': data,
                 'widths': [0x40] * count}


def build_extended(entries, layout):
    data = layout['raw']
    buf = bytearray(struct.pack('<2I', layout['count'], layout['unk']))
    pos = 8
    for i, (_, text) in enumerate(entries):
        index = struct.unpack_from('<I', data, pos)[0]
        buf += struct.pack('<I', index)
        buf += _write_field(text, 0x40)
        pos += 4 + 0x40
    return _align16(bytes(buf))


def parse_sg_text(data):
    """Two slots: 0x30 then 0x7D0."""
    widths = (0x30, 0x7D0)
    out = []
    pos = 0
    for i, w in enumerate(widths):
        out.append((i, _read_field(data, pos, w)))
        pos += w
    return out, {'widths': list(widths)}


def build_sg_text(entries, layout):
    buf = bytearray()
    for (_, text), w in zip(entries, layout['widths']):
        buf += _write_field(text, w)
    buf = _align16(bytes(buf))
    if len(buf) > 0x800:
        raise TooLong('arquivo SG maior que 0x800')
    return buf


def parse_sg_named(data):
    """Repeating [4 unk][0x3C text]."""
    out = []
    pos = 0
    i = 0
    while pos + 0x40 <= len(data):
        out.append((i, _read_field(data, pos + 4, 0x3C)))
        pos += 0x40
        i += 1
    return out, {'raw': data, 'widths': [0x3C] * i}


def build_sg_named(entries, layout):
    data = layout['raw']
    buf = bytearray()
    for i, (_, text) in enumerate(entries):
        buf += data[i * 0x40:i * 0x40 + 4]
        buf += _write_field(text, 0x3C)
    return _align16(bytes(buf))


def parse_sg_common(data):
    """Repeating [0x30 text][0x30 unk]."""
    out = []
    pos = 0
    i = 0
    while pos + 0x60 <= len(data):
        out.append((i, _read_field(data, pos, 0x30)))
        pos += 0x60
        i += 1
    return out, {'raw': data, 'widths': [0x30] * i}


def build_sg_common(entries, layout):
    data = layout['raw']
    buf = bytearray()
    for i, (_, text) in enumerate(entries):
        buf += _write_field(text, 0x30)
        buf += data[i * 0x60 + 0x30:i * 0x60 + 0x60]
    return _align16(bytes(buf))


_IMD_WIDTHS = [0x20] * 4 + [0x80] * 10


def parse_infomatrix_d(data):
    """[0x64 header] + 4x0x20 + 10x0x80 + [0xC tail]."""
    out = []
    pos = 0x64
    for i, w in enumerate(_IMD_WIDTHS):
        out.append((i, _read_field(data, pos, w)))
        pos += w
    return out, {'raw': data, 'tail_at': pos, 'widths': list(_IMD_WIDTHS)}


def build_infomatrix_d(entries, layout):
    data = layout['raw']
    buf = bytearray(data[:0x64])
    for (_, text), w in zip(entries, _IMD_WIDTHS):
        buf += _write_field(text, w)
    buf += data[layout['tail_at']:layout['tail_at'] + 0xC]
    return _align16(bytes(buf))


def parse_infomatrix_t(data):
    """[4 header] then NUL-terminated strings, each padded to a 4-byte edge."""
    out = []
    slots = []
    pos = 4
    i = 0
    n = len(data)
    while pos < n:
        start = pos
        end = data.find(b'\0', pos)
        if end < 0:
            break
        text = decode(data[pos:end])
        pos = end
        while pos < n and data[pos] == 0:
            pos += 1
        if not text and pos >= n:
            break
        slots.append((start, pos - start))
        out.append((i, text))
        i += 1
    return out, {'raw': data, 'slots': slots,
                 'widths': [w for _, w in slots]}


def build_infomatrix_t(entries, layout):
    """Keeps every slot at its original size; the file must not grow."""
    data = layout['raw']
    buf = bytearray(data[:4])
    for (_, text), (start, width) in zip(entries, layout['slots']):
        buf += _write_field(text, width)
    buf = _align16(bytes(buf))
    if len(buf) > len(data):
        raise TooLong('infomatrix_t cresceu')
    return buf + b'\0' * (len(data) - len(buf))


def parse_dungeon_select(data):
    """Repeating [0x30 text1][0x30 text2][0x30 unk]."""
    out = []
    pos = 0
    i = 0
    while pos + 0x90 <= len(data):
        out.append((i, _read_field(data, pos, 0x30)))
        out.append((i + 1, _read_field(data, pos + 0x30, 0x30)))
        pos += 0x90
        i += 2
    return out, {'raw': data, 'widths': [0x30] * i}


def build_dungeon_select(entries, layout):
    data = layout['raw']
    buf = bytearray()
    for rec in range(len(entries) // 2):
        t1 = entries[rec * 2][1]
        t2 = entries[rec * 2 + 1][1]
        buf += _write_field(t1, 0x30)
        buf += _write_field(t2, 0x30)
        buf += data[rec * 0x90 + 0x60:rec * 0x90 + 0x90]
    return _align16(bytes(buf))


# item_param records: (record_size, [(name, offset, width), ...])
_ITEM01 = (0xE4, [('nome', 0x00, 0x54), ('texto1', 0x5C, 0x30),
                  ('texto2', 0x8C, 0x30), ('texto3', 0xBC, 0x28)])
_ITEM04 = (0xB8, [('nome', 0x00, 0x50), ('texto1', 0x50, 0x30),
                  ('texto2', 0x80, 0x38)])


def _parse_item(data, spec):
    rec_size, fields = spec
    count = struct.unpack_from('<I', data, 0)[0]
    out = []
    widths = []
    i = 0
    for r in range(count):
        base = 0x10 + r * rec_size
        if base + rec_size > len(data):
            break
        for _, off, width in fields:
            out.append((i, _read_field(data, base + off, width)))
            widths.append(width)
            i += 1
    return out, {'raw': data, 'count': count, 'spec': spec, 'widths': widths}


def _build_item(entries, layout):
    data = layout['raw']
    rec_size, fields = layout['spec']
    buf = bytearray(data)
    k = 0
    for r in range(layout['count']):
        base = 0x10 + r * rec_size
        if base + rec_size > len(data):
            break
        for _, off, width in fields:
            text = entries[k][1]
            buf[base + off:base + off + width] = _write_field(text, width)
            k += 1
    return bytes(buf)


def parse_item01(data):
    return _parse_item(data, _ITEM01)


def build_item01(entries, layout):
    return _build_item(entries, layout)


def parse_item04(data):
    return _parse_item(data, _ITEM04)


def build_item04(entries, layout):
    return _build_item(entries, layout)


# --- which game file uses which format -----------------------------------

FORMATS = {
    'extended': (parse_extended, build_extended),
    'sg_text': (parse_sg_text, build_sg_text),
    'sg_named': (parse_sg_named, build_sg_named),
    'sg_common': (parse_sg_common, build_sg_common),
    'infomatrix_d': (parse_infomatrix_d, build_infomatrix_d),
    'infomatrix_t': (parse_infomatrix_t, build_infomatrix_t),
    'dungeon_select': (parse_dungeon_select, build_dungeon_select),
    'item01': (parse_item01, build_item01),
    'item04': (parse_item04, build_item04),
}


def file_format(rel):
    """Pick the format for a game-relative path, or None if it is not one of these."""
    name = rel.rsplit('/', 1)[-1]
    if rel == 'cmn/item_param_01.bin':
        return 'item01'
    if rel == 'cmn/item_param_04.bin':
        return 'item04'
    if rel in ('interface/nameentry/msg.bin', 'interface/select/i_move.bin'):
        return 'extended'
    if rel == 'interface/dungeonselect/0000.bin':
        return 'dungeon_select'
    if rel == 'interface/sg/0000.bin':
        return 'sg_common'
    if rel.startswith('interface/sg/'):
        return 'sg_text' if '_text' in name else 'sg_named'
    if rel.startswith('interface/infomatrixex/infomatrix_d_'):
        return 'infomatrix_d'
    if rel.startswith('interface/infomatrixex/infomatrix_t_'):
        return 'infomatrix_t'
    return None


def parse(rel, data):
    fmt = file_format(rel)
    if fmt is None:
        return None
    return fmt, FORMATS[fmt][0](data)


def build(fmt, entries, layout):
    return FORMATS[fmt][1](entries, layout)
