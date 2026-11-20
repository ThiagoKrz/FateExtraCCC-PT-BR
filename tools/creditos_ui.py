"""Insere a logo do Fate Café na tela de créditos da tradução (staffroll_03.txb #4)."""

from pathlib import Path

import numpy as np
from PIL import Image

from pak import PakFile
from ui_textures import ChunkedTexture


ROOT = Path(__file__).resolve().parents[1]
LOGO_PATH = ROOT / 'ptbr/graficos/fate_cafe_logo.png'
STAFFROLL_REL = 'interface/staffroll/staffroll_03.txb'
STAFFROLL_TEX_INDEX = 4


def _composite_logo_rgba8888(texture, logo_path, shift_left=46, logo_size=114, logo_x=352):
    """Desloca o bloco original à esquerda e insere a logo colorida nos slots livres da paleta."""
    if texture.bpp != 8 or texture.color_size != 4:
        raise ValueError('Esperada textura 8bpp RGBA8888 para os créditos')

    pal = texture.palette_rgba().copy()
    canvas = texture.canvas().copy()

    used = set(int(i) for i in np.unique(canvas))
    free = [i for i in range(len(pal)) if i not in used]
    if len(free) < 32:
        raise ValueError(f'Poucos slots livres na paleta dos créditos ({len(free)})')

    # Desloca os créditos originais (CCC TRANSLATION TEAM) para a esquerda, preservando 100% dos pixels
    shifted = np.zeros_like(canvas)
    shifted[:, :texture.width - shift_left] = canvas[:, shift_left:]

    logo = Image.open(logo_path).convert('RGBA').resize(
        (logo_size, logo_size), Image.Resampling.LANCZOS)
    arr = np.asarray(logo)
    alpha = arr[:, :, 3]

    # Reserva slots para RGB opaco + alguns níveis semitransparentes para suavizar a borda circular
    edge_steps = 8
    n_opaque = min(120, len(free) - edge_steps)
    opaque_slots = free[:n_opaque]
    edge_slots = free[n_opaque:n_opaque + edge_steps]

    logo_q = logo.convert('RGB').quantize(colors=n_opaque, method=Image.Quantize.MEDIANCUT)
    q_pal = np.array(logo_q.getpalette()[:n_opaque * 3], dtype=np.uint8).reshape(-1, 3)
    q_idx = np.asarray(logo_q)

    for k in range(len(q_pal)):
        pal[opaque_slots[k]] = [q_pal[k, 0], q_pal[k, 1], q_pal[k, 2], 255]

    # Cor média da borda externa do círculo (creme claro) com rampa de alfa
    border_rgb = np.array([255, 245, 232], dtype=np.uint8)
    for k, slot in enumerate(edge_slots):
        a = int(round((k + 1) * 255 / (edge_steps + 1)))
        pal[slot] = [border_rgb[0], border_rgb[1], border_rgb[2], a]

    logo_y = (texture.height - logo_size) // 2
    for y in range(logo_size):
        for x in range(logo_size):
            a = int(alpha[y, x])
            if a >= 220:
                shifted[logo_y + y, logo_x + x] = opaque_slots[int(q_idx[y, x])]
            elif a >= 24:
                step = min(edge_steps - 1, a * edge_steps // 220)
                shifted[logo_y + y, logo_x + x] = edge_slots[step]

    encoded = bytearray(texture.update_canvas(shifted))
    pal_bytes = pal.astype(np.uint8).tobytes()
    if len(pal_bytes) != len(texture.pal_bytes):
        raise ValueError('Tamanho da paleta divergente')
    encoded[texture.pal_at:texture.pal_at + len(pal_bytes)] = pal_bytes
    return bytes(encoded), shifted, pal


def patch_staffroll_txb(source_bytes, logo_path=LOGO_PATH):
    """Retorna os bytes do staffroll_03.txb com a logo do Fate Café inserida."""
    txb = PakFile(source_bytes)
    entry = txb.entries[STAFFROLL_TEX_INDEX]
    texture = ChunkedTexture(entry.data)
    updated, expected_canvas, expected_pal = _composite_logo_rgba8888(texture, logo_path)
    if len(updated) != len(entry.data):
        raise ValueError('Tamanho da textura de créditos mudou')
    verify = ChunkedTexture(updated)
    if not np.array_equal(verify.canvas(), expected_canvas):
        raise ValueError('Pixels divergentes após codificação dos créditos')
    if not np.array_equal(verify.palette_rgba(), expected_pal):
        raise ValueError('Paleta divergente após codificação dos créditos')
    entry.data = updated
    return txb.build()


def patched_credits():
    """Retorna {rel_path: bytes} para integração direta em tools/build.py."""
    if not LOGO_PATH.exists():
        return {}
    src = ROOT / 'work/pak' / STAFFROLL_REL
    if not src.exists():
        return {}
    return {STAFFROLL_REL: patch_staffroll_txb(src.read_bytes(), LOGO_PATH)}
