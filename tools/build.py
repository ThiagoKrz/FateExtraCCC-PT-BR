"""Build a pt-BR ISO from the English base + whatever is translated in ptbr/.

Pipeline:
  ptbr/*.po  ->  patch .dat/.bin  ->  rebuild .pak  ->  patch GAME.DNS (CPK)
             ->  write output/ccc-ptbr.iso

Anything left untranslated keeps the English text, so the ISO is always
playable no matter how far the translation has got.

Usage:  python tools/build.py [--only historia/024]
"""
import os
import sys
import glob
import json
import shutil
import struct

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fatetext
import binfile
import fixedbin
import medida
import pak as pakmod
from cpk import Cpk
from dump import read_po

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAKDIR = os.path.join(ROOT, 'work', 'pak')
CPKDIR = os.path.join(ROOT, 'work', 'cpk')
PTBR = os.path.join(ROOT, 'ptbr')
OUTDIR = os.path.join(ROOT, 'output')
BASE_ISO = os.path.join(ROOT, 'EnglishBase', 'ccc-patched.iso')
GAME_DNS_IN_ISO = 'PSP_GAME/INSDIR/GAME.DNS'

warnings = []


def warn(msg):
    warnings.append(msg)
    print('  AVISO: %s' % msg)


def check_encodable(text, where):
    """Reject characters the in-game font cannot draw."""
    bad = set()
    for ch in text:
        if ch in fatetext.ACCENTS_REV or ch in '\n\r\t':
            continue
        try:
            ch.encode('cp932')
        except UnicodeEncodeError:
            bad.add(ch)
    if bad:
        warn('%s: caractere sem glifo no jogo: %s (sera substituido)'
             % (where, ' '.join(sorted(bad))))
    return bad


def patched_game_files(only=None):
    """Return {game_relative_path: new_bytes} for every translated file."""
    result = {}

    # --- patched font (adds the pt-BR accented letters) ---
    fontdir = os.path.join(ROOT, 'work', 'font-ptbr')
    if os.path.isdir(fontdir):
        for nm in ('font.txb', 'kanzi.bin'):
            p = os.path.join(fontdir, nm)
            if os.path.exists(p):
                result[nm] = open(p, 'rb').read()
        if result:
            print('  fonte pt-BR: %s' % ', '.join(sorted(result)))
    else:
        warn('work/font-ptbr nao existe - rode tools/accents.py para gerar os acentos')

    # --- story scripts (.dat) ---
    for po in sorted(glob.glob(os.path.join(PTBR, 'historia', '*.po'))):
        stem = os.path.splitext(os.path.basename(po))[0]
        if only and ('historia/' + stem) not in only:
            continue
        tl = read_po(po)
        if not tl:
            continue
        if stem.endswith('-1000'):
            rel = 'field_new/%s/1000.dat' % stem[:-5]
        else:
            rel = 'field_new/%s/0000.dat' % stem
        src = os.path.join(PAKDIR, rel.replace('/', os.sep))
        if not os.path.exists(src):
            warn('%s: arquivo de origem nao encontrado (%s)' % (po, rel))
            continue
        data = open(src, 'rb').read()
        entries = fatetext.scan_dat(data, rel)
        valid = {e['textLoc'] for e in entries}
        types_by_loc = {}
        for e in entries:
            types_by_loc.setdefault(e['textLoc'], set()).add(e['type'])
        types_by_loc = {k: ','.join(sorted(v)) for k, v in types_by_loc.items()}
        texts = {}
        for ctx, val in tl.items():
            loc = int(ctx)
            if loc not in valid:
                warn('%s: msgctxt %s nao existe mais no script' % (po, ctx))
                continue
            check_encodable(val, '%s:%s' % (stem, ctx))
            # o jogo nao quebra linha sozinho: o que passa da largura da caixa
            # some da tela, entao isso e verificado a cada build
            kind = medida.kind_for(types_by_loc.get(loc, ''))
            for ln, w, limit, why in medida.check(val, kind):
                if why == 'linhas demais':
                    warn('%s[%s]: %d linhas, cabem %d' % (stem, ctx, w, limit))
                else:
                    warn('%s[%s]: linha %d tem %dpx, cabe %dpx (corte ~%d caractere(s))'
                         % (stem, ctx, ln, w, limit, (w - limit + 6) // 7))
            texts[loc] = val
        if not texts:
            continue
        result[rel] = fatetext.patch_dat(data, {'entries': entries, 'texts': texts})
        print('  historia/%s: %d textos' % (stem, len(texts)))

    # --- menus and the fixed-width formats (.bin) ---
    for group in ('menus', 'lore', 'sg'):
        for po in sorted(glob.glob(os.path.join(PTBR, group, '*.po'))):
            stem = os.path.splitext(os.path.basename(po))[0]
            if only and ('%s/%s' % (group, stem)) not in only:
                continue
            tl = read_po(po)
            if not tl:
                continue
            rel = stem.replace('__', '/') + '.bin'
            src = os.path.join(PAKDIR, rel.replace('/', os.sep))
            if not os.path.exists(src):
                warn('%s: arquivo de origem nao encontrado (%s)' % (po, rel))
                continue
            data = open(src, 'rb').read()
            fmt = fixedbin.file_format(rel)
            used = 0
            try:
                if fmt:
                    _, (entries, layout) = fixedbin.parse(rel, data)
                    new = []
                    for i, (slot, text) in enumerate(entries):
                        val = tl.get(str(i))
                        if val:
                            check_encodable(val, '%s:%d' % (stem, i))
                            used += 1
                            new.append((slot, val))
                        else:
                            new.append((slot, text))
                    if not used:
                        continue
                    result[rel] = fixedbin.build(fmt, new, layout)
                else:
                    is_utf8 = rel in binfile.UTF8_FILES
                    entries = binfile.parse(data, utf8=is_utf8)
                    new = []
                    for i, (idx, text) in enumerate(entries):
                        val = tl.get(str(i))
                        if val:
                            # UTF-8 files are not drawn with the CP932 font, so
                            # the glyph check does not apply to them
                            if not is_utf8:
                                check_encodable(val, '%s:%d' % (stem, i))
                            used += 1
                            new.append((idx, val))
                        else:
                            new.append((idx, text))
                    if not used:
                        continue
                    result[rel] = binfile.build(new, utf8=is_utf8)
            except fixedbin.TooLong as ex:
                warn('%s/%s: traducao nao cabe no campo (%s) - arquivo mantido em ingles'
                     % (group, stem, ex))
                continue
            print('  %s/%s: %d textos' % (group, stem, used))

    return result


def patched_eboot(only=None):
    """Patch strings inside EBOOT.BIN. Returns new bytes, or None if unchanged.

    EBOOT.BIN sits directly in the ISO rather than inside the CPK, and its size
    never changes, so the result is spliced straight into the output image.
    """
    import eboot
    po = os.path.join(PTBR, 'sistema', 'eboot.po')
    if not os.path.exists(po):
        return None
    if only and 'sistema/eboot' not in only:
        return None
    tl = read_po(po)
    if not tl:
        return None
    src = os.path.join(ROOT, 'work', 'iso', 'PSP_GAME', 'SYSDIR', 'EBOOT.BIN')
    data = open(src, 'rb').read()
    wanted = {}
    for ctx, val in tl.items():
        check_encodable(val, 'eboot:%s' % ctx)
        wanted[int(ctx)] = val
    new, skipped = eboot.build(data, wanted)
    for i, why in skipped:
        warn('eboot[%d]: %s - entrada mantida em ingles' % (i, why))
    applied = len(wanted) - len(skipped)
    if applied <= 0:
        return None
    print('  sistema/eboot: %d textos' % applied)
    return new


def rebuild_paks(game_files):
    """Map patched game files back into the .pak/.cmp containers holding them."""
    refs = json.load(open(os.path.join(PAKDIR, 'pak-files.json'), encoding='utf-8'))
    containers = {}
    for rel in game_files:
        holders = refs.get(rel)
        if not holders:
            warn('%s: nao esta em nenhum .pak' % rel)
            continue
        for h in holders:
            containers.setdefault(h, set()).add(rel)

    out = {}
    for cont, members in sorted(containers.items()):
        src = os.path.join(CPKDIR, cont.replace('/', os.sep))
        original = pakmod.load_package(src)
        pk = pakmod.PakFile(original)
        # PRELOAD.pak is special: the English patch loads its native code at
        # baseAddress + sum(entry size + 0x40), an address baked into the
        # EBOOT. If any entry changes size that code moves and the game dies
        # on boot, so refuse rather than ship a broken ISO.
        sizes_before = {e.path: len(e.data) for e in pk.entries}
        for rel in members:
            pk.replace(rel, game_files[rel])
        if cont.endswith('PRELOAD.pak'):
            reverted = False
            for e in pk.entries:
                if len(e.data) != sizes_before[e.path]:
                    warn('PRELOAD.pak: %s ficaria com %d bytes em vez de %d. '
                         'Arquivos do PRELOAD nao podem mudar de tamanho '
                         '(desloca o codigo nativo e trava o boot), entao esse '
                         'arquivo fica em ingles. Encurte a traducao.'
                         % (e.path, len(e.data), sizes_before[e.path]))
                    reverted = True
            if reverted:
                # rebuild from scratch, keeping only the entries that fit
                pk = pakmod.PakFile(original)
                for rel in members:
                    candidate = game_files[rel]
                    if len(pakmod.pad16(candidate)) == sizes_before[rel]:
                        pk.replace(rel, candidate)
        # a .cmp is rewritten as a plain .pak (the CPK entry gets renamed too)
        name = cont[:-4] + '.pak' if cont.endswith('.cmp') else cont
        out[cont] = pk.build()
        print('  pak %s -> %d bytes' % (name, len(out[cont])))
    return out


def find_iso_extent(iso_path, rel):
    import pycdlib
    iso = pycdlib.PyCdlib()
    iso.open(iso_path)
    try:
        rec = iso._find_iso_record(('/' + rel).encode('ascii'))
        lba = rec.extent_location()
        size = rec.get_data_length()
        block = iso.pvds[0].logical_block_size()
    finally:
        iso.close()
    return lba * block, size


def main():
    only = None
    if '--only' in sys.argv:
        only = set(sys.argv[sys.argv.index('--only') + 1].split(','))
        print('Modo parcial: %s' % ', '.join(sorted(only)))

    if not os.path.exists(BASE_ISO):
        sys.exit('ISO base nao encontrada: %s' % BASE_ISO)

    print('1/5  Lendo traducoes e aplicando nos arquivos do jogo...')
    game_files = patched_game_files(only)
    eboot_bytes = patched_eboot(only)
    if not game_files and not eboot_bytes:
        sys.exit('Nenhuma traducao encontrada em ptbr/. Traduza algo primeiro.')
    print('     %d arquivos de jogo modificados' % len(game_files))

    print('2/5  Reconstruindo containers .pak...')
    paks = rebuild_paks(game_files)

    print('3/5  Copiando GAME.DNS base...')
    os.makedirs(OUTDIR, exist_ok=True)
    work_dns = os.path.join(OUTDIR, 'GAME.DNS.tmp')
    shutil.copyfile(os.path.join(ROOT, 'work', 'iso', 'PSP_GAME', 'INSDIR', 'GAME.DNS'), work_dns)

    print('4/5  Aplicando no CPK...')
    cpk = Cpk(work_dns, 'r+b')
    stats = cpk.patch_in_place(paks)
    cpk.close()

    print('5/5  Gerando ISO...')
    dns_off, dns_size = find_iso_extent(BASE_ISO, GAME_DNS_IN_ISO)
    new_len = stats['new_len']
    out_iso = os.path.join(OUTDIR, 'ccc-ptbr.iso')

    if new_len > dns_size:
        # The patched CPK outgrew the extent it sits in, so the image cannot be
        # written over a copy of the original any more - build a fresh one.
        print('     GAME.DNS passou do espaco original (%.1f MiB a mais); '
              'reconstruindo a ISO inteira' % ((new_len - dns_size) / 1048576.0))
        import isobuild
        overrides = {'PSP_GAME/INSDIR/GAME.DNS': work_dns}
        eboot_tmp = None
        if eboot_bytes:
            eboot_tmp = os.path.join(OUTDIR, 'EBOOT.BIN.tmp')
            with open(eboot_tmp, 'wb') as f:
                f.write(eboot_bytes)
            overrides['PSP_GAME/SYSDIR/EBOOT.BIN'] = eboot_tmp
        size = isobuild.build(os.path.join(ROOT, 'work', 'iso'), out_iso,
                              BASE_ISO, overrides, log=lambda s: None)
        os.remove(work_dns)
        if eboot_tmp:
            os.remove(eboot_tmp)
        print('\nPronto: %s' % out_iso)
        print('Tamanho: %.2f GiB' % (size / 1073741824.0))
        if warnings:
            print('\n%d aviso(s):' % len(warnings))
            for w in warnings[:20]:
                print('  - %s' % w)
        return

    shutil.copyfile(BASE_ISO, out_iso)
    with open(out_iso, 'r+b') as iso, open(work_dns, 'rb') as dns:
        iso.seek(dns_off)
        shutil.copyfileobj(dns, iso, 1024 * 1024)
        # zero the tail so no stale bytes remain inside the file's extent
        written = new_len
        if written < dns_size:
            iso.seek(dns_off + written)
            remaining = dns_size - written
            chunk = b'\0' * (1024 * 1024)
            while remaining > 0:
                iso.write(chunk[:min(len(chunk), remaining)])
                remaining -= min(len(chunk), remaining)

        if eboot_bytes:
            eb_off, eb_size = find_iso_extent(BASE_ISO, 'PSP_GAME/SYSDIR/EBOOT.BIN')
            if len(eboot_bytes) != eb_size:
                sys.exit('EBOOT.BIN mudou de tamanho (%d != %d)'
                         % (len(eboot_bytes), eb_size))
            iso.seek(eb_off)
            iso.write(eboot_bytes)
            print('     EBOOT.BIN gravado (%d bytes)' % eb_size)
    os.remove(work_dns)

    print('\nPronto: %s' % out_iso)
    print('Tamanho: %.2f GiB' % (os.path.getsize(out_iso) / 1073741824.0))
    if warnings:
        print('\n%d aviso(s):' % len(warnings))
        for w in warnings[:20]:
            print('  - %s' % w)


if __name__ == '__main__':
    main()
