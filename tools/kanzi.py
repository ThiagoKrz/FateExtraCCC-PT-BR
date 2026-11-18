"""kanzi.bin / ruby.bin glyph table reader+writer.

Layout: u32 count, then count 6-byte entries, padded to 16 bytes.
Entry: [2 bytes: Shift-JIS code][4 bytes: the same character in UTF-8, NUL padded].
Single-byte characters store the code as 00 XX; two-byte ones store it
little-endian (e.g. SJIS 0x81A9 -> bytes A9 81).

The entry's position in the table IS the glyph cell index in font.txb:
cell N lives in texture N // 256, at row (N % 256) // 16, column N % 16,
each cell being 16x16 pixels.
"""
import struct

CELL = 16
CELLS_PER_ROW = 16
CELLS_PER_TEX = 256


class KanziTable:
    def __init__(self, data):
        self.count = struct.unpack_from('<I', data, 0)[0]
        self.entries = []
        for i in range(self.count):
            self.entries.append(data[4 + i * 6: 4 + (i + 1) * 6])

    def code_of(self, i):
        """Return the character this entry maps, as a str (best effort)."""
        e = self.entries[i]
        utf8 = e[2:].split(b'\0')[0]
        if utf8:
            try:
                return utf8.decode('utf-8')
            except UnicodeDecodeError:
                pass
        hi, lo = e[1], e[0]
        if hi == 0:
            return chr(lo)
        return '?'

    def sjis_of(self, i):
        e = self.entries[i]
        if e[0] == 0:
            return e[1]
        return (e[1] << 8) | e[0]

    def index_of_char(self, ch):
        for i in range(self.count):
            if self.code_of(i) == ch:
                return i
        return -1

    def add_single_byte(self, code):
        """Append an entry for a 1-byte code; returns its glyph cell index.

        WARNING: this grows the file. kanzi.bin lives in PRELOAD.pak, and the
        English patch places its native code right after PRELOAD's contents in
        memory at an address hardcoded in the EBOOT - growing the file shifts
        that code and the game crashes on boot. Use set_single_byte instead.
        """
        entry = bytes([0x00, code]) + bytes([code, 0, 0, 0])
        self.entries.append(entry)
        self.count += 1
        return self.count - 1

    def set_single_byte(self, index, code):
        """Repoint an existing entry at a 1-byte code, keeping the file size."""
        self.entries[index] = bytes([0x00, code]) + bytes([code, 0, 0, 0])
        return index

    def build(self):
        out = bytearray(struct.pack('<I', self.count))
        for e in self.entries:
            out += e
        while len(out) % 16:
            out += b'\0'
        return bytes(out)


def cell_rect(index):
    """(texture_index, x, y) of a glyph cell."""
    tex = index // CELLS_PER_TEX
    local = index % CELLS_PER_TEX
    row = local // CELLS_PER_ROW
    col = local % CELLS_PER_ROW
    return tex, col * CELL, row * CELL
