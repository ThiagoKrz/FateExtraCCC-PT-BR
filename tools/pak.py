"""PAK / CMP (IECP) reader+writer - ported from ccc-tl/translation-tools."""
import struct
import os
import sys
import json


class PakEntry:
    __slots__ = ('index', 'path', 'data')

    def __init__(self, index, path, data):
        self.index = index
        self.path = path
        self.data = data


class PakFile:
    """.pak container: u16 count, u16 flag(0x8000 = has 64-byte path headers),
    u32 size per file, align16, then [path(64)] + data for each file."""

    def __init__(self, data):
        self.raw = data
        count, flag = struct.unpack_from('<HH', data, 0)
        self.has_paths = (flag == 0x8000)
        sizes = list(struct.unpack_from('<%dI' % count, data, 4))
        pos = 4 + 4 * count
        pos = (pos + 15) & ~15
        self.header_size = pos
        self.entries = []
        for i in range(count):
            if self.has_paths:
                path = data[pos:pos + 64].split(b'\0')[0].decode('ascii', 'replace')
                pos += 64
            else:
                path = ''
            self.entries.append(PakEntry(i, path, data[pos:pos + sizes[i]]))
            pos += sizes[i]

    def get(self, path):
        for e in self.entries:
            if e.path == path:
                return e
        raise KeyError(path)

    def replace(self, path, new_data):
        for e in self.entries:
            if e.path == path:
                e.data = pad16(new_data)
                return
        raise KeyError(path)

    def build(self):
        """Rebuild the .pak binary from current entries."""
        count = len(self.entries)
        out = bytearray()
        out += struct.pack('<HH', count, 0x8000 if self.has_paths else 0)
        for e in self.entries:
            out += struct.pack('<I', len(e.data))
        while len(out) % 16:
            out += b'\0'
        for e in self.entries:
            if self.has_paths:
                p = e.path.encode('ascii')
                if len(p) > 63:
                    raise ValueError('path too long: %s' % e.path)
                out += p + b'\0' * (64 - len(p))
            out += e.data
        return bytes(out)


def pad16(data):
    r = len(data) % 16
    return data + b'\0' * (16 - r) if r else data


def decompress_cmp(data):
    """IECP / LZSS decompressor."""
    if data[:4] != b'IECP':
        raise ValueError('not a CMP file')
    size = struct.unpack_from('<I', data, 4)[0]
    out = bytearray(size)
    op = 0
    dict_ = bytearray(4096)
    dp = 0xFEE
    pos = 8
    n = len(data)
    while pos < n and op < size:
        ctrl = data[pos]
        pos += 1
        for bit in range(8):
            if op >= size:
                break
            if ctrl & (1 << bit):
                b = data[pos]
                pos += 1
                out[op] = b
                op += 1
                dict_[dp] = b
                dp = (dp + 1) & 0xFFF
            else:
                b1 = data[pos]
                b2 = data[pos + 1]
                pos += 2
                length = (b2 & 0xF) + 2
                offset = ((b2 & 0xF0) << 4) | b1
                for lo in range(length + 1):
                    if op >= size:
                        break
                    b = dict_[(offset + lo) & 0xFFF]
                    out[op] = b
                    op += 1
                    dict_[dp] = b
                    dp = (dp + 1) & 0xFFF
    return bytes(out)


def load_package(path):
    """Read a .pak or .cmp file and return its decompressed PAK bytes."""
    data = open(path, 'rb').read()
    if path.lower().endswith('.cmp') or data[:4] == b'IECP':
        data = decompress_cmp(data)
    return data


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'extract':
        srcdir, outdir = sys.argv[2], sys.argv[3]
        refs = {}
        files = []
        for root, _, names in os.walk(srcdir):
            for nm in names:
                if nm.lower().endswith(('.pak', '.cmp')):
                    files.append(os.path.join(root, nm))
        files.sort()
        n_entries = 0
        collisions = 0
        for i, fp in enumerate(files):
            rel = os.path.relpath(fp, srcdir).replace('\\', '/')
            try:
                pak = PakFile(load_package(fp))
            except Exception as ex:
                print('SKIP %s: %s' % (rel, ex))
                continue
            for e in pak.entries:
                name = e.path or ('__anon/%s/%d' % (os.path.basename(fp), e.index))
                if name.endswith('/'):
                    # entry path names a directory, not a file (matches Kotlin tool behaviour)
                    name = '__dir/%s/%d' % (os.path.basename(fp), e.index)
                refs.setdefault(name, []).append(rel)
                op = os.path.join(outdir, name)
                os.makedirs(os.path.dirname(op), exist_ok=True)
                if os.path.isdir(op):
                    op = os.path.join(outdir, '__dir', os.path.basename(fp), str(e.index))
                    os.makedirs(os.path.dirname(op), exist_ok=True)
                if os.path.exists(op):
                    if open(op, 'rb').read() != e.data:
                        collisions += 1
                    continue
                with open(op, 'wb') as fo:
                    fo.write(e.data)
                n_entries += 1
            if (i + 1) % 200 == 0:
                print('  %d/%d paks' % (i + 1, len(files)), flush=True)
        with open(os.path.join(outdir, 'pak-files.json'), 'w', encoding='utf-8') as fo:
            json.dump(refs, fo, indent=1)
        print('paks=%d unique entries=%d content-collisions=%d' % (len(files), n_entries, collisions))
