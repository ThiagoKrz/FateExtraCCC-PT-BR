"""Apply the PT-BR item texts and timed captions to a compatible CCC ISO.

    python tools/native_text.py BASE.iso --check
    python tools/native_text.py BASE.iso OUTPUT.iso

The English patch's linked code is kept in place. Only its two string pools,
their pointers, and the addresses in the two item tables are rewritten.
"""

import argparse
import hashlib
import re
import shutil
import struct
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

from pycdlib import PyCdlib
from pycdlib.pycdlibexception import PyCdlibInvalidInput

import fatetext
from build import GAME_DNS_IN_ISO, find_iso_extent
from cpk import Cpk
from medida import ASCII_W, measure, strip_for_measure
from pak import PakFile
from scripts_ccc import parse_po


CATALOGS = Path(__file__).resolve().parents[1] / 'ptbr' / 'nativo'
NATIVE = 'hax/patch.o'
NATIVE_HASH = 'bcaff2360840fd961b0a19402800d69f0cf304044099f8ba22112d7171d269d5'
PRELOAD_ADDRESS = 0x08D5F0F0
NATIVE_ADDRESS = 0x08FE1D60
# Offsets in the linked English patch.o, guarded by NATIVE_HASH.
SUB_COUNT_OFFSET = 0x2964
SUB_RECORD = struct.Struct('<IBBBBI')
SUB_PART = struct.Struct('<IhH')
SUB_POOL = (0xB3F0, 0x21BFC)
ITEM_POOL = (0x23134, 0x27354)
ITEM_TABLES = (
    ('cmn/item_param_01.bin', 0x64B0, 113, 0xE4, (0, 0x5C, 0x8C, 0xBC)),
    ('cmn/item_param_04.bin', 0x4DB0, 108, 0xB8, (0, 0x50, 0x80)),
)
ITEM_MARKER = re.compile(rb'!rmap>!([0-9A-Fa-f]{8})\x00')
SPECIAL_GLYPHS = re.compile(r'#[A-Z][A-Z0-9]*|[鷙薗☆♪]')


@dataclass(frozen=True)
class TextRef:
    key: str
    member: str
    link: int
    offset: int
    raw: bytes
    metadata: tuple = ()

    @property
    def text(self):
        return fatetext.decode(self.raw[1:] if self.member == NATIVE else self.raw)


def entry_offsets(pack):
    if not pack.has_paths or pack.entries[-1].path != NATIVE:
        raise ValueError('PRELOAD incompatível com o módulo nativo esperado')
    offsets = {}
    offset = pack.header_size
    for entry in pack.entries:
        offset += 0x40
        offsets[entry.path] = offset
        offset += len(entry.data)
    address = PRELOAD_ADDRESS + offsets[NATIVE] - pack.header_size
    if address != NATIVE_ADDRESS or offset != len(pack.raw):
        raise ValueError('Endereços ou tamanho do PRELOAD incompatíveis')
    return offsets


def read_text(native, address, pool):
    offset = address - NATIVE_ADDRESS
    start, end = pool
    if offset % 4 or not start <= offset < end:
        raise ValueError(f'Ponteiro de texto fora do bloco: {address:#x}')
    return offset, native[offset:native.index(b'\0', offset, end)]


def item_refs(pack, native):
    refs = []
    for member, length, count, stride, fields in ITEM_TABLES:
        data = pack.get(member).data
        if len(data) != length or struct.unpack_from('<I', data)[0] != count:
            raise ValueError(f'Tabela de itens incompatível: {member}')
        for row in range(count):
            for field, field_offset in enumerate(fields):
                marker = 0x10 + row * stride + field_offset
                match = ITEM_MARKER.match(data, marker)
                if not match:
                    raise ValueError(f'Marcador de item inválido: {member} {marker:#x}')
                offset, raw = read_text(native, int(match[1], 16), ITEM_POOL)
                refs.append(TextRef(f'{Path(member).stem}:{row}:{field}', member,
                                    match.start(1), offset, raw, (field,)))
    return refs


def sub_refs(native):
    count, = struct.unpack_from('<I', native, SUB_COUNT_OFFSET)
    if count != 1365:
        raise ValueError(f'Tabela de legendas incompatível: {count} eventos')
    refs = []
    table_start = SUB_COUNT_OFFSET + 4
    table_end = table_start + count * SUB_RECORD.size
    for event in range(count):
        record = SUB_RECORD.unpack_from(native, table_start + event * SUB_RECORD.size)
        audio, skip, display, dispatch, parts, address = record
        part_offset = address - NATIVE_ADDRESS
        if not table_end <= part_offset <= SUB_POOL[0] - parts * SUB_PART.size:
            raise ValueError(f'Tabela de segmentos inválida: {event}')
        for part in range(parts):
            link = part_offset + part * SUB_PART.size
            target, x, frames = SUB_PART.unpack_from(native, link)
            offset, raw = read_text(native, target, SUB_POOL)
            if not raw or raw[0] not in (1, 2) or raw[0] != raw.count(b'\n') + 1:
                raise ValueError(f'Cabeçalho de legenda inválido: {event}:{part}')
            refs.append(TextRef(f'{event}:{part}', NATIVE, link, offset, raw,
                                (audio, skip, display, dispatch, x, frames)))
    if len(refs) != 2311:
        raise ValueError(f'Tabela de legendas incompatível: {len(refs)} segmentos')
    return refs


def verify_original_pool(native, refs, pool):
    """Require all bytes in the range to belong to referenced strings or padding."""
    start, end = pool
    unique = {ref.offset: ref.raw for ref in refs}
    cursor = start
    for offset, raw in sorted(unique.items()):
        if offset != cursor:
            raise ValueError(f'Lacuna entre textos em {cursor:#x}')
        cursor = (offset + len(raw) + 4) & ~3
        if any(native[offset + len(raw):cursor]):
            raise ValueError(f'Preenchimento inválido em {offset:#x}')
    if cursor != end:
        raise ValueError(f'Fim inesperado do bloco de textos: {cursor:#x}')


def translated_entries(catalog, refs):
    translations = {}
    expected = {ref.key: ref for ref in refs if ref.text.strip()}
    for entry in parse_po(catalog)['entries']:
        key, source, target = entry['msgctxt'], entry['en'], entry['pt']
        if key in translations or key not in expected or source != expected[key].text:
            raise ValueError(f'Entrada fora da ISO base ou duplicada: {catalog.name} {key}')
        if not target.strip() or any(char in target for char in '\0\r'):
            raise ValueError(f'Tradução vazia ou inválida: {catalog.name} {key}')
        if SPECIAL_GLYPHS.findall(source) != SPECIAL_GLYPHS.findall(target):
            raise ValueError(f'Símbolos de controle divergentes: {catalog.name} {key}')
        if fatetext.decode(fatetext.encode(target)) != target:
            raise ValueError(f'Caractere indisponível na fonte: {catalog.name} {key}')
        translations[key] = target
    missing = expected.keys() - translations.keys()
    if missing:
        raise ValueError(f'{catalog.name}: {len(missing)} textos ausentes')
    return translations


def width(line):
    return measure(strip_for_measure(line))


def subtitle_bytes(text, limit, key):
    lines = text.split('\n')
    if len(lines) > 2 or any(not line.strip() or width(line) > limit for line in lines):
        raise ValueError(f'Legenda fora do limite de 2 linhas/{limit}px: {key} {text!r}')
    maximum = max(map(width, lines))
    centered = []
    for line in lines:
        # Match the upstream paired padding, rounded to the nearest space.
        padding = ' ' * ((maximum - width(line) + ASCII_W) // (2 * ASCII_W))
        centered.append(padding + line + padding)
    return bytes([len(lines)]) + fatetext.encode('\n'.join(centered))


def payloads(refs, translations):
    for ref in refs:
        pt = translations.get(ref.key)
        if pt is None:
            yield ref.raw
        elif ref.member == NATIVE:
            display = ref.metadata[2]
            limit = (67 if display == 2 else 48) * ASCII_W
            yield subtitle_bytes(pt, limit, ref.key)
        else:
            if pt.count('@') != ref.text.count('@'):
                raise ValueError(f'Separadores de item divergentes: {ref.key}')
            # Conservative static checks for names and descriptions.
            limit = 336 if ref.metadata[0] == 0 else 413
            if any(width(line) > limit for line in re.split(r'[@\n]', pt)):
                raise ValueError(f'Texto de item excede {limit}px: {ref.key} {pt!r}')
            yield fatetext.encode(pt)


def pack_pool(native, pool, raws):
    start, end = pool
    data = bytearray()
    addresses = {}
    for raw in raws:
        if raw not in addresses:
            addresses[raw] = NATIVE_ADDRESS + start + len(data)
            data.extend(raw + b'\0' * (4 - len(raw) % 4))
    if len(data) > end - start:
        raise ValueError(f'Textos precisam de {len(data)} bytes; disponíveis: {end - start}')
    native[start:end] = data.ljust(end - start, b'\0')
    return addresses, len(data)


def verify_refs(before, after, expected):
    for original, actual, raw in zip(before, after, expected, strict=True):
        if ((actual.key, actual.member, actual.link, actual.metadata)
                != (original.key, original.member, original.link, original.metadata)
                or actual.raw != raw):
            raise ValueError(f'Texto ou metadados divergentes após a gravação: {actual.key}')


def patch_preload(original):
    pack = PakFile(original)
    offsets = entry_offsets(pack)
    native = pack.get(NATIVE).data
    if hashlib.sha256(native).hexdigest() != NATIVE_HASH:
        raise ValueError('Use a ISO PT-BR integrada com o módulo nativo inglês de 08/12/2023')

    items, subs = item_refs(pack, native), sub_refs(native)
    for refs, pool in ((items, ITEM_POOL), (subs, SUB_POOL)):
        verify_original_pool(native, refs, pool)
    addresses = {NATIVE_ADDRESS + ref.offset for ref in (*items, *subs)}
    found_links = {index * 4 for index, (value,) in enumerate(struct.iter_unpack('<I', native))
                   if value in addresses}
    if found_links != {ref.link for ref in subs}:
        raise ValueError('Há referências inesperadas aos blocos de texto nativo')

    item_pt = translated_entries(CATALOGS / 'itens.po', items)
    sub_pt = translated_entries(CATALOGS / 'legendas.po', subs)
    item_raws = list(payloads(items, item_pt))
    sub_raws = list(payloads(subs, sub_pt))
    native_new = bytearray(native)
    item_addr, item_size = pack_pool(native_new, ITEM_POOL, item_raws)
    sub_addr, sub_size = pack_pool(native_new, SUB_POOL, sub_raws)

    out = bytearray(original)
    for ref, raw in zip(items, item_raws, strict=True):
        link = offsets[ref.member] + ref.link
        out[link:link + 8] = f'{item_addr[raw]:08X}'.encode('ascii')
    for ref, raw in zip(subs, sub_raws, strict=True):
        struct.pack_into('<I', native_new, ref.link, sub_addr[raw])
    start = offsets[NATIVE]
    out[start:start + len(native)] = native_new

    updated = PakFile(bytes(out))
    if entry_offsets(updated) != offsets or len(out) != len(original):
        raise ValueError('A aplicação alterou o tamanho de uma entrada do PRELOAD')
    verify_refs(items, item_refs(updated, native_new), item_raws)
    verify_refs(subs, sub_refs(native_new), sub_raws)
    print(f'Itens: {len(item_pt)} campos traduzidos; {item_size}/{ITEM_POOL[1]-ITEM_POOL[0]} bytes')
    print(f'Legendas: {len(sub_pt)} segmentos traduzidos; {sub_size}/{SUB_POOL[1]-SUB_POOL[0]} bytes')
    return bytes(out)


def read_iso_paks(iso_path, temporary, names, skipped=None):
    """Read selected uncompressed CPK members and their image-relative offsets."""
    try:
        dns_offset, dns_size = find_iso_extent(str(iso_path), GAME_DNS_IN_ISO)
        dns_path = GAME_DNS_IN_ISO
    except PyCdlibInvalidInput:
        dns_path = GAME_DNS_IN_ISO + ';1'
        dns_offset, dns_size = find_iso_extent(str(iso_path), dns_path)
    iso = PyCdlib()
    iso.open(str(iso_path))
    dns = temporary / 'GAME.DNS'
    try:
        with dns.open('wb') as output:
            iso.get_file_from_iso_fp(output, iso_path='/' + dns_path)
    finally:
        iso.close()
    packs = {}
    with closing(Cpk(dns)) as cpk:
        for entry in cpk.iter_files():
            name = entry['name']
            if entry['dir'] != 'pack' or name not in names:
                continue
            if skipped is not None and entry['extract_size'] != entry['size']:
                skipped.add(name)   # comprimido: quem chamou decide o que fazer
                continue
            if name in packs or entry['extract_size'] != entry['size']:
                raise ValueError(f'PAK duplicado ou comprimido: {name}')
            if entry['abs_offset'] + entry['size'] > dns_size:
                raise ValueError(f'PAK fora dos limites do GAME.DNS: {name}')
            packs[name] = (dns_offset + entry['abs_offset'], cpk.read_file(entry))
    dns.unlink()
    if missing := set(names) - packs.keys() - (skipped or set()):
        raise ValueError(f'PAK ausente: {", ".join(sorted(missing))}')
    return packs


def read_preload(iso_path, temporary):
    return read_iso_paks(iso_path, temporary, {'PRELOAD.pak'})['PRELOAD.pak']


def verify_iso(base, output, replacements):
    """Check the written PAKs and compare every other byte to the input image."""
    if base.stat().st_size != output.stat().st_size:
        raise ValueError('O tamanho final da ISO diverge da base')
    with base.open('rb') as original, output.open('rb') as candidate:
        for start, expected in sorted(replacements.items()):
            remaining = start - original.tell()
            if remaining < 0:
                raise ValueError('PAKs de substituição sobrepostos')
            while remaining:
                size = min(4 << 20, remaining)
                if original.read(size) != candidate.read(size):
                    raise ValueError('A ISO mudou fora dos PAKs de substituição')
                remaining -= size
            original.seek(len(expected), 1)
            if candidate.read(len(expected)) != expected:
                raise ValueError(f'PAK gravado difere do conteúdo validado: {start:#x}')
        while chunk := original.read(4 << 20):
            if candidate.read(len(chunk)) != chunk:
                raise ValueError('A ISO mudou depois do último PAK de substituição')


def write_iso(base, output, temporary, replacements):
    staged = temporary / output.name
    shutil.copyfile(base, staged)
    with staged.open('r+b') as image:
        for offset, data in replacements.items():
            image.seek(offset)
            image.write(data)
    verify_iso(base, staged, replacements)
    if output.exists():
        raise FileExistsError(output)
    staged.rename(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base_iso', type=Path)
    parser.add_argument('output_iso', nargs='?', type=Path)
    parser.add_argument('--check', action='store_true', help='valida os textos sem criar uma ISO')
    args = parser.parse_args()
    if args.check == bool(args.output_iso):
        parser.error('informe uma ISO de saída ou use --check')

    parent = args.output_iso.parent if args.output_iso else args.base_iso.parent
    if args.output_iso and args.output_iso.exists():
        parser.error('a ISO de saída já existe')
    try:
        with TemporaryDirectory(prefix='ccc-native-', dir=parent) as directory:
            temporary = Path(directory)
            offset, original = read_preload(args.base_iso, temporary)
            patched = patch_preload(original)
            if args.check:
                return
            write_iso(args.base_iso, args.output_iso, temporary, {offset: patched})
    except (OSError, ValueError) as exc:
        parser.exit(1, f'{exc}\n')
    print(f'ISO verificada: {args.output_iso.resolve()}')


if __name__ == '__main__':
    main()
