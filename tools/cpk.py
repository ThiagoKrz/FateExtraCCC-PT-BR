"""CPK (CRI) reader - ported from ccc-tl/translation-tools CpkFile.kt"""
import struct
import os
import sys

COLUMN_STORAGE_MASK = 0xF0
COLUMN_TYPE_MASK = 0x0F
COLUMN_STORAGE_CONSTANT = 0x30
COLUMN_STORAGE_ZERO = 0x10

T_DATA, T_STRING, T_FLOAT = 0x0B, 0x0A, 0x08
T_8B2, T_8B, T_4B2, T_4B = 0x07, 0x06, 0x05, 0x04
T_2B2, T_2B, T_1B2, T_1B = 0x03, 0x02, 0x01, 0x00

_CONST_SIZE = {T_STRING: 4, T_DATA: 8, T_FLOAT: 4, T_8B2: 8, T_8B: 8,
               T_4B2: 4, T_4B: 4, T_2B2: 2, T_2B: 2, T_1B2: 1, T_1B: 1}


class UtfTable:
    __slots__ = ('table_offset', 'table_size', 'rows_offset', 'string_table_offset',
                 'data_offset', 'name_string', 'columns', 'row_width', 'rows',
                 'schemas', 'base_offset')


class Schema:
    __slots__ = ('type', 'column_name', 'constant_offset', 'name')


class Cpk:
    def __init__(self, path, mode='rb'):
        self.f = open(path, mode)
        self.path = path
        self._strcache = {}
        if self._read(0, 4) != b'CPK ':
            raise ValueError('not a CPK file')
        self.toc_table = self.create_utf_table(0)
        self.toc_offset = self.query(self.toc_table, 0, 'TocOffset')
        self.content_offset = self.query(self.toc_table, 0, 'ContentOffset')
        self.files = self.query(self.toc_table, 0, 'Files')
        if self._read(self.toc_offset, 4) != b'TOC ':
            raise ValueError('no TOC signature')
        self.file_table = self.create_utf_table(self.toc_offset)

    def _read(self, off, n):
        self.f.seek(off)
        return self.f.read(n)

    def _cstr(self, off):
        if off in self._strcache:
            return self._strcache[off]
        self.f.seek(off)
        buf = b''
        while True:
            chunk = self.f.read(64)
            if not chunk:
                break
            i = chunk.find(b'\0')
            if i >= 0:
                buf += chunk[:i]
                break
            buf += chunk
        s = buf.decode('ascii', 'replace')
        self._strcache[off] = s
        return s

    def create_utf_table(self, initial_offset):
        off = initial_offset + 0x10
        f = self.f
        f.seek(off)
        if f.read(4) != b'@UTF':
            raise ValueError('no UTF table at %d' % off)
        t = UtfTable()
        t.table_offset = off
        (t.table_size, t.rows_offset, t.string_table_offset, t.data_offset,
         t.name_string) = struct.unpack('>IIIII', f.read(20))
        t.columns, t.row_width, t.rows = struct.unpack('>HHI', f.read(8))
        t.base_offset = t.string_table_offset + 0x8 + off
        t.schemas = []
        for _ in range(t.columns):
            s = Schema()
            s.type = f.read(1)[0]
            s.column_name = struct.unpack('>I', f.read(4))[0]
            s.constant_offset = -1
            if (s.type & COLUMN_STORAGE_MASK) == COLUMN_STORAGE_CONSTANT:
                s.constant_offset = f.tell()
                f.seek(_CONST_SIZE[s.type & COLUMN_TYPE_MASK], 1)
            s.name = None
            t.schemas.append(s)
        for s in t.schemas:
            s.name = self._cstr(t.base_offset + s.column_name)
        return t

    def _row_values(self, t, i):
        """Read one row -> dict colname -> (value, file_offset_of_value)."""
        f = self.f
        row_offset = t.table_offset + 8 + t.rows_offset + i * t.row_width
        out = {}
        for s in t.schemas:
            data_offset = s.constant_offset if s.constant_offset >= 0 else row_offset
            if (s.type & COLUMN_STORAGE_MASK) == COLUMN_STORAGE_ZERO:
                out[s.name] = (0, -1)
                continue
            f.seek(data_offset)
            tf = s.type & COLUMN_TYPE_MASK
            at = f.tell()
            if tf == T_STRING:
                so = struct.unpack('>I', f.read(4))[0]
                val = self._cstr(t.base_offset + so)
                n = 4
            elif tf == T_DATA:
                do, ds = struct.unpack('>II', f.read(8))
                val = self._read(t.base_offset + do, ds)
                n = 8
            elif tf == T_FLOAT:
                val = struct.unpack('>f', f.read(4))[0]
                n = 4
            elif tf in (T_8B, T_8B2):
                val = struct.unpack('>q', f.read(8))[0]
                n = 8
            elif tf in (T_4B, T_4B2):
                val = struct.unpack('>i', f.read(4))[0]
                n = 4
            elif tf in (T_2B, T_2B2):
                val = struct.unpack('>h', f.read(2))[0]
                n = 2
            elif tf in (T_1B, T_1B2):
                val = struct.unpack('>b', f.read(1))[0]
                n = 1
            else:
                raise ValueError('unknown type %d' % tf)
            out[s.name] = (val, at)
            if s.constant_offset < 0:
                row_offset = at + n
        return out

    def query(self, t, i, name):
        return self._row_values(t, i)[name][0]

    def iter_files(self):
        for i in range(self.files):
            r = self._row_values(self.file_table, i)
            yield {
                'index': i,
                'dir': r['DirName'][0],
                'name': r['FileName'][0],
                'size': r['FileSize'][0],
                'extract_size': r['ExtractSize'][0],
                'offset': r['FileOffset'][0],
                'abs_offset': r['FileOffset'][0] + self.toc_offset,
            }

    def read_file(self, e):
        data = self._read(e['abs_offset'], e['size'])
        if e['extract_size'] > e['size']:
            data = decompress_layla(data, e['extract_size'])
        return data

    def close(self):
        self.f.close()

    # ---- in-place patching (port of CpkFile.patchInPlace) ----

    def patch_in_place(self, patched, data_align=2048, rewrite_cmp_to_pak=True,
                       block_replace=True, log=print):
        """Replace files inside an already-open read-write CPK.

        `patched` maps "<dir>/<name>" -> bytes. New content is written
        uncompressed and the TOC is repointed at it. With `block_replace` the
        space freed by the files being replaced is reused (best fit), which
        keeps the CPK close to its original size; anything that does not fit
        is appended. A .cmp entry is renamed to .pak because we write plain,
        uncompressed PAK data.

        Only run this against a pristine CPK (we always copy the user's
        English GAME.DNS first), never against one already patched.
        """
        f = self.f
        f.seek(0, 2)
        original_len = f.tell()
        insert_at = original_len

        rows = [self._row_values(self.file_table, i) for i in range(self.files)]

        free = []
        if block_replace:
            used = []
            for r in rows:
                rel = '%s/%s' % (r['DirName'][0], r['FileName'][0])
                abs_off = r['FileOffset'][0] + self.toc_offset
                size = r['FileSize'][0]
                if rel in patched:
                    continue
                used.append((abs_off, size))
            used.sort()
            # free space = gaps between the blocks that stay in place,
            # starting after the TOC/content header
            cursor = self.content_offset
            for off, size in used:
                if off > cursor:
                    free.append([cursor, off - cursor])
                cursor = max(cursor, off + size)
                cursor = (cursor + data_align - 1) // data_align * data_align
            free = [b for b in free if b[1] >= data_align]
            log('  reusable free blocks: %d (%.1f MiB)'
                % (len(free), sum(b[1] for b in free) / 1048576.0))

        def allocate(size):
            best = -1
            for idx, (off, length) in enumerate(free):
                if length >= size and (best < 0 or length < free[best][1]):
                    best = idx
            if best < 0:
                return None
            off, length = free[best]
            aligned = (size + data_align - 1) // data_align * data_align
            if length - aligned >= data_align:
                free[best] = [off + aligned, length - aligned]
            else:
                free.pop(best)
            return off

        written = {}
        n_patched = 0
        appended = 0

        for r in rows:
            rel = '%s/%s' % (r['DirName'][0], r['FileName'][0])
            if rel not in patched:
                continue
            blob = patched[rel]
            if rel not in written:
                off = allocate(len(blob))
                if off is None:
                    pad = (-insert_at) % data_align
                    if pad:
                        f.seek(insert_at)
                        f.write(b'\0' * pad)
                        insert_at += pad
                    off = insert_at
                    insert_at += len(blob)
                    appended += len(blob)
                f.seek(off)
                f.write(blob)
                written[rel] = off
            off = written[rel]

            # FileSize / ExtractSize must both equal the new (uncompressed) size
            for col in ('FileSize', 'ExtractSize'):
                at = r[col][1]
                if at < 0:
                    raise ValueError('cannot patch zero-storage column %s' % col)
                f.seek(at)
                f.write(struct.pack('>i', len(blob)))

            at = r['FileOffset'][1]
            f.seek(at)
            f.write(struct.pack('>q', off - self.toc_offset))

            name = r['FileName'][0]
            if rewrite_cmp_to_pak and name.lower().endswith('.cmp'):
                new_name = name[:-4] + '.pak'
                at = r['FileName'][1]
                f.seek(at)
                str_off = struct.unpack('>I', f.read(4))[0]
                f.seek(self.file_table.base_offset + str_off)
                f.write(new_name.encode('ascii') + b'\0')
            n_patched += 1

        f.flush()
        f.seek(0, 2)
        new_len = f.tell()
        log('  patched %d entries (%d unique files); appended %.1f MiB; CPK %d -> %d bytes'
            % (n_patched, len(written), appended / 1048576.0, original_len, new_len))
        return {'entries': n_patched, 'files': len(written),
                'appended': appended, 'orig_len': original_len, 'new_len': new_len}


def decompress_layla(src, extract_size):
    if src[:8] != b'CRILAYLA':
        raise ValueError('not CRILAYLA')
    usize, hsize = struct.unpack('<II', src[8:16])
    out = bytearray(usize + 0x100)
    out[:0x100] = src[16 + hsize: 16 + hsize + 0x100]

    state = {'pos': 16 + hsize - 1, 'pool': 0, 'left': 0}

    def getbits(n):
        v = 0
        while n > 0:
            if state['left'] == 0:
                state['pool'] = src[state['pos']]
                state['pos'] -= 1
                state['left'] = 8
            take = min(state['left'], n)
            v = (v << take) | ((state['pool'] >> (state['left'] - take)) & ((1 << take) - 1))
            state['left'] -= take
            n -= take
        return v

    outpos = len(out) - 1
    end = 0x100
    vle_levels = (2, 3, 5, 8)
    while outpos >= end:
        if getbits(1):
            ref = outpos + getbits(13) + 3
            length = 3
            lvl = 0
            while True:
                bits = vle_levels[lvl] if lvl < 4 else 8
                this = getbits(bits)
                length += this
                if this != (1 << bits) - 1:
                    break
                if lvl < 3:
                    lvl += 1
            for _ in range(length):
                out[outpos] = out[ref]
                outpos -= 1
                ref -= 1
        else:
            out[outpos] = getbits(8)
            outpos -= 1
    return bytes(out)


if __name__ == '__main__':
    cmd = sys.argv[1]
    cpk = Cpk(sys.argv[2])
    if cmd == 'list':
        print('TocOffset=%d ContentOffset=%d Files=%d' % (cpk.toc_offset, cpk.content_offset, cpk.files))
        comp = 0
        exts = {}
        for e in cpk.iter_files():
            if e['extract_size'] > e['size']:
                comp += 1
            ext = os.path.splitext(e['name'])[1].lower()
            exts[ext] = exts.get(ext, 0) + 1
            if e['index'] < 30:
                print('%5d %s/%s  size=%d ext=%d off=%d' %
                      (e['index'], e['dir'], e['name'], e['size'], e['extract_size'], e['abs_offset']))
        print('compressed files: %d' % comp)
        print('extensions:', sorted(exts.items(), key=lambda kv: -kv[1]))
    elif cmd == 'extract':
        outdir = sys.argv[3]
        n = 0
        for e in cpk.iter_files():
            p = os.path.join(outdir, e['dir'], e['name'])
            os.makedirs(os.path.dirname(p), exist_ok=True)
            if os.path.exists(p):
                continue
            with open(p, 'wb') as fo:
                fo.write(cpk.read_file(e))
            n += 1
            if n % 500 == 0:
                print('  %d/%d' % (n, cpk.files), flush=True)
        print('extracted %d files' % n)
