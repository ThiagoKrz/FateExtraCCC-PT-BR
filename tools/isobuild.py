"""Write a fresh PSP ISO from the extracted tree.

Patching GAME.DNS back into a copy of the original image only works while the
new CPK still fits in the old one's extent. Once the translation grows past
that, the image has to be rebuilt - this does that, copying the original
volume identifiers so the result still looks like the same UMD.
"""
import os
import pycdlib

# Order matters only for read performance on real hardware; correctness-wise
# any order works. Directories are created before the files inside them.
DIRS = ['/PSP_GAME', '/PSP_GAME/INSDIR', '/PSP_GAME/SYSDIR',
        '/PSP_GAME/SYSDIR/UPDATE', '/PSP_GAME/USRDIR', '/PSP_GAME/USRDIR/MOVIE']


def read_volume_info(src_iso):
    iso = pycdlib.PyCdlib()
    iso.open(src_iso)
    pvd = iso.pvds[0]
    info = {
        'sys_ident': pvd.system_identifier.decode('ascii').rstrip(),
        'vol_ident': pvd.volume_identifier.decode('ascii').rstrip(),
        'app_ident': pvd.application_identifier.text.decode('ascii').rstrip(),
    }
    iso.close()
    return info


def collect(tree_dir):
    """Every file under the extracted tree, as (iso_path, local_path)."""
    out = []
    for root, _, names in os.walk(tree_dir):
        for nm in sorted(names):
            local = os.path.join(root, nm)
            rel = os.path.relpath(local, tree_dir).replace(os.sep, '/')
            out.append(('/' + rel, local))
    return out


def build(tree_dir, out_iso, src_iso, overrides=None, log=print):
    """overrides maps an iso path like 'PSP_GAME/INSDIR/GAME.DNS' to a local file."""
    overrides = overrides or {}
    info = read_volume_info(src_iso)
    log('  identificadores: sistema=%r volume=%r' % (info['sys_ident'], info['vol_ident']))

    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=1,
            sys_ident=info['sys_ident'],
            vol_ident=info['vol_ident'],
            app_ident_str=info['app_ident'])

    for d in DIRS:
        iso.add_directory(d)

    files = collect(tree_dir)
    for iso_path, local in files:
        src = overrides.get(iso_path.lstrip('/'), local)
        size = os.path.getsize(src)
        # ISO9660 file identifiers carry a version suffix
        iso.add_file(src, iso_path + ';1')
        log('    %-40s %d bytes' % (iso_path, size))

    iso.write(out_iso)
    iso.close()
    return os.path.getsize(out_iso)
