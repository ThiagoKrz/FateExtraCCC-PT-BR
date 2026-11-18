"""Recursos extras de equipe para o painel CCC: busca global e conferência de glossário."""
from __future__ import annotations

import json
from pathlib import Path
import re
import tkinter as tk
from tkinter import ttk

TAG_STRIP_RE = re.compile(r'#C\d{8}#?|#CDEF|#RUBS|#RUBE|#REND|#ROFS[-\d]\d{3}')


def _clean_for_match(text: str) -> str:
    return TAG_STRIP_RE.sub('', text or '')


def _extract_pt_options(raw_pt: str) -> list[str]:
    """Extrai variantes válidas em PT-BR de uma definição de glossário (ex.: 'Mestre / Mestra')."""
    base = re.sub(r'\([^)]*\)', '', raw_pt or '')
    opts = []
    for part in re.split(r'\s*/\s*', base):
        p = part.strip()
        if p and len(p) >= 2:
            opts.append(p.casefold())
    return opts


def load_ccc_glossary_terms(standards_dir: Path) -> list[tuple[str, str]]:
    """Carrega termos de GLOSSARIO_TYPEMOON_OPERACIONAL.json e GLOSSARIO_CCC_OPERACIONAL.json."""
    terms: dict[str, str] = {}

    tm_path = standards_dir / 'GLOSSARIO_TYPEMOON_OPERACIONAL.json'
    if tm_path.exists():
        tm_data = json.loads(tm_path.read_text(encoding='utf-8-sig'))
        block = tm_data.get('glossario_geral_type_moon')
        if isinstance(block, dict):
            for en_term, pt_term in block.items():
                if en_term.startswith('_') or not isinstance(pt_term, str):
                    continue
                if re.search(r'[A-Za-z]', en_term) and len(en_term.strip()) >= 3 and pt_term.strip():
                    terms[en_term.strip()] = pt_term.strip()

    ccc_path = standards_dir / 'GLOSSARIO_CCC_OPERACIONAL.json'
    if ccc_path.exists():
        ccc_data = json.loads(ccc_path.read_text(encoding='utf-8-sig'))
        block = ccc_data.get('glossario_ccc')
        if isinstance(block, dict):
            for en_term, entry in block.items():
                if en_term.startswith('_') or en_term.startswith('('):
                    continue
                pt_val = entry.get('pt', '') if isinstance(entry, dict) else (entry if isinstance(entry, str) else '')
                if isinstance(pt_val, str) and pt_val.strip() and len(en_term.strip()) >= 3:
                    terms[en_term.strip()] = pt_val.strip()

    return sorted(terms.items(), key=lambda x: -len(x[0]))


def check_scene_glossary(
    data: dict,
    sid: str,
    json_path: Path,
    terms: list[tuple[str, str]],
    issue_cls,
) -> list:
    issues = []
    if not isinstance(data, dict) or not isinstance(data.get('linhas'), list):
        return issues

    compiled = [
        (en_t, pt_t, _extract_pt_options(pt_t), re.compile(r'\b' + re.escape(en_t) + r'\b', re.IGNORECASE))
        for en_t, pt_t in terms
        if '/' not in en_t and '->' not in en_t and len(en_t) >= 4
    ]
    forbidden_pt = [
        (re.compile(r'\btaumaturg(?:ia|o|a)\b', re.IGNORECASE), 'Proibido "taumaturgia": use "magia" (Magecraft).'),
        (re.compile(r'\bfeiti[çc]aria\b', re.IGNORECASE), 'Proibido "feitiçaria": use "magia" (Magecraft) ou "Magia Verdadeira" (True Magic).'),
        (re.compile(r'\bOrdem de Comando\b', re.IGNORECASE), 'Use "Selo de Comando" em vez de "Ordem de Comando".'),
    ]

    for rec in data['linhas']:
        if not isinstance(rec, dict):
            continue
        en_raw = str(rec.get('en', ''))
        pt_raw = str(rec.get('pt', '') or '')
        if not en_raw or not pt_raw.strip():
            continue

        en_clean = _clean_for_match(en_raw)
        pt_clean = _clean_for_match(pt_raw)
        pt_fold = pt_clean.casefold()

        for rx_bad, msg_bad in forbidden_pt:
            if rx_bad.search(pt_clean):
                issues.append(issue_cls(msg_bad, str(json_path), sid, rec.get('id'), 'pt', severity='erro'))

        for en_t, pt_t, opts, rx in compiled:
            if rx.search(en_clean):
                if opts and not any(opt in pt_fold for opt in opts):
                    issues.append(issue_cls(
                        f'Glossário: "{en_t}" → esperado "{pt_t}"',
                        str(json_path),
                        sid,
                        rec.get('id'),
                        'pt',
                        severity='aviso',
                    ))
    return issues


def open_global_search(panel, tree_scrollbars_fn) -> None:
    win = tk.Toplevel(panel.root)
    win.title('Busca global — Fate/Extra CCC PT-BR')
    win.geometry('980x580')
    p = getattr(panel, 'palette', {})
    if p:
        win.configure(background=p['bg'])

    top = ttk.Frame(win, padding=10)
    top.pack(fill='x')
    ttk.Label(top, text='Buscar em todo o projeto (PT-BR, EN, msgctxt ou ID):', style='Muted.TLabel').pack(side='left')
    query_var = tk.StringVar()
    entry = ttk.Entry(top, textvariable=query_var)
    entry.pack(side='left', fill='x', expand=True, padx=8)

    skip_stubs_var = tk.BooleanVar(value=True)
    ttk.Checkbutton(top, text='Ignorar mapas base (81)', variable=skip_stubs_var).pack(side='left', padx=(0, 8))

    body = ttk.Frame(win, padding=(10, 0, 10, 10))
    body.pack(fill='both', expand=True)
    tree = ttk.Treeview(body, columns=('scene', 'id', 'ctx', 'text'), show='headings', selectmode='browse')
    tree.heading('scene', text='Cena / Arquivo')
    tree.heading('id', text='Linha')
    tree.heading('ctx', text='msgctxt')
    tree.heading('text', text='Trecho encontrado (PT-BR ou EN)')
    tree.column('scene', width=260, stretch=False)
    tree.column('id', width=65, stretch=False)
    tree.column('ctx', width=85, stretch=False)
    tree.column('text', width=530)
    tree_scrollbars_fn(body, tree)

    status_var = tk.StringVar(value='Digite pelo menos 2 caracteres e pressione Enter.')
    ttk.Label(win, textvariable=status_var, style='Muted.TLabel', padding=(10, 0, 10, 8)).pack(anchor='w')

    hits: dict[str, tuple[str, int | str | None]] = {}

    def run_search(_=None):
        q = query_var.get().strip().casefold()
        tree.delete(*tree.get_children())
        hits.clear()
        if len(q) < 2:
            status_var.set('Digite pelo menos 2 caracteres.')
            return
        count = 0
        limit = 500
        for sid, meta in panel.manifest['scenes'].items():
            if skip_stubs_var.get() and meta.get('is_stub'):
                continue
            scene_path = panel.work / meta['path']
            if not scene_path.exists():
                continue
            try:
                scene_data = json.loads(scene_path.read_text(encoding='utf-8-sig'))
            except Exception:
                continue
            title = meta.get('title', sid)
            for rec in scene_data.get('linhas', []):
                if not isinstance(rec, dict):
                    continue
                hay = ' '.join(str(rec.get(k, '')) for k in ('id', 'msgctxt', 'pt', 'en')).casefold()
                if q in hay:
                    pt_v = str(rec.get('pt', '') or '')
                    en_v = str(rec.get('en', '') or '')
                    prev = (f'[PT] {pt_v}' if pt_v else f'[EN] {en_v}').replace('\n', ' ↵ ')
                    iid = tree.insert('', 'end', values=(f'{title} [{sid}]', rec.get('id', ''), rec.get('msgctxt', ''), prev))
                    hits[iid] = (sid, rec.get('id'))
                    count += 1
                    if count >= limit:
                        break
            if count >= limit:
                break
        status_var.set(f'{count} ocorrência(s) encontrada(s)' + (' (limite de 500 atingido)' if count >= limit else '') + ' · Duplo clique para abrir')

    def on_jump(_=None):
        sel = tree.selection()
        if not sel:
            return
        sid, rid = hits.get(sel[0], (None, None))
        if sid and panel.open_scene(sid, rid):
            panel.pt.focus_set()
            win.destroy()

    ttk.Button(top, text='Buscar', command=run_search).pack(side='left')
    entry.bind('<Return>', run_search)
    tree.bind('<Double-1>', on_jump)
    entry.focus_set()
