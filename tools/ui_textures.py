"""Read and replace pixel indices in the game's swizzled UI texture chunks.

Chunk layout follows ccc-tl/translation-tools' TexFile and PalettedUnswizzler.
"""

import struct

import numpy as np

from tex import Tex


class ChunkedTexture(Tex):
    """Paletted TEX with a chunk-composition table, as used by the CCC UI."""

    def __init__(self, data):
        super().__init__(data)
        if not self.swizzled or not self.cct_present:
            raise ValueError('Expected a swizzled TEX with a chunk table')
        self.table_at = self.pal_at + len(self.pal_bytes)
        self.cols, self.rows, count, self.side, self.unique = struct.unpack_from(
            '<IIHhH', data, self.table_at)
        if self.side not in (16, 32):
            raise ValueError(f'Unsupported chunk size: {self.side}')
        self.stride = self.side * self.bpp // 8
        self.chunk_bytes = self.stride * self.side
        if self.stride % 16 or len(self.tex_bytes) != self.unique * self.chunk_bytes:
            raise ValueError('Invalid chunk storage size')
        entries_at = self.table_at + 20
        self.ids = np.full(self.cols * self.rows, -1, dtype=np.int16)
        for index in range(len(self.ids)):
            if count == 0:
                break
            value, = struct.unpack_from('<h', data, entries_at + 2 * index)
            if not -1 <= value < self.unique:
                raise ValueError(f'Invalid chunk index: {value}')
            self.ids[index] = value
            count -= value != -1
        if count:
            raise ValueError('Invalid chunk count')
        self.chunks = self._unpack()

    def _unpack(self):
        blocks = np.frombuffer(self.tex_bytes, dtype=np.uint8).reshape(
            self.unique, self.side // 8, self.stride // 16, 8, 16)
        packed = blocks.transpose(0, 1, 3, 2, 4).reshape(self.unique, self.side, self.stride)
        if self.bpp == 8:
            return packed
        indices = np.empty((self.unique, self.side, self.side), dtype=np.uint8)
        indices[:, :, ::2] = packed & 15
        indices[:, :, 1::2] = packed >> 4
        return indices

    def canvas(self):
        tiles = np.zeros((len(self.ids), self.side, self.side), dtype=np.uint8)
        assigned = self.ids >= 0
        tiles[assigned] = self.chunks[self.ids[assigned]]
        return tiles.reshape(self.rows, self.cols, self.side, self.side).transpose(
            0, 2, 1, 3).reshape(self.rows * self.side, self.cols * self.side)

    def update_canvas(self, canvas):
        if canvas.shape != (self.rows * self.side, self.cols * self.side):
            raise ValueError('Canvas dimensions differ from the original TEX')
        tiles = canvas.reshape(self.rows, self.side, self.cols, self.side).transpose(
            0, 2, 1, 3).reshape(len(self.ids), self.side, self.side)
        chunks = self.chunks.copy()
        changes = {}
        for index, tile in zip(self.ids, tiles, strict=True):
            if index < 0:
                if tile.any():
                    raise ValueError('Replacement needs a tile missing from the original texture')
                continue
            previous = changes.setdefault(index, tile)
            if not np.array_equal(previous, tile):
                raise ValueError('Replacement assigns different pixels to a shared chunk')
            chunks[index] = tile
        return self._encode(chunks, self.ids, self.raw)

    def _encode(self, chunks, ids, raw):
        packed = chunks if self.bpp == 8 else chunks[:, :, ::2] | (chunks[:, :, 1::2] << 4)
        swizzled = packed.reshape(self.unique, self.side // 8, 8, self.stride // 16, 16)
        payload = swizzled.transpose(0, 1, 3, 2, 4).tobytes()
        out = bytearray(raw[:48] + payload + raw[48 + len(self.tex_bytes):])
        struct.pack_into('<H', out, self.table_at + 8, int((ids >= 0).sum()))
        for index, value in enumerate(ids):
            struct.pack_into('<h', out, self.table_at + 20 + 2 * index, int(value))
        return bytes(out)

    def relayout(self, canvas, transparent):
        """Encode `canvas` with a fresh chunk table, keeping the byte size.

        Tiles made only of `transparent` pixels become -1 (not stored), equal
        tiles share one chunk. Fails if more distinct tiles than the original
        chunk storage are needed.
        """
        if canvas.shape != (self.rows * self.side, self.cols * self.side):
            raise ValueError('Canvas dimensions differ from the original TEX')
        tiles = canvas.reshape(self.rows, self.side, self.cols, self.side).transpose(
            0, 2, 1, 3).reshape(len(self.ids), self.side, self.side)
        chunks = np.zeros_like(self.chunks)
        ids = np.full(len(self.ids), -1, dtype=np.int16)
        seen = {}
        for position, tile in enumerate(tiles):
            if np.isin(tile, transparent).all():
                continue
            key = tile.tobytes()
            if key not in seen:
                if len(seen) >= self.unique:
                    raise ValueError(f'Precisa de mais de {self.unique} blocos distintos')
                seen[key] = len(seen)
                chunks[seen[key]] = tile
            ids[position] = seen[key]
        return self._encode(chunks, ids, self.raw)

    def encode_canvas(self, canvas, transparent):
        """Keep the original chunk table when possible, else relayout."""
        try:
            return self.update_canvas(canvas)
        except ValueError:
            return self.relayout(canvas, transparent)
