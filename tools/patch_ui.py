"""Localize the opening notice and System menu art in a built CCC ISO."""

import argparse
import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from native_text import read_iso_paks, write_iso
from pak import PakFile
from ui_textures import ChunkedTexture


CATALOG = Path(__file__).resolve().parents[1] / 'ptbr/graficos/abertura-e-sistema.json'
LOGO_PATH = Path(__file__).resolve().parents[1] / 'ptbr/graficos/fate_cafe_logo.png'
NOTICE = 'interface/logo/0000.txb'
SAVE_MENU = 'interface/save/0000.txb'
SAVE_FILES = 'interface/save/0001.txb'
MEMBERS = {'title.pak': (NOTICE,), 'savemenu.pak': (SAVE_MENU, SAVE_FILES)}
SOURCE_HASHES = {
    NOTICE: 'ca8d5c7c5876958081a9d4b3b00dbf62bb11876b147b414b49a6e6f7879d23fb',
    SAVE_MENU: '7f3ead1bed8cde746bef189b017e230d1094bfa1411360d2a7885df50cd33ee5',
    SAVE_FILES: '7d7434273fd25e0311180694342ae7e38921ff9e9ad216cfb9fbb4922edf3187',
}
LABELS = {
    SAVE_MENU: {
        6: 'SAVE', 7: 'LOAD', 8: 'DELETE', 9: 'OPTION', 11: 'RETURN TO TITLE',
        12: 'SAVES DATA', 13: 'LOAD DATA', 14: 'DELETE', 15: 'OPTION',
        17: 'RETURN TITLE', 19: 'SYSTEM',
    },
    SAVE_FILES: {
        2: 'FILES', 7: 'SAVE', 8: 'DELETE', 9: 'SAVES DATA', 10: 'DELETE', 11: 'SYSTEM',
    },
}
SCALE = 6


def glyph_mask(text, font):
    left, top, right, bottom = font.getbbox(text)
    mask = Image.new('L', (right - left, bottom - top))
    ImageDraw.Draw(mask).text((-left, -top), text, font=font, fill=255)
    return mask.crop(mask.getbbox())


def menu_pixels(texture, text, fonts):
    palette = texture.palette_rgba()
    original = texture.canvas()
    height, width = texture.height, texture.width
    visible = palette[original[:height, :width], 3]
    ys, xs = np.where(visible > 0)
    top, bottom = int(ys.min()), int(ys.max()) + 1
    left, right = int(xs.min()), int(xs.max()) + 1
    small = height == 8
    header = height == 32
    font = fonts['header' if header else 'small' if small else 'option']
    mask = glyph_mask(text, font)
    cap_height = glyph_mask('H', font).height

    scale = (6 if small else bottom - top) / cap_height
    target_h = min(height, max(1, round(mask.height * scale)))
    natural_w = round(mask.width * target_h / mask.height)
    if header:
        target_w = right - left
    elif small:
        target_w = min(right, round(natural_w * 1.30))
    else:
        target_w = min(width - left - 1, natural_w)
    x = right - target_w if small else left
    y = min(height - target_h, max(0, bottom - target_h))
    coverage = np.asarray(mask.resize((target_w, target_h), Image.Resampling.LANCZOS))

    # Retain the original game's color and alpha steps, including header tint.
    valid = np.flatnonzero((palette[:, :3].sum(axis=1) > 0) & (palette[:, 3] > 0))
    valid = np.r_[0, valid]
    levels = palette[valid, 3].astype(int)
    desired = coverage.astype(int) * levels.max() // 255
    indices = valid[np.abs(desired[:, :, None] - levels).argmin(axis=2)]
    translated = np.zeros_like(original)
    translated[y:y + target_h, x:x + target_w] = indices
    return translated


def notice_pixels(texture, lines, font):
    if len(lines) != 6:
        raise ValueError('O aviso precisa de título, quatro linhas e agradecimento')
    canvas = np.zeros_like(texture.canvas())
    palette = texture.palette_rgba()
    levels = palette[:, :3].astype(int).mean(axis=1)
    has_logo = LOGO_PATH.exists()
    ys = (32, 66, 85, 104, 123, 158) if has_logo else (61, 98, 118, 137, 156, 194)
    for text, y in zip(lines, ys, strict=True):
        mask = glyph_mask(text, font)
        target_w = min(420, round(mask.width / SCALE))
        target_h = round(mask.height / SCALE)
        mask = mask.resize((target_w, target_h), Image.Resampling.LANCZOS)
        coverage = np.asarray(mask).astype(int) * levels.max() / 255
        indices = np.abs(coverage[:, :, None] - levels).argmin(axis=2)
        x = (texture.width - target_w) // 2
        canvas[y:y + target_h, x:x + target_w] = indices
    if has_logo:
        size = 64
        logo = Image.open(LOGO_PATH).convert('RGBA').resize(
            (size, size), Image.Resampling.LANCZOS)
        arr = np.asarray(logo)
        lum = (0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]) * (arr[:, :, 3] / 255.0)
        lg_idx = np.abs(lum[:, :, None] - levels).argmin(axis=2)
        gx = (texture.width - size) // 2
        gy = 194
        canvas[gy:gy + size, gx:gx + size] = lg_idx
    return canvas


def render_txb(path, source, texts, fonts):
    if hashlib.sha256(source).hexdigest() != SOURCE_HASHES[path]:
        raise ValueError(f'Textura original incompatível: {path}')
    txb = PakFile(source)
    labels = {4: ''} if path == NOTICE else LABELS[path]
    for index, label in labels.items():
        entry = txb.entries[index]
        texture = ChunkedTexture(entry.data)
        if path == NOTICE:
            canvas = notice_pixels(texture, texts['aviso']['pt'], fonts['notice'])
        else:
            canvas = menu_pixels(texture, texts['menu'][label], fonts)
        updated = texture.update_canvas(canvas)
        if len(updated) != len(entry.data):
            raise ValueError(f'Tamanho da textura mudou: {path}[{index}]')
        if not np.array_equal(ChunkedTexture(updated).canvas(), canvas):
            raise ValueError(f'Pixels divergentes após codificação: {path}[{index}]')
        entry.data = updated
    rendered = txb.build()
    if len(rendered) != len(source):
        raise ValueError(f'Tamanho do TXB mudou: {path}')
    return rendered


def patch_pak(original, members, texts, fonts):
    pak = PakFile(original)
    if pak.build() != original:
        raise ValueError('A estrutura do PAK de origem não é reproduzível')
    for member in members:
        entry = pak.get(member)
        entry.data = render_txb(member, entry.data, texts, fonts)
    patched = pak.build()
    if len(patched) != len(original):
        raise ValueError('Tamanho do PAK mudou')
    return patched


def load_fonts(directory):
    return {
        'notice': ImageFont.truetype(directory / 'verdana.ttf', 15 * SCALE),
        'option': ImageFont.truetype(directory / 'seguisb.ttf', 14 * SCALE),
        'small': ImageFont.truetype(directory / 'Square721 BT Bold.ttf', 11 * SCALE),
        'header': ImageFont.truetype(directory / 'Square721 BT Roman.ttf', 34 * SCALE),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base_iso', type=Path)
    parser.add_argument('output_iso', type=Path)
    parser.add_argument('--font-dir', type=Path,
                        default=Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts')
    args = parser.parse_args()
    if args.output_iso.exists():
        parser.error('a ISO de saída já existe')
    try:
        texts = json.loads(CATALOG.read_text(encoding='utf-8'))
        fonts = load_fonts(args.font_dir)
        with TemporaryDirectory(prefix='ccc-ui-', dir=args.output_iso.parent) as directory:
            temporary = Path(directory)
            sources = read_iso_paks(args.base_iso, temporary, MEMBERS)
            replacements = {
                offset: patch_pak(original, MEMBERS[name], texts, fonts)
                for name, (offset, original) in sources.items()
            }
            write_iso(args.base_iso, args.output_iso, temporary, replacements)
    except (OSError, ValueError) as exc:
        parser.exit(1, f'{exc}\n')
    print(f'ISO verificada: {args.output_iso.resolve()}')


if __name__ == '__main__':
    main()
