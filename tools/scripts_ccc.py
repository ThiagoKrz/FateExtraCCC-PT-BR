"""Backend compartilhado entre o Painel GUI, a pasta trabalho/ e os .po de ptbr/.

Mantém sincronizados:
  - `ptbr/<grupo>/<arquivo>.po` (fonte usada por build.py, glossario.py, medida.py, genero.py)
  - `trabalho/<capitulo>/<ordem>_<slug>__<stem>.json` + `trabalho/manifesto.json`
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
import glob
import hashlib
import json
import os
from pathlib import Path
import re
import sys

TOOLS_DIR = Path(__file__).resolve().parent
ROOT = TOOLS_DIR.parent
PTBR = ROOT / 'ptbr'
WORK = ROOT / 'trabalho'
STANDARDS = ROOT / 'standards'

if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import binfile
import catalogo_ccc as cat
import fatetext
import genero
import medida

TAG_PATTERNS = (
    re.compile(r'#C\d{8}#?'),
    re.compile(r'#CDEF'),
    re.compile(r'#RUBS|#RUBE|#REND'),
    re.compile(r'#ROFS[-\d]\d{3}'),
    re.compile(r'#FAMILY|#GIVEN|#NICK|#SVT'),
    re.compile(r'#TITM\d{4}|#VAL\d{3}|#TVAL\d{2}|#SP\d{2}|#T\d'),
)

# Strings muito genéricas/curtas que podem ter traduções contextuais diferentes em menus
SKIP_AUTO_PROPAGATE_EN = {'Yes', ' No', 'Exit', 'Buy', 'Sell', 'Items'}


@dataclass
class Issue:
    message: str
    file: str = ''
    scene: str = ''
    row_id: int | str | None = None
    field: str = 'pt'
    po_line: int | None = None
    column: int | None = None
    severity: str = 'erro'


@dataclass
class Inspection:
    manifest: dict | None = None
    issues: list[Issue] = field(default_factory=list)

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == 'erro']

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.severity != 'erro']


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def atomic_write(path: Path | str, data: bytes) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + '.tmp')
    tmp.write_bytes(data)
    os.replace(tmp, p)


def read_json(path: Path | str) -> dict:
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write_json(path: Path | str, payload: dict) -> str:
    raw = (json.dumps(payload, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    atomic_write(path, raw)
    return sha(raw)


def po_escape(s: str) -> str:
    s = s.replace('\\', '\\\\').replace('"', '\\"')
    return s.replace('\r', '\\r').replace('\n', '\\n').replace('\t', '\\t')


def po_unescape(s: str) -> str:
    out = []
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c == '\\' and i + 1 < n:
            nxt = s[i + 1]
            out.append({'n': '\n', 'r': '\r', 't': '\t', '"': '"', '\\': '\\'}.get(nxt, nxt))
            i += 2
        else:
            out.append(c)
            i += 1
    return ''.join(out)


def parse_po_text(text: str) -> dict:
    """Lê texto em formato .po mantendo cabeçalho, comentários, msgctxt, msgid e msgstr."""
    blocks = re.split(r'\r?\n\s*\r?\n', text.strip())
    header_lines: list[str] = []
    source_bin = ''
    entries: list[dict] = []

    for b_idx, block in enumerate(blocks):
        lines = block.splitlines()
        if b_idx == 0 and any(ln.startswith('msgid ""') for ln in lines):
            header_lines = lines
            for ln in lines:
                if ln.startswith('# Fonte no jogo:'):
                    source_bin = ln.split(':', 1)[1].strip()
            continue

        comment_parts: list[str] = []
        msgctxt = None
        cur_field = None
        buf_id: list[str] = []
        buf_str: list[str] = []

        for ln in lines:
            st = ln.strip()
            if st.startswith('#.'):
                comment_parts.append(st[2:].strip())
            elif st.startswith('#'):
                continue
            elif st.startswith('msgctxt "') and st.endswith('"'):
                msgctxt = po_unescape(st[9:-1])
                cur_field = None
            elif st.startswith('msgid "') and st.endswith('"'):
                cur_field = 'id'
                buf_id = [po_unescape(st[7:-1])]
            elif st.startswith('msgstr "') and st.endswith('"'):
                cur_field = 'str'
                buf_str = [po_unescape(st[8:-1])]
            elif st.startswith('"') and st.endswith('"') and cur_field:
                val = po_unescape(st[1:-1])
                if cur_field == 'id':
                    buf_id.append(val)
                else:
                    buf_str.append(val)

        if msgctxt is not None:
            entries.append({
                'msgctxt': msgctxt,
                'comment': ' '.join(comment_parts).strip(),
                'en': ''.join(buf_id),
                'pt': ''.join(buf_str),
            })

    return {
        'header_lines': header_lines,
        'source_bin': source_bin,
        'entries': entries,
    }


def parse_po(path: Path) -> dict:
    """Lê um .po mantendo cabeçalho, comentários, msgctxt, msgid e msgstr."""
    return parse_po_text(path.read_text(encoding='utf-8-sig'))


def write_po(path: Path, parsed_or_header: list[str], source_rel: str, entries: list[dict], title: str = '') -> None:
    """Grava o .po preservando msgctxt, msgid e comentários originais, atualizando só msgstr."""
    out: list[str] = []
    if parsed_or_header:
        out.extend(parsed_or_header)
    else:
        out.extend([
            f'# {title or path.stem}',
            f'# Fonte no jogo: {source_rel}',
            '# Deixe msgstr "" para manter o texto em ingles.',
            '# Nao altere as linhas msgctxt nem os codigos de controle (#CDEF, #RUBS, ...).',
            'msgid ""',
            'msgstr ""',
            '"Content-Type: text/plain; charset=UTF-8\\n"',
            '"Language: pt_BR\\n"',
        ])
    out.append('')
    for e in entries:
        cmt = e.get('comment') or e.get('tipo') or ''
        if cmt:
            out.append(f'#. {cmt}')
        out.append(f'msgctxt "{po_escape(str(e["msgctxt"]))}"')
        out.append(f'msgid "{po_escape(str(e["en"]))}"')
        pt_val = e.get('pt', e.get('msgstr', '')) or ''
        out.append(f'msgstr "{po_escape(str(pt_val))}"')
        out.append('')

    atomic_write(path, ('\n'.join(out)).encode('utf-8'))


def parse_max_bytes(comment: str, en: str = '', po_id: str = '') -> int | None:
    m = re.search(r'max\s+(\d+)\s+bytes', comment or '')
    if m:
        return int(m.group(1))
    if po_id == 'historia/main':
        slot = (len(fatetext.encode(en)) + 4) & ~3
        return max(0, slot - 1)
    if po_id == 'menus/interface__cmn__install':
        return len(en.encode('utf-8'))
    return None


def _bin_rel_from_item(item: dict) -> str:
    stem = item['stem']
    if item['cat'] == 'historia':
        if stem.endswith('-1000'):
            return f"field_new/{stem[:-5]}/1000.dat"
        return f"field_new/{stem}/0000.dat"
    if item['cat'] == 'sistema':
        return 'PSP_GAME/SYSDIR/EBOOT.BIN'
    return stem.replace('__', '/') + '.bin'


def compute_string_frequencies(items: list[dict], parsed_cache: dict[str, dict]) -> Counter:
    freq: Counter = Counter()
    for it in items:
        parsed = parsed_cache[it['id']]
        for s in {e['en'] for e in parsed['entries']}:
            freq[s] += 1
    return freq


def _build_scene_payload(item: dict, parsed: dict, freq: Counter) -> dict:
    po_id = item['id']
    origem = parsed.get('source_bin') or _bin_rel_from_item(item)
    is_utf8 = origem in binfile.UTF8_FILES
    linhas = []
    traduzidas = 0
    exclusivas = 0

    for idx, e in enumerate(parsed['entries'], 1):
        en = e['en']
        pt = e['pt']
        cmt = e['comment']
        rep = freq.get(en, 1)
        comum = rep >= 25
        if not comum:
            exclusivas += 1
        if pt:
            traduzidas += 1
        linhas.append({
            'id': idx,
            'msgctxt': e['msgctxt'],
            'tipo': cmt,
            'medida': medida.kind_for(cmt),
            'max_bytes': parse_max_bytes(cmt, en, po_id),
            'comum': comum,
            'repeticoes': rep,
            'en': en,
            'pt': pt,
        })

    return {
        'id': po_id,
        'po': item['po_rel'],
        'grupo': item['grupo_id'],
        'capitulo': item['planilha_cap'],
        'titulo': item['titulo'],
        'origem': origem,
        'utf8': is_utf8,
        'preload_fixo': item['preload_fixo'],
        'is_stub': item['is_stub'],
        'nota': item['nota'],
        'linhas_totais': len(linhas),
        'linhas_exclusivas': exclusivas,
        'traduzidas': traduzidas,
        'linhas': linhas,
    }


def _po_to_json_sync_needed(po_path: Path, json_path: Path) -> bool:
    if not json_path.exists():
        return True
    return po_path.stat().st_mtime > json_path.stat().st_mtime + 0.5


def build_work_tree(work_dir: Path = WORK, force_all: bool = False) -> dict:
    """Constrói ou atualiza a árvore `trabalho/` e `trabalho/manifesto.json` a partir de `ptbr/`."""
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    items = cat.catalogar_todos(str(PTBR))

    parsed_cache: dict[str, dict] = {}
    for it in items:
        parsed_cache[it['id']] = parse_po(ROOT / it['po_rel'])

    freq = compute_string_frequencies(items, parsed_cache)

    total_lines = 0
    total_translated = 0
    manifest_scenes: dict[str, dict] = {}
    manifest_groups: list[dict] = []
    grp_counts = {gid: {'id': gid, 'rotulo': rot, 'planilha': plan, 'descricao': desc, 'cenas': 0, 'linhas': 0, 'traduzidas': 0}
                  for gid, rot, plan, desc in cat.GRUPOS}

    for it in items:
        po_path = ROOT / it['po_rel']
        json_path = work_dir / it['work_rel']
        parsed = parsed_cache[it['id']]
        if force_all or _po_to_json_sync_needed(po_path, json_path):
            payload = _build_scene_payload(it, parsed, freq)
            write_json(json_path, payload)
        else:
            payload = read_json(json_path)

        n_lines = len(payload['linhas'])
        n_tr = sum(1 for r in payload['linhas'] if str(r.get('pt', '')).strip())
        n_uniq = payload.get('linhas_exclusivas', 0)

        total_lines += n_lines
        total_translated += n_tr

        g = grp_counts[it['grupo_id']]
        g['cenas'] += 1
        g['linhas'] += n_lines
        g['traduzidas'] += n_tr

        manifest_scenes[it['id']] = {
            'id': it['id'],
            'po': it['po_rel'],
            'path': it['work_rel'],
            'grupo': it['grupo_id'],
            'capitulo': it['planilha_cap'],
            'ordem': it['ordem'],
            'titulo': it['titulo'],
            'origem': payload['origem'],
            'nota': it['nota'],
            'is_stub': it['is_stub'],
            'preload_fixo': it['preload_fixo'],
            'linhas': n_lines,
            'exclusivas': n_uniq,
            'traduzidas': n_tr,
        }

    for gid, *_ in cat.GRUPOS:
        manifest_groups.append(grp_counts[gid])

    manifest = {
        'projeto': 'Fate/Extra CCC PT-BR',
        'scene_count': len(manifest_scenes),
        'line_count': total_lines,
        'translated_count': total_translated,
        'groups': manifest_groups,
        'scenes': manifest_scenes,
    }
    write_json(work_dir / 'manifesto.json', manifest)
    return manifest


def refresh_manifest(work_dir: Path = WORK) -> dict:
    """Recalcula contagens no manifesto a partir dos JSONs em trabalho/."""
    work_dir = Path(work_dir)
    man_path = work_dir / 'manifesto.json'
    if not man_path.exists():
        return build_work_tree(work_dir)
    manifest = read_json(man_path)
    grp_totals = {g['id']: g for g in manifest.get('groups', [])}
    for g in grp_totals.values():
        g['linhas'] = 0
        g['traduzidas'] = 0
    total_lines = 0
    total_translated = 0
    for sid, meta in manifest.get('scenes', {}).items():
        jp = work_dir / meta['path']
        if jp.exists():
            sc = read_json(jp)
            lines = sc.get('linhas', [])
            n_lines = len(lines)
            n_tr = sum(1 for r in lines if str(r.get('pt', '')).strip())
            meta['linhas'] = n_lines
            meta['traduzidas'] = n_tr
        else:
            n_lines = meta.get('linhas', 0)
            n_tr = meta.get('traduzidas', 0)
        total_lines += n_lines
        total_translated += n_tr
        g = grp_totals.get(meta['grupo'])
        if g:
            g['linhas'] += n_lines
            g['traduzidas'] += n_tr
    manifest['line_count'] = total_lines
    manifest['translated_count'] = total_translated
    write_json(man_path, manifest)
    return manifest


def _can_fit_translation(en: str, pt: str, max_bytes: int | None, is_utf8: bool, po_id: str) -> tuple[bool, str]:
    if not pt:
        return True, ''
    if po_id == 'menus/interface__cmn__install':
        return False, 'interface/cmn/install.bin permanece em inglês (UTF-8 tamanho fixo no PRELOAD.pak)'
    if is_utf8:
        blen = len(pt.encode('utf-8'))
        if max_bytes is not None and blen > max_bytes:
            return False, f'{blen} > {max_bytes} bytes UTF-8'
        return True, ''
    try:
        enc = fatetext.encode(pt)
    except UnicodeEncodeError as exc:
        return False, f'caractere sem glifo CP932: {exc}'
    pad = 4 - (len(enc) % 4)
    if max_bytes is not None:
        # historia/main e sistema/eboot exigem apenas 1 byte NUL (len(enc) <= max_bytes).
        # Os formatos fixedbin (sg/, lore/, menus/) gravam writeDatString alinhado em 4 bytes.
        if po_id in ('historia/main', 'sistema/eboot'):
            if len(enc) > max_bytes:
                onde = 'PRELOAD.pak' if po_id == 'historia/main' else 'EBOOT.BIN'
                return False, f'{len(enc)} > {max_bytes} bytes úteis no slot de {onde}'
        elif len(enc) + pad > max_bytes + 1:
            return False, f'{len(enc) + pad} > {max_bytes + 1} bytes do campo fixo'
    return True, ''


def save_scene(work_dir: Path, json_path: Path, data: dict, fingerprint: str | None = None,
               propagate: bool = True) -> tuple[str, int]:
    """Salva o JSON da cena, atualiza o `.po` correspondente e propaga traduções seguras."""
    work_dir = Path(work_dir)
    json_path = Path(json_path)
    if fingerprint is not None and json_path.exists():
        current = sha(json_path.read_bytes())
        if current != fingerprint:
            raise RuntimeError('O arquivo da cena foi alterado externamente; recarregue antes de salvar.')

    linhas = data.get('linhas', [])
    data['linhas_totais'] = len(linhas)
    data['traduzidas'] = sum(1 for r in linhas if isinstance(r, dict) and str(r.get('pt', '')).strip())
    new_fp = write_json(json_path, data)

    # Atualiza ptbr/<cat>/<stem>.po preservando cabeçalho/msgid/msgctxt
    po_rel = data.get('po')
    if po_rel:
        po_path = ROOT / po_rel
        parsed = parse_po(po_path)
        by_ctx = {str(r['msgctxt']): str(r.get('pt', '')) for r in linhas if isinstance(r, dict)}
        changed = False
        for e in parsed['entries']:
            new_pt = by_ctx.get(str(e['msgctxt']), e['pt'])
            if new_pt != e['pt']:
                e['pt'] = new_pt
                changed = True
        if changed or not po_path.exists():
            write_po(po_path, parsed['header_lines'], parsed['source_bin'], parsed['entries'])

    propagated = 0
    if propagate:
        changes_map: dict[str, str] = {}
        for r in linhas:
            if not isinstance(r, dict):
                continue
            pt_val = str(r.get('pt', '') or '')
            en_val = str(r.get('en', '') or '')
            if pt_val.strip() and en_val and en_val not in SKIP_AUTO_PROPAGATE_EN and r.get('repeticoes', 1) > 1:
                changes_map[en_val] = pt_val
        if changes_map:
            propagated = propagate_translations(
                work_dir,
                changes_map,
                source_id=data.get('id', ''),
                mirror_071=(data.get('id') == 'historia/071'),
            )

    refresh_manifest(work_dir)
    return new_fp, propagated


def propagate_translations(work_dir: Path, en_to_pt: dict[str, str] | None = None,
                           source_id: str = '', mirror_071: bool = False) -> int:
    """Propaga traduções de strings repetidas para entradas vazias (e espelhos 071 -> 032/033)."""
    work_dir = Path(work_dir)
    manifest = read_json(work_dir / 'manifesto.json')
    if en_to_pt is None:
        # Coleta o mapeamento consensual de tudo que já está traduzido (preferindo cenas não-stub e 071)
        en_to_pt = {}
        priority_ids = ['historia/071', 'historia/030'] + [
            sid for sid, m in manifest['scenes'].items() if not m.get('is_stub')
        ]
        seen = set()
        for sid in priority_ids:
            if sid in seen or sid not in manifest['scenes']:
                continue
            seen.add(sid)
            sc = read_json(work_dir / manifest['scenes'][sid]['path'])
            for r in sc.get('linhas', []):
                en_v = str(r.get('en', ''))
                pt_v = str(r.get('pt', ''))
                if pt_v.strip() and en_v and en_v not in SKIP_AUTO_PROPAGATE_EN:
                    en_to_pt.setdefault(en_v, pt_v)

    if not en_to_pt:
        return 0

    updated_entries = 0
    for sid, meta in manifest['scenes'].items():
        if sid == source_id or sid == 'menus/interface__cmn__install':
            continue
        json_path = work_dir / meta['path']
        if not json_path.exists():
            continue
        sc = read_json(json_path)
        is_mirror = mirror_071 and sid in ('historia/032', 'historia/033')
        is_utf8 = sc.get('utf8', False)
        dirty = False

        for r in sc.get('linhas', []):
            en_v = str(r.get('en', ''))
            if en_v not in en_to_pt:
                continue
            cand = en_to_pt[en_v]
            cur = str(r.get('pt', '') or '')
            if cur and not is_mirror:
                continue
            if cur == cand:
                continue
            ok, _ = _can_fit_translation(en_v, cand, r.get('max_bytes'), is_utf8, sid)
            if not ok:
                continue
            kind = r.get('medida')
            if kind and medida.check(cand, kind):
                continue
            r['pt'] = cand
            updated_entries += 1
            dirty = True

        if dirty:
            sc['traduzidas'] = sum(1 for r in sc.get('linhas', []) if str(r.get('pt', '')).strip())
            write_json(json_path, sc)
            po_path = ROOT / meta['po']
            parsed = parse_po(po_path)
            by_ctx = {str(r['msgctxt']): str(r.get('pt', '')) for r in sc['linhas']}
            for e in parsed['entries']:
                e['pt'] = by_ctx.get(str(e['msgctxt']), e['pt'])
            write_po(po_path, parsed['header_lines'], parsed['source_bin'], parsed['entries'])

    if updated_entries:
        refresh_manifest(work_dir)
    return updated_entries


def check_tags(en: str, pt: str) -> str | None:
    """Verifica se códigos de controle obrigatórios (#C..., #CDEF, #RUBS, #[a][b]#) estão íntegros."""
    if '#[' in pt or ']#' in pt:
        # verifica balanceamento de #[a][b]#
        cleaned = re.sub(r'#\[[^\]]*\]\[[^\]]*\]#', '', pt)
        if '#[' in cleaned or ']#' in cleaned:
            return 'Seletor #[masc][fem]# malformado (precisa de exatamente 2 colchetes e fechar com #)'
    for pat in TAG_PATTERNS:
        en_tags = pat.findall(en)
        pt_tags = pat.findall(pt)
        if Counter(en_tags) != Counter(pt_tags):
            return f'Códigos de controle divergem do inglês: EN={en_tags} vs PT={pt_tags}'
    return None


def inspect_scene(data: dict, sid: str, json_path: Path | str, check_glossary_terms: list[tuple[str, str]] | None = None) -> list[Issue]:
    issues: list[Issue] = []
    if not isinstance(data, dict) or not isinstance(data.get('linhas'), list):
        return [Issue('Estrutura JSON inválida: falta a lista "linhas".', str(json_path), sid, severity='erro')]

    is_utf8 = bool(data.get('utf8', False))
    for r in data['linhas']:
        if not isinstance(r, dict):
            issues.append(Issue('Registro inválido dentro de "linhas".', str(json_path), sid))
            continue
        rid = r.get('id', '?')
        en = str(r.get('en', ''))
        pt = str(r.get('pt', '') or '')
        if not pt.strip():
            continue

        # 1. Glifos suportados pelo jogo (CP932 + acentos customizados)
        ok_bytes, byte_msg = _can_fit_translation(en, pt, r.get('max_bytes'), is_utf8, sid)
        if not ok_bytes:
            # Em EBOOT.BIN, slots que estouram são ignorados individualmente pelo build.py
            # mantendo a linha em inglês (aviso); já fixedbin/main rejeitam o arquivo inteiro.
            sev = 'aviso' if sid == 'sistema/eboot' and 'slot de EBOOT.BIN' in byte_msg else 'erro'
            msg = f'{byte_msg} (encurte para aplicar; senão fica em inglês)' if sev == 'aviso' else byte_msg
            issues.append(Issue(msg, str(json_path), sid, rid, 'pt', severity=sev))

        # 2. Caixa alta acentuada proibida (Â Ã Ê Ô Õ não existem na fonte)
        bad_caps = [ch for ch in ('Â', 'Ã', 'Ê', 'Ô', 'Õ') if ch in pt]
        if bad_caps and not is_utf8:
            issues.append(Issue(
                f'Caixa alta acentuada sem glifo no jogo ({"".join(bad_caps)}); use minúsculas ou texto sem acento.',
                str(json_path), sid, rid, 'pt', severity='erro',
            ))

        # 3. Medida em pixels / número de linhas
        kind = r.get('medida')
        if kind:
            for ln, w, limit, why in medida.check(pt, kind):
                if why == 'linhas demais':
                    issues.append(Issue(
                        f'Caixa "{kind}": {w} linhas (máximo {limit})',
                        str(json_path), sid, rid, 'pt', severity='erro',
                    ))
                else:
                    over = (w - limit + medida.ASCII_W - 1) // medida.ASCII_W
                    issues.append(Issue(
                        f'Linha {ln} estoura a caixa ({kind}): {w}px > {limit}px (~{over} caractere(s) a mais)',
                        str(json_path), sid, rid, 'pt', severity='erro',
                    ))

        # 4. Tags de controle e seletores #[masc][fem]#
        tag_err = check_tags(en, pt)
        if tag_err:
            issues.append(Issue(tag_err, str(json_path), sid, rid, 'pt', severity='erro'))

        # 5. Suspeitas de gênero do protagonista (aviso para revisão humana; ignora cabeçalho comum)
        if not data.get('is_stub') and sid != 'historia/main' and not r.get('comum'):
            suspects = genero.suspects(pt)
            if suspects:
                issues.append(Issue(
                    f'Possível gênero do protagonista sem #[masc][fem]#: {", ".join(suspects)}',
                    str(json_path), sid, rid, 'pt', severity='aviso',
                ))

    return issues


def apply_po_text_to_scene(data: dict, raw_po_text: str) -> dict:
    """Atualiza `data['linhas']` a partir do texto .po editado na aba bruta, proibindo alterações em msgctxt/msgid."""
    parsed = parse_po_text(raw_po_text)
    if not parsed['entries']:
        raise ValueError('Nenhuma entrada msgctxt válida encontrada no texto .po.')
    by_ctx = {str(e['msgctxt']): e for e in parsed['entries']}
    new_data = dict(data)
    new_linhas = []
    for r in data.get('linhas', []):
        ctx = str(r['msgctxt'])
        if ctx not in by_ctx:
            raise ValueError(f'msgctxt "{ctx}" foi removido do .po; operação cancelada para evitar corrupção.')
        ent = by_ctx[ctx]
        if ent['en'] != r['en']:
            raise ValueError(f'msgid de msgctxt "{ctx}" foi alterado; nunca altere msgid/msgctxt.')
        nr = dict(r)
        nr['pt'] = ent['pt']
        new_linhas.append(nr)
    new_data['linhas'] = new_linhas
    new_data['traduzidas'] = sum(1 for r in new_linhas if str(r.get('pt', '')).strip())
    return new_data


def save_log(work_dir: Path, inspection: Inspection, extra: str = '') -> Path:
    from datetime import datetime
    logs_dir = Path(work_dir) / 'logs'
    logs_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_path = logs_dir / f'validacao_{stamp}.log'
    lines = [
        f'Data: {datetime.now().isoformat(timespec="seconds")}',
        f'Erros: {len(inspection.errors)} | Avisos: {len(inspection.warnings)}',
    ]
    if extra:
        lines.append(extra)
    lines.append('')
    for iss in inspection.issues:
        lines.append(f'[{iss.severity.upper()}] {iss.scene} #{iss.row_id}: {iss.message}')
    atomic_write(log_path, ('\n'.join(lines) + '\n').encode('utf-8'))
    return log_path


def inspect_project(work_dir: Path = WORK) -> Inspection:
    """Valida todos os 292 scripts em `trabalho/`."""
    work_dir = Path(work_dir)
    manifest = refresh_manifest(work_dir)
    issues: list[Issue] = []

    for sid, meta in manifest.get('scenes', {}).items():
        json_path = work_dir / meta['path']
        if not json_path.exists():
            issues.append(Issue('Arquivo JSON ausente em trabalho/', str(json_path), sid, severity='erro'))
            continue
        try:
            data = read_json(json_path)
        except Exception as exc:
            issues.append(Issue(f'JSON inválido: {exc}', str(json_path), sid, severity='erro'))
            continue
        issues.extend(inspect_scene(data, sid, json_path))

    return Inspection(manifest=manifest, issues=issues)


def main() -> None:
    if '--build-work' in sys.argv:
        force = '--force' in sys.argv
        man = build_work_tree(WORK, force_all=force)
        print(f"trabalho/: {man['scene_count']} scripts | {man['translated_count']}/{man['line_count']} linhas traduzidas")
    elif '--sync-repeats' in sys.argv:
        n = propagate_translations(WORK)
        print(f"Propagadas {n} entradas idênticas.")
    elif '--validate' in sys.argv:
        res = inspect_project(WORK)
        print(f"Validados {res.manifest['scene_count']} scripts | {len(res.errors)} erro(s) | {len(res.warnings)} aviso(s)")
        for iss in res.errors[:30]:
            print(f"  [ERRO] {iss.scene} #{iss.row_id}: {iss.message}")
    else:
        print('Uso: python tools/scripts_ccc.py [--build-work [--force] | --sync-repeats | --validate]')


if __name__ == '__main__':
    main()
