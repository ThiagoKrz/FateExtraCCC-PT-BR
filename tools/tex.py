"""TXB / TEX texture reader+writer.

Ported from ccc-tl/translation-tools TxbFile.kt + TexFile.kt.
Only the path the font uses is implemented: unswizzled, paletted, no CCT.
Pixels are kept as raw palette indices so glyph edits are lossless.
"""
import struct
import numpy as np

import pak as pakmod


class Tex:
    """One texture inside a .txb."""

    def __init__(self, data):
        self.raw = data
        (self.unkA1, self.unkA2, self.unkA3, self.unkA4) = struct.unpack_from('<4I', data, 0)
        (self.tex_type, swz, self.width, self.height,
         self.unk_width, self.unk_height) = struct.unpack_from('<6H', data, 16)
        self.swizzled = (swz == 1)
        self.tex_byte_size, self.tex_offset = struct.unpack_from('<2I', data, 28)
        (self.cct_present, self.unkB2, self.unkB3) = struct.unpack_from('<3I', data, 36)

        if self.tex_type == 4:
            self.bpp = 4
        elif self.tex_type == 5:
            self.bpp = 8
        else:
            raise ValueError('unsupported texture type %d' % self.tex_type)

        self.tex_data_at = 48
        self.tex_bytes = data[48:48 + self.tex_byte_size]

        p = 48 + self.tex_byte_size
        self.pal_mode, self.pal_colors = struct.unpack_from('<2H', data, p)
        self.pal_byte_size, self.unkP2, self.unkP3 = struct.unpack_from('<3I', data, p + 4)
        color_size = 4 if self.pal_mode == 3 else 2
        self.pal_at = p + 16
        self.pal_bytes = data[self.pal_at:self.pal_at + self.pal_colors * color_size]
        self.color_size = color_size

    def indices(self):
        """Return an (height, width) array of palette indices."""
        if self.swizzled or self.cct_present:
            raise NotImplementedError('only unswizzled, no-CCT textures are supported')
        w, h = self.width, self.height
        if self.bpp == 8:
            a = np.frombuffer(self.tex_bytes, dtype=np.uint8)
            return a[:w * h].reshape(h, w).copy()
        buf = np.frombuffer(self.tex_bytes, dtype=np.uint8)
        lo = buf & 0x0F
        hi = buf >> 4
        out = np.empty(buf.size * 2, dtype=np.uint8)
        out[0::2] = lo
        out[1::2] = hi
        return out[:w * h].reshape(h, w).copy()

    def set_indices(self, arr):
        """Write an (height, width) index array back into the texture bytes."""
        h, w = arr.shape
        if (w, h) != (self.width, self.height):
            raise ValueError('size mismatch: got %dx%d, expected %dx%d'
                             % (w, h, self.width, self.height))
        flat = arr.reshape(-1).astype(np.uint8)
        if self.bpp == 8:
            packed = flat.tobytes()
        else:
            if flat.size % 2:
                flat = np.append(flat, 0)
            packed = ((flat[1::2] << 4) | (flat[0::2] & 0x0F)).astype(np.uint8).tobytes()
        if len(packed) > self.tex_byte_size:
            raise ValueError('packed data larger than original texture block')
        packed = packed + b'\0' * (self.tex_byte_size - len(packed))
        self.raw = self.raw[:48] + packed + self.raw[48 + self.tex_byte_size:]
        self.tex_bytes = packed

    def palette_rgba(self):
        """Decode the palette to an (n, 4) uint8 RGBA array."""
        n = self.pal_colors
        b = self.pal_bytes
        out = np.zeros((n, 4), dtype=np.uint8)
        if self.color_size == 4:
            a = np.frombuffer(b, dtype=np.uint8).reshape(n, 4)
            return a.copy()
        vals = np.frombuffer(b, dtype='<u2')[:n]
        if self.pal_mode == 0:      # RGBA5650
            out[:, 0] = ((vals & 0x1F) * 255 // 31)
            out[:, 1] = (((vals >> 5) & 0x3F) * 255 // 63)
            out[:, 2] = (((vals >> 11) & 0x1F) * 255 // 31)
            out[:, 3] = 255
        elif self.pal_mode == 1:    # RGBA5551
            out[:, 0] = ((vals & 0x1F) * 255 // 31)
            out[:, 1] = (((vals >> 5) & 0x1F) * 255 // 31)
            out[:, 2] = (((vals >> 10) & 0x1F) * 255 // 31)
            out[:, 3] = np.where((vals >> 15) & 1, 255, 0)
        else:                       # RGBA4444
            out[:, 0] = ((vals & 0xF) * 17)
            out[:, 1] = (((vals >> 4) & 0xF) * 17)
            out[:, 2] = (((vals >> 8) & 0xF) * 17)
            out[:, 3] = (((vals >> 12) & 0xF) * 17)
        return out


class Txb:
    """A .txb file: a PAK whose entries are textures."""

    def __init__(self, data):
        self.pak = pakmod.PakFile(data)
        self.textures = {}
        for i, e in enumerate(self.pak.entries):
            if not e.data:
                continue
            try:
                self.textures[i] = Tex(e.data)
            except Exception:
                pass

    def save_texture(self, index):
        self.pak.entries[index].data = self.textures[index].raw

    def build(self):
        return self.pak.build()


if __name__ == '__main__':
    import sys
    t = Txb(open(sys.argv[1], 'rb').read())
    print('entradas no txb:', len(t.pak.entries), ' texturas:', sorted(t.textures))
    for i, tex in sorted(t.textures.items()):
        print('  tex %-3d %4dx%-4d bpp=%d swizzled=%s cct=%d pal=%d cores=%d'
              % (i, tex.width, tex.height, tex.bpp, tex.swizzled,
                 tex.cct_present, tex.pal_mode, tex.pal_colors))
