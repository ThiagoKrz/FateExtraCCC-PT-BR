"""Redesenha rótulos de interface gravados em texturas (TXB) em PT-BR.

O catálogo (ptbr/graficos/lote*.json) diz, para cada textura, qual trecho do
inglês trocar e por qual texto. A ferramenta mede o texto inglês na arte
original (altura da letra, linha de base, espaçamento, alinhamento) e lê as
cores dele: preenchimento (com degradê por linha), contorno escuro e brilho
colorido em volta, quando existem. O português é desenhado com a mesma
métrica e as mesmas camadas e quantizado para a paleta original. Dimensões,
paleta e tamanho dos arquivos não mudam.

Uso:
  python tools/ui_labels.py --preview PASTA      # PNGs antes/depois, sem ISO
  python tools/ui_labels.py BASE.iso SAIDA.iso   # aplica sobre uma ISO
"""

import argparse
import json
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pak import PakFile  # noqa: E402
from tex import Tex  # noqa: E402
from ui_textures import ChunkedTexture  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
WORK_PAK = ROOT / 'work' / 'pak'
CATALOGS = sorted((ROOT / 'ptbr' / 'graficos').glob('lote*.json'))
BIG = 320                     # tamanho de referência para medir as fontes
FONT_FILES = {
    'quadrada': 'Square721 BT Bold.ttf',
    'quadrada_fina': 'Square721 BT Roman.ttf',
    'quadrada_cond': 'Square721 Cn BT Bold.ttf',
    'segoe': 'segoeui.ttf',
    'segoe_sb': 'seguisb.ttf',
    'segoe_b': 'segoeuib.ttf',
    'verdana': 'verdana.ttf',
    'arial_b': 'arialbd.ttf',
    'serifa_b': 'timesbd.ttf',
    'garamond': 'GARA.TTF',
    'garamond_b': 'GARABD.TTF',
}
MAX_SQUEEZE = 0.62            # compressão horizontal máxima aceita


class Fonts:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.cache = {}

    def sized(self, key, size):
        size = round(size * 4) / 4
        if (key, size) not in self.cache:
            self.cache[key, size] = ImageFont.truetype(
                str(self.directory / FONT_FILES[key]), size)
        return self.cache[key, size]

    def get(self, key):
        return self.sized(key, BIG)


# ---------------------------------------------------------------- métrica ---

def _big_render(text, font):
    """Texto no tamanho de referência. Devolve (máscara 0..1, y da base)."""
    ascent, descent = font.getmetrics()
    width = int(font.getlength(text) + 4 * ascent)
    height = 3 * ascent + descent
    image = Image.new('L', (max(width, 8), height))
    ImageDraw.Draw(image).text((2 * ascent, 2 * ascent), text, font=font,
                               fill=255, anchor='ls')
    return np.asarray(image, dtype=np.float32) / 255.0, 2 * ascent


def _cap_height(font):
    return -font.getbbox('H', anchor='ls')[1]


def natural_width(text, font, cap_px):
    """Largura da tinta (px da textura) sem espaçamento extra."""
    big, _ = _big_render(text, font)
    cols = np.where(big.max(0) > 0)[0]
    return (cols[-1] + 1 - cols[0]) * cap_px / _cap_height(font) if len(cols) else 0


def ink_rows(text, font, cap_px, baseline_y):
    """Linhas (topo, base) ocupadas pela tinta na textura."""
    big, base = _big_render(text, font)
    rows = np.where(big.max(1) > 0)[0]
    k = cap_px / _cap_height(font)
    return baseline_y + (rows[0] - base) * k, baseline_y + (rows[-1] + 1 - base) * k


def render_coverage(text, fonts, key, cap_px, tracking, squeeze, shape, baseline_y, x_left):
    """Cobertura 0..1 do texto no tamanho da textura (shape = (h, w)).

    Sem compressão desenha direto no tamanho final, com o hinting da fonte
    (letra nítida). Com compressão desenha 4x mais largo e reduz só na
    horizontal.
    """
    big_font = fonts.get(key)
    size = cap_px * BIG / _cap_height(big_font)
    ss = 1 if abs(squeeze - 1) < 0.015 else 4
    font = fonts.sized(key, size * ss)
    h, w = shape
    wide = int((w + 16) * ss / squeeze) + 16
    image = Image.new('L', (wide, h * ss))
    draw = ImageDraw.Draw(image)
    x = x_left * ss / squeeze - font.getbbox(text[0], anchor='ls')[0]
    step = tracking * ss / squeeze
    base = round(baseline_y) if ss == 1 else baseline_y * ss
    for ch in text:
        draw.text((round(x), base), ch, font=font, fill=255, anchor='ls')
        x += font.getlength(ch) + step
    if ss != 1:
        image = image.resize((max(1, round(wide * squeeze / ss)), h), Image.Resampling.LANCZOS)
    cov = np.asarray(image, dtype=np.float32)[:, :w] / 255.0
    out = np.zeros(shape, dtype=np.float32)
    out[:, :cov.shape[1]] = cov
    return np.clip(out, 0, 1)


# ------------------------------------------------------------- estilo ---

def _lum(rgb):
    rgb = np.asarray(rgb, dtype=np.float64)
    return rgb[..., 0] * 0.3 + rgb[..., 1] * 0.59 + rgb[..., 2] * 0.11


def fit_original(part, rgba, font):
    """Mede o texto inglês na arte: altura, base, espaçamento e cores."""
    x0, x1, y0, y1 = part['box']
    area = rgba[y0:y1, x0:x1].astype(int)
    alpha = area[..., 3]
    if part.get('fundo') is not None:   # fundo opaco: tinta = cor longe do fundo
        diff = np.abs(area[..., :3] - part['fundo']).sum(-1)
        strong = diff >= part.get('limiar', 0.6 * diff.max())
        visible = diff > 0.05 * diff.max()
    else:
        strong = alpha >= part.get('limiar', min(200, 0.75 * alpha.max()))
        visible = alpha > 0.05 * alpha.max()
    rows = np.where(strong.any(1))[0]
    cols = np.where(strong.any(0))[0]
    if not len(rows):
        raise ValueError(f'Sem texto na área de "{part["en"]}"')
    top, bottom = y0 + rows[0], y0 + rows[-1] + 1
    left, right = x0 + cols[0], x0 + cols[-1] + 1
    en = part['en']
    big, base = _big_render(en, font)
    ink = np.where(big.max(1) > 0)[0]
    cap = _cap_height(font)
    above = (base - ink[0]) / cap
    below = (ink[-1] + 1 - base) / cap
    cap_px = (bottom - top) / (above + below)
    baseline = top + above * cap_px
    natural = natural_width(en, font, cap_px)
    tracking = (right - left - natural) / max(1, len(en) - 1)
    ratio = (right - left) / natural if natural else 1.0

    # --- cores ---
    lum = _lum(area[..., :3])
    bright = strong & (lum >= np.percentile(lum[strong], part.get('percentil', 75)))
    fill = np.median(area[bright][:, :3], axis=0)
    rows_rgb = {}
    for r in range(area.shape[0]):
        if bright[r].sum() >= 2:
            rows_rgb[y0 + r] = np.median(area[r][bright[r]][:, :3], axis=0)
    style = {'fill': fill, 'fill_a': float(np.median(alpha[bright])), 'rows': rows_rgb,
             'outline': None, 'glow': None}
    dark = strong & (lum < 0.6 * _lum(fill))
    if part.get('contorno', bool(dark.sum() > 0.3 * strong.sum())) and dark.any():
        style['outline'] = (np.median(area[dark][:, :3], axis=0),
                            float(np.median(alpha[dark])))
    if part.get('fundo') is None:
        semi = visible & ~strong
        if semi.any():
            semi_rgb = np.median(area[semi][:, :3], axis=0)
            auto = bool(np.abs(semi_rgb - fill).sum() > 90 and semi.sum() > 0.4 * strong.sum())
            if part.get('brilho', auto):
                radius = part.get('raio', float(np.clip(cap_px / 9, 0.8, 2.5)))
                style['glow'] = (semi_rgb, float(np.percentile(alpha[semi], 90)), radius)
    return {'cap_px': cap_px, 'baseline': baseline, 'tracking': tracking, 'ratio': ratio,
            'left': left, 'right': right, 'style': style}


def quantize(pre, palette):
    """RGBA pré-multiplicado -> índice da paleta mais próximo."""
    pal = palette.astype(np.float64)
    pal_pre = pal.copy()
    pal_pre[:, :3] *= pal[:, 3:4] / 255.0
    diff = pre[..., None, :] - pal_pre[None, None, :, :]
    diff[..., 3] *= 1.5
    return np.argmin((diff ** 2).sum(-1), axis=-1).astype(np.uint8)


def _over(dst, rgb, a):
    """Compõe `rgb` (h, w, 3 ou 3) com alfa `a` (0..1) sobre dst pré-multiplicado."""
    a = a[..., None]
    rgb = np.broadcast_to(np.asarray(rgb, dtype=np.float64), dst[..., :3].shape)
    out = dst * (1 - a)
    out[..., :3] += rgb * a
    out[..., 3:] += 255.0 * a
    return out


# ------------------------------------------------------------ rótulos ---

def plan_part(part, rgba, fonts, report):
    """Calcula posição, tamanho e estilo do texto PT de uma parte.

    Se não couber, tenta uma versão mais estreita da fonte (condensada/normal).
    """
    try:
        return _plan_part(part, rgba, fonts, report)
    except ValueError as exc:
        narrower = {'quadrada': 'quadrada_cond', 'quadrada_fina': 'quadrada_cond',
                    'garamond_b': 'garamond'}
        if 'não cabe' not in str(exc) or part['fonte'] not in narrower:
            raise
        narrow = dict(part, fonte=narrower[part['fonte']])
        return _plan_part(narrow, rgba, fonts, report)


def _plan_part(part, rgba, fonts, report):
    font = fonts.get(part['fonte'])
    fit = fit_original(part, rgba, font)
    x0, x1, y0, y1 = part['box']
    pt = part['pt']
    cap_px = fit['cap_px'] * part.get('escala', 1.0)
    baseline = fit['baseline'] + part.get('desce', 0)
    # acentos/cedilha não podem sair da área: desce a linha ou reduz a letra
    top, bottom = ink_rows(pt, font, cap_px, baseline)
    above, below = baseline - top, bottom - baseline       # em px, proporcionais à letra
    if bottom - top > y1 - y0:
        k = (y1 - y0) / (bottom - top)
        cap_px *= k
        above, below = above * k, below * k
    baseline = min(max(baseline, y0 + above), y1 - below)
    avail_left = part.get('x_min', x0)
    avail_right = part.get('x_max', x1)
    gaps = max(1, len(pt) - 1)
    natural = natural_width(pt, font, cap_px)
    if part.get('manter_espaco', False):
        # letras espaçadas de propósito (L O A D): mantém o espaçamento
        stretch, tracking = 1.0, fit['tracking']
    else:
        # fonte nossa mais estreita/larga que a original: corrige a largura
        stretch = float(np.clip(part.get('largura', fit['ratio']), 0.85, 1.3))
        tracking = part.get('espaco', 0.0)
    avail = avail_right - avail_left - 1
    width = natural * stretch + tracking * gaps
    if width > avail and tracking > 0:
        tracking = max(0.0, (avail - natural * stretch) / gaps)
        width = natural * stretch + tracking * gaps
    squeeze = stretch
    if width > avail:
        squeeze = stretch * avail / width
        tracking *= avail / width
        width = avail
    if squeeze < MAX_SQUEEZE:
        raise ValueError(f'"{pt}" não cabe: compressão {squeeze:.2f}')
    align = part.get('alinhar') or _guess_align(fit, x0, x1)
    if align == 'esq':
        x_left = max(fit['left'], avail_left)
        x_left = min(x_left, avail_right - 1 - width)
    elif align == 'dir':
        x_left = max(avail_left, fit['right'] - width)
    else:
        center = part.get('centro', (fit['left'] + fit['right']) / 2)
        x_left = min(max(avail_left, center - width / 2), avail_right - 1 - width)
    x_left = max(avail_left, round(x_left))
    # a letra desenhada no tamanho final (hinting) pode sair mais larga que a
    # medida em alta resolução: confere a tinta real e comprime se preciso
    for _ in range(6):
        cov = render_coverage(pt, fonts, part['fonte'], cap_px, tracking, squeeze,
                              (rgba.shape[0], rgba.shape[1] + 64), baseline, x_left)
        cols = np.where(cov.max(0) > 0.1)[0]
        real_right = cols[-1] + 1 if len(cols) else x_left
        if real_right <= avail_right:
            break
        k = (avail_right - x_left) / max(1, real_right - x_left)
        squeeze *= k * 0.995
        tracking *= k
    if squeeze < MAX_SQUEEZE:
        raise ValueError(f'"{pt}" não cabe: compressão {squeeze:.2f}')
    st = fit['style']
    extras =('+contorno' if st['outline'] is not None else '') + \
             ('+brilho' if st['glow'] is not None else '')
    report.append(f'    "{part["en"]}" -> "{pt}": compressão {squeeze:.2f}, '
                  f'letra {cap_px:.1f}px (orig {fit["cap_px"]:.1f}) {extras}')
    return {'key': part['fonte'], 'cap_px': cap_px, 'tracking': tracking,
            'squeeze': squeeze, 'baseline': baseline, 'x_left': x_left,
            'style': st}


def _guess_align(fit, x0, x1):
    gap_l, gap_r = fit['left'] - x0, x1 - fit['right']
    if abs(gap_l - gap_r) <= 4:
        return 'centro'
    return 'esq' if gap_l < gap_r else 'dir'


def draw_part(pre, plan, part, fonts):
    """Desenha brilho, contorno e preenchimento sobre `pre` (pré-multiplicado)."""
    h, w = pre.shape[:2]
    cov = render_coverage(part['pt'], fonts, plan['key'], plan['cap_px'], plan['tracking'],
                          plan['squeeze'], (h, w), plan['baseline'], plan['x_left'])
    x0, x1, y0, y1 = part['box']
    keep = np.zeros((h, w), dtype=bool)
    keep[y0:y1, part.get('x_min', x0):part.get('x_max', x1)] = True
    cov = np.where(keep, cov, 0)
    st = plan['style']
    out = pre
    if st['glow'] is not None:
        rgb, a, radius = st['glow']
        g = ndimage.gaussian_filter(ndimage.maximum_filter(cov, size=2), radius)
        if g.max() > 0:
            g = np.clip(g / g.max() * 1.6, 0, 1)
        out = _over(out, rgb, np.where(keep, g, 0) * a / 255.0)
    if st['outline'] is not None:
        rgb, a = st['outline']
        out = _over(out, rgb, ndimage.maximum_filter(cov, size=3) * a / 255.0)
    fill = np.broadcast_to(st['fill'], (h, w, 3)).astype(np.float64).copy()
    for y, rgb in st['rows'].items():
        if 0 <= y < h:
            fill[y] = rgb
    out = _over(out, fill, cov * st['fill_a'] / 255.0)
    pre[...] = out


class PlainTexture(Tex):
    """Textura paletada sem swizzle nem tabela de blocos (ex.: plaquinhas)."""

    def canvas(self):
        return self.indices()

    def encode_canvas(self, canvas, transparent):
        self.set_indices(canvas)
        return self.raw


def _visible(rgba):
    out = rgba.astype(int).copy()
    out[out[..., 3] == 0] = 0
    return out


def _visible_rgba(texture):
    """RGBA como o jogo mostra: blocos ausentes (-1) são transparentes."""
    rgba = texture.palette_rgba()[texture.canvas()].astype(int)
    if isinstance(texture, ChunkedTexture):
        side = texture.side
        for pos, value in enumerate(texture.ids):
            if value < 0:
                r, c = divmod(pos, texture.cols)
                rgba[r * side:(r + 1) * side, c * side:(c + 1) * side] = 0
    return _visible(rgba[:texture.height, :texture.width])


def open_texture(data):
    tex = Tex(data)
    if tex.swizzled and tex.cct_present:
        return ChunkedTexture(data)
    if not tex.swizzled and not tex.cct_present:
        return PlainTexture(data)
    raise ValueError('Formato de textura não suportado (swizzle sem tabela de blocos)')


def render_texture(entry_data, parts, fonts, report):
    """Redesenha; se faltar bloco na textura, tenta de novo mais estreito."""
    last = None
    for shrink in (1.0, 0.9, 0.8, 0.72, 0.65, 0.58):
        try:
            return _render_texture(entry_data, parts, fonts, report, shrink)
        except ValueError as exc:
            if 'blocos' not in str(exc) and 'tile' not in str(exc):
                raise
            last = exc
    raise last


def _render_texture(entry_data, parts, fonts, report, shrink):
    texture = open_texture(entry_data)
    palette = texture.palette_rgba()
    original = texture.canvas()
    h, w = texture.height, texture.width
    rgba = palette[original[:h, :w]]
    transparent = np.flatnonzero(palette[:, 3] == 0)
    background = None
    if len(transparent):
        clear = int(transparent[0])
    else:
        # fundo opaco: limpa com a cor mais comum e nunca descarta blocos
        clear = int(np.bincount(original[:h, :w].ravel()).argmax())
        background = palette[clear, :3].astype(int)
    plans = []
    for part in parts:
        part = dict(part)
        part['fundo'] = background
        box = part.get('area') or [0, w, 0, h]
        part['box'] = [box[0], min(box[1], w), box[2], min(box[3], h)]
        if part.get('placa'):
            # texto vazado numa placa: o fundo é a cor mais comum da área
            x0, x1, y0, y1 = part['box']
            idx = int(np.bincount(original[y0:y1, x0:x1].ravel()).argmax())
            part['fundo'] = palette[idx, :3].astype(int)
            part['placa_cor'] = palette[idx].astype(np.float64)
        if shrink < 1:
            # largura útil menor = menos blocos ocupados (a área apagada é a mesma)
            lo = part.get('x_min', part['box'][0])
            hi = part.get('x_max', part['box'][1])
            part['x_min'] = lo
            part['x_max'] = max(lo + 8, int(lo + (hi - lo) * shrink))
        plans.append((part, plan_part(part, rgba, fonts, report)))
    pre = rgba.astype(np.float64)
    pre[..., :3] *= pre[..., 3:4] / 255.0
    blank = np.zeros(4) if background is None else palette[clear].astype(np.float64)
    touched = np.zeros((h, w), dtype=bool)
    for part, _ in plans:
        x0, x1, y0, y1 = part['box']
        pre[y0:y1, x0:x1] = part.get('placa_cor', blank)
        touched[y0:y1, x0:x1] = True
    for part, plan in plans:
        draw_part(pre, plan, part, fonts)
    indices = quantize(pre, palette)
    canvas = original.copy()
    region = canvas[:h, :w]
    region[touched] = indices[touched]
    if background is None:
        region[touched & (pre[..., 3] < 8)] = clear
    data = texture.encode_canvas(canvas, transparent)
    if len(data) != len(entry_data):
        raise ValueError('Tamanho da textura mudou')
    if not np.array_equal(_visible_rgba(open_texture(data)), _visible(palette[canvas[:h, :w]])):
        raise ValueError('Pixels divergentes após codificação')
    return data, palette[canvas[:h, :w]]


# ---------------------------------------------------------- catálogo/ISO ---

def load_catalog():
    labels = {}
    for path in CATALOGS:
        data = json.loads(path.read_text(encoding='utf-8'))
        for txb, textures in data['texturas'].items():
            for index, item in textures.items():
                parts = item['partes'] if 'partes' in item else [item]
                labels.setdefault(txb, {})[int(index)] = [p for p in parts if p.get('pt')]
    return labels


def patch_txb(txb_path, data, labels, fonts, report, previews=None):
    pak = PakFile(data)
    reference = PakFile((WORK_PAK / txb_path).read_bytes())
    for index, parts in sorted(labels.items()):
        if not parts:
            continue
        entry = pak.entries[index]
        if entry.data != reference.entries[index].data:
            raise ValueError(f'{txb_path}[{index}] difere da extração de referência')
        report.append(f'  {txb_path}[{index}]')
        before = open_texture(entry.data)
        try:
            entry.data, after = render_texture(entry.data, parts, fonts, report)
        except ValueError as exc:
            report.append(f'    ERRO: {exc} (textura mantida em inglês)')
            continue
        if previews is not None:
            previews.append((f'{txb_path}[{index}]',
                             before.palette_rgba()[before.canvas()[:before.height, :before.width]],
                             after))
    out = pak.build()
    if len(out) != len(data):
        raise ValueError(f'Tamanho do TXB mudou: {txb_path}')
    return out


def preview_sheet(previews, path, zoom=3):
    rows = [(n, b, a, b.shape[0] * zoom, b.shape[1] * zoom) for n, b, a in previews]
    width = min(max(2 * r[4] + 30 for r in rows) + 10, 3000)
    height = sum(r[3] + 18 for r in rows) + 10
    sheet = Image.new('RGBA', (width, height), (30, 30, 38, 255))
    draw = ImageDraw.Draw(sheet)
    y = 5
    for name, before, after, h, w in rows:
        draw.text((5, y), name, fill=(255, 220, 0, 255))
        for k, img in enumerate((before, after)):
            im = Image.fromarray(img.astype(np.uint8), 'RGBA').resize((w, h), Image.NEAREST)
            sheet.alpha_composite(im, (5 + k * (w + 20), y + 14))
        y += h + 18
    sheet.save(path)


def pak_members(labels):
    refs = json.loads((WORK_PAK / 'pak-files.json').read_text(encoding='utf-8'))
    members = {}
    for txb in labels:
        holders = refs.get(txb) or []
        if len(holders) != 1:
            raise ValueError(f'{txb}: esperado em um único PAK, achado em {holders}')
        members.setdefault(holders[0].split('/')[-1], []).append(txb)
    return members


def patch_pak(original, txbs, labels, fonts, report):
    pak = PakFile(original)
    if pak.build() != original:
        raise ValueError('A estrutura do PAK de origem não é reproduzível')
    for txb in txbs:
        entry = pak.get(txb)
        entry.data = patch_txb(txb, entry.data, labels[txb], fonts, report)
    patched = pak.build()
    if len(patched) != len(original):
        raise ValueError('Tamanho do PAK mudou')
    return patched


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('base_iso', type=Path, nargs='?')
    parser.add_argument('output_iso', type=Path, nargs='?')
    parser.add_argument('--preview', type=Path, help='gera PNGs antes/depois nesta pasta')
    parser.add_argument('--font-dir', type=Path,
                        default=Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts')
    args = parser.parse_args()
    labels = load_catalog()
    fonts = Fonts(args.font_dir)
    report = []
    if args.preview:
        args.preview.mkdir(parents=True, exist_ok=True)
        for txb in labels:
            previews = []
            patch_txb(txb, (WORK_PAK / txb).read_bytes(), labels[txb], fonts, report, previews)
            name = txb.replace('interface/', '').replace('/', '_').replace('.txb', '')
            preview_sheet(previews, args.preview / f'{name}.png')
        print('\n'.join(report))
        print(f'Prévias em {args.preview.resolve()}')
        return
    if not args.base_iso or not args.output_iso:
        parser.error('informe BASE.iso e SAIDA.iso, ou --preview PASTA')
    if args.output_iso.exists():
        parser.error('a ISO de saída já existe')
    from native_text import read_iso_paks, write_iso
    members = pak_members(labels)
    try:
        with TemporaryDirectory(prefix='ccc-labels-', dir=args.output_iso.parent) as directory:
            temporary = Path(directory)
            skipped = set()
            sources = read_iso_paks(args.base_iso, temporary, set(members), skipped)
            for name in sorted(skipped):
                report.append(f'  AVISO: {name} está comprimido no CPK; '
                              f'não aplicado ({", ".join(members[name])})')
            replacements = {
                offset: patch_pak(original, members[name], labels, fonts, report)
                for name, (offset, original) in sources.items()
            }
            write_iso(args.base_iso, args.output_iso, temporary, replacements)
    except (OSError, ValueError) as exc:
        print('\n'.join(report))
        parser.exit(1, f'{exc}\n')
    print('\n'.join(report))
    print(f'ISO verificada: {args.output_iso.resolve()}')


if __name__ == '__main__':
    main()
