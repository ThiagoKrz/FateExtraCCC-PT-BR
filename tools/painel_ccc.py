"""Painel local de tradução e revisão — Fate/Extra CCC PT-BR.

Organiza os 292 arquivos `.po` em capítulos (`trabalho/`), oferece busca
global, checagem de glossário, régua de pixels/bytes em tempo real, alerta de
gênero `#[masc][fem]#`, edição direta do `.po` e compilação de ISO via `build.py`.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import queue
import re
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import fatetext
import genero
import medida
import painel_extras as extras
import scripts_ccc as scripts

TAGS_EXTRACT_RE = re.compile(
    r'#C\d{8}#?|#CDEF|#RUBS.*?#RUBE|#REND|#ROFS[-\d]\d{3}|'
    r'#\[[^\]]*\]\[[^\]]*\]#|#FAMILY|#GIVEN|#NICK|#SVT|#TITM\d{4}|#VAL\d{3}|#TVAL\d{2}|#SP\d{2}|#T\d'
)


class ReviewPanel(ttk.Frame):
    def __init__(self, root: tk.Tk, work: Path = scripts.WORK):
        super().__init__(root, padding=12)
        self.root = root
        self.work = Path(work).resolve()
        if not (self.work / 'manifesto.json').exists():
            scripts.build_work_tree(self.work)
        self.manifest = scripts.read_json(self.work / 'manifesto.json')
        self.data: dict | None = None
        self.current_scene: str | None = None
        self.path: Path | None = None
        self.po_path: Path | None = None
        self.fingerprint: str | None = None
        self.current_index: int | None = None
        self.visible_indices: list[int] = []
        self.dirty = False
        self.raw_dirty = False
        self.rendering = False
        self.busy = False
        self.messages: queue.Queue = queue.Queue()
        self.issue_map: dict[str, scripts.Issue] = {}
        self.scene_nodes: dict[str, str] = {}
        self.group_nodes: dict[str, str] = {}
        self.autosave_job = None

        try:
            self.theme = scripts.read_json(self.work / '.preferencias.json').get('tema', 'escuro')
        except (OSError, ValueError):
            self.theme = 'escuro'
        if self.theme not in ('claro', 'escuro'):
            self.theme = 'escuro'

        self.pack(fill='both', expand=True)
        self._build()
        self.apply_theme()
        self.root.title('Fate/Extra CCC PT-BR — Painel de Tradução e Revisão')
        self.root.geometry('1480x960')
        self.root.minsize(1100, 760)
        self.root.protocol('WM_DELETE_WINDOW', self.close)
        self.root.bind('<Control-s>', lambda _: self.save_current())
        self.root.bind('<F5>', lambda _: self.run_validation())
        self.root.bind('<Control-Return>', lambda _: self.run_validation(build_mode='full'))
        self.root.bind('<Control-Shift-F>', lambda _: self.open_global_search())
        self.root.after(80, self.poll)

        first = self._pick_initial_scene()
        if first:
            self.open_scene(first)
        self.root.after(450, self.run_validation)

    def _pick_initial_scene(self) -> str | None:
        if 'historia/007' in self.scene_nodes:
            return 'historia/007'
        return next(iter(self.scene_nodes), None)

    def _progress_summary_text(self) -> str:
        tot = self.manifest.get('line_count', 0)
        tr = self.manifest.get('translated_count', 0)
        sc = self.manifest.get('scene_count', 0)
        pct = (100.0 * tr / tot) if tot else 0.0
        return (
            f"Painel de tradução e revisão  •  {tr:,}/{tot:,} linhas ({pct:.1f}%) em {sc} arquivos"
            .replace(',', '.')
        )

    def _build(self) -> None:
        self.style = ttk.Style(self.root)
        self.style.theme_use('clam')

        # Cabeçalho
        header = ttk.Frame(self)
        header.pack(fill='x', pady=(2, 10))
        heading = ttk.Frame(header)
        heading.pack(side='left')
        ttk.Label(heading, text='Fate/Extra CCC PT-BR', style='Title.TLabel').pack(anchor='w')
        self.header_summary = tk.StringVar(value=self._progress_summary_text())
        ttk.Label(heading, textvariable=self.header_summary, style='Muted.TLabel').pack(anchor='w', pady=(2, 0))

        self.theme_button = ttk.Button(header, command=self.toggle_theme)
        self.theme_button.pack(side='right', anchor='n', pady=6)
        self.validation_state = tk.StringVar(value='Aguardando validação')
        self.validation_label = ttk.Label(header, textvariable=self.validation_state, style='Muted.TLabel')
        self.validation_label.pack(side='right', padx=16, pady=12, anchor='n')

        # Barra de ações principal
        actions = ttk.Frame(self)
        actions.pack(fill='x', pady=(0, 8))
        self.save_button = ttk.Button(actions, text='Salvar cena  Ctrl+S', command=self.save_current)
        self.save_button.pack(side='left')
        self.validate_button = ttk.Button(actions, text='Validar projeto  F5', command=self.run_validation)
        self.validate_button.pack(side='left', padx=(6, 0))
        ttk.Button(actions, text='Sincronizar repetidas', command=self.run_sync_repeats).pack(side='left', padx=(6, 0))
        ttk.Button(actions, text='Busca global  Ctrl+Shift+F', command=self.open_global_search).pack(side='left', padx=(6, 0))
        ttk.Button(actions, text='Conferir glossário', command=self.check_glossary).pack(side='left', padx=(6, 0))

        self.propagate_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            actions,
            text='Propagar repetidas ao salvar',
            variable=self.propagate_var,
        ).pack(side='left', padx=(12, 0))

        self.generate_full_btn = ttk.Button(
            actions,
            text='Gerar ISO completa  Ctrl+Enter',
            command=lambda: self.run_validation(build_mode='full'),
            style='Primary.TButton',
        )
        self.generate_full_btn.pack(side='right')
        self.generate_only_btn = ttk.Button(
            actions,
            text='Testar cena (--only)',
            command=lambda: self.run_validation(build_mode='only'),
        )
        self.generate_only_btn.pack(side='right', padx=(0, 6))

        # Barra informativa de ISO / glossários
        iso_bar = ttk.Frame(self)
        iso_bar.pack(fill='x', pady=(0, 10))
        ttk.Label(
            iso_bar,
            text=f'Saída ISO: {scripts.ROOT / "output" / "ccc-ptbr.iso"}   •   Sincronizado com ptbr/*.po e trabalho/*.json',
            style='Muted.TLabel',
        ).pack(side='left')

        # Área principal dividida
        workspace = ttk.Panedwindow(self, orient='vertical')
        workspace.pack(fill='both', expand=True)
        main = ttk.Panedwindow(workspace, orient='horizontal')
        workspace.add(main, weight=5)

        left = ttk.Frame(main, padding=(10, 10), style='Surface.TFrame')
        right = ttk.Frame(main, padding=(10, 0, 0, 0))
        main.add(left, weight=1)
        main.add(right, weight=4)

        # Painel esquerdo: árvore de capítulos e cenas
        ttk.Label(left, text='Capítulos, rotas e arquivos', style='Section.TLabel').pack(anchor='w', pady=(0, 6))
        self.scene_filter = tk.StringVar()
        ttk.Entry(left, textvariable=self.scene_filter).pack(fill='x', pady=(0, 6))
        self.scene_filter.trace_add('write', lambda *_: self.populate_scene_tree())

        self.hide_stubs_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            left,
            text='Ocultar mapas base sem falas próprias (81)',
            variable=self.hide_stubs_var,
            command=self.populate_scene_tree,
        ).pack(anchor='w', pady=(0, 6))

        scene_frame = ttk.Frame(left)
        scene_frame.pack(fill='both', expand=True)
        self.scene_tree = ttk.Treeview(scene_frame, show='tree', selectmode='browse')
        self.scene_tree.column('#0', width=340, minwidth=220)
        self.tree_scrollbars(scene_frame, self.scene_tree)
        self.populate_scene_tree()
        self.scene_tree.bind('<<TreeviewSelect>>', self.on_scene_select)

        # Painel direito: Notebook (Falas da cena | Arquivo .po bruto)
        self.notebook = ttk.Notebook(right)
        self.notebook.pack(fill='both', expand=True)
        editor = ttk.Frame(self.notebook, padding=10, style='Surface.TFrame')
        raw_frame = ttk.Frame(self.notebook, padding=10, style='Surface.TFrame')
        self.notebook.add(editor, text='Falas e textos da cena')
        self.notebook.add(raw_frame, text='Arquivo .po bruto')

        # Barra de busca + filtro da cena
        searchbar = ttk.Frame(editor)
        searchbar.pack(fill='x')
        ttk.Label(searchbar, text='Buscar na cena', style='Muted.TLabel').pack(side='left')
        self.search = tk.StringVar()
        ttk.Entry(searchbar, textvariable=self.search).pack(side='left', fill='x', expand=True, padx=(8, 10))
        self.search.trace_add('write', lambda *_: self.fill_rows())

        ttk.Label(searchbar, text='Mostrar:', style='Muted.TLabel').pack(side='left')
        self.row_filter_var = tk.StringVar(value='Todas')
        row_filter_cb = ttk.Combobox(
            searchbar,
            textvariable=self.row_filter_var,
            values=['Todas', 'Exclusivas da cena', 'Faltando tradução', 'Traduzidas'],
            state='readonly',
            width=19,
        )
        row_filter_cb.pack(side='left', padx=(6, 0))
        row_filter_cb.bind('<<ComboboxSelected>>', lambda *_: self.fill_rows())

        # Tabela de linhas da cena
        rows_frame = ttk.Frame(editor)
        rows_frame.pack(fill='both', expand=True, pady=(8, 8))
        self.rows_tree = ttk.Treeview(
            rows_frame,
            columns=('id', 'ctx', 'tipo', 'en', 'pt'),
            show='headings',
            height=8,
            selectmode='browse',
        )
        self.rows_tree.heading('id', text='#')
        self.rows_tree.heading('ctx', text='msgctxt')
        self.rows_tree.heading('tipo', text='Tipo / Limite')
        self.rows_tree.heading('en', text='Inglês (original)')
        self.rows_tree.heading('pt', text='Português brasileiro')
        self.rows_tree.column('id', width=52, stretch=False, anchor='e')
        self.rows_tree.column('ctx', width=76, stretch=False, anchor='e')
        self.rows_tree.column('tipo', width=128, stretch=False)
        self.rows_tree.column('en', width=290)
        self.rows_tree.column('pt', width=340)
        self.tree_scrollbars(rows_frame, self.rows_tree)
        self.rows_tree.bind('<<TreeviewSelect>>', self.on_row_select)

        # Detalhes e caixas de texto
        self.line_label = ttk.Label(editor, text='', style='Section.TLabel')
        self.line_label.pack(anchor='w', pady=(2, 4))

        self.en = self.make_text(editor, 'Inglês · referência imutável', 4, False)

        # Barra de botões rápidos do editor PT-BR
        quick_bar = ttk.Frame(editor)
        quick_bar.pack(fill='x', pady=(6, 2))
        ttk.Label(quick_bar, text='Português brasileiro', style='Section.TLabel').pack(side='left')
        ttk.Button(quick_bar, text='Limpar', command=self.clear_pt).pack(side='right')
        ttk.Button(quick_bar, text='Copiar EN', command=self.copy_en_to_pt).pack(side='right', padx=(0, 6))
        ttk.Button(quick_bar, text='Copiar códigos EN', command=self.insert_missing_tags).pack(side='right', padx=(0, 6))
        ttk.Button(quick_bar, text='Inserir #[masc][fem]#', command=self.insert_gender_selector).pack(side='right', padx=(0, 6))

        self.pt = ScrolledText(editor, width=40, height=5, wrap='word', undo=True, font=('Segoe UI', 11),
                               padx=12, pady=8, spacing1=2, spacing3=3)
        self.pt.pack(fill='both', expand=False)
        self.pt.bind('<<Modified>>', self.on_pt_modified)

        # Régua de pixels / bytes / gênero em tempo real
        self.ruler_var = tk.StringVar(value='')
        self.ruler_label = ttk.Label(editor, textvariable=self.ruler_var, style='Muted.TLabel')
        self.ruler_label.pack(anchor='w', pady=(5, 0))

        # Aba 2: Arquivo .po bruto
        raw_actions = ttk.Frame(raw_frame)
        raw_actions.pack(fill='x', pady=(0, 6))
        ttk.Button(raw_actions, text='Aplicar .po ao editor e salvar', command=self.apply_raw_po).pack(side='left')
        ttk.Button(raw_actions, text='Recarregar .po do disco', command=self.reload_scene).pack(side='left', padx=8)
        ttk.Label(raw_actions, text='Só edite msgstr "...". Nunca altere msgctxt ou msgid.', style='Muted.TLabel').pack(side='left')
        self.raw = ScrolledText(raw_frame, wrap='none', undo=True, font=('Consolas', 10))
        self.raw.pack(fill='both', expand=True)
        self.raw.bind('<<Modified>>', self.on_raw_modified)
        self.notebook.bind('<<NotebookTabChanged>>', self.on_tab_changed)

        # Painel inferior: Validação, avisos e logs
        bottom = ttk.Frame(workspace, padding=(10, 8), style='Surface.TFrame')
        workspace.add(bottom, weight=1)
        log_header = ttk.Frame(bottom)
        log_header.pack(fill='x', pady=(0, 6))
        ttk.Label(log_header, text='Validação, glossário e avisos', style='Section.TLabel').pack(side='left')
        ttk.Label(log_header, text='Duplo clique para ir diretamente à linha', style='Muted.TLabel').pack(side='right')

        issues_frame = ttk.Frame(bottom)
        issues_frame.pack(fill='both', expand=True)
        self.issues = ttk.Treeview(issues_frame, columns=('id', 'scene', 'field', 'message'), show='headings', height=4)
        for key, title, width in [('id', 'Linha', 65), ('scene', 'Arquivo', 210), ('field', 'Campo', 65), ('message', 'Mensagem', 740)]:
            self.issues.heading(key, text=title)
            self.issues.column(key, width=width, stretch=(key == 'message'))
        self.tree_scrollbars(issues_frame, self.issues)
        self.issues.bind('<Double-1>', self.jump_issue)

        log_actions = ttk.Frame(bottom)
        log_actions.pack(fill='x', pady=(5, 0))
        ttk.Button(log_actions, text='Ir para o item', command=self.jump_issue).pack(side='left')
        ttk.Button(log_actions, text='Atualizar planilha (.xlsx)', command=self.update_spreadsheet).pack(side='left', padx=8)
        ttk.Button(log_actions, text='Recarregar cena do disco', command=self.reload_scene).pack(side='left')
        ttk.Button(log_actions, text='Abrir pasta de logs', command=self.open_logs).pack(side='right')

        # Rodapé
        footer = ttk.Frame(self)
        footer.pack(fill='x', pady=(8, 0))
        self.status = tk.StringVar(value='Pronto.')
        status_label = ttk.Label(footer, textvariable=self.status, anchor='w', style='Muted.TLabel', wraplength=1100)
        status_label.pack(side='left', fill='x', expand=True)
        footer.bind('<Configure>', lambda event: status_label.configure(wraplength=max(400, event.width - 150)))
        self.progress = ttk.Progressbar(footer, mode='indeterminate', length=130)
        self.progress.pack(side='right', padx=(12, 0))
        self.root.after_idle(lambda: main.sashpos(0, 340))

    @staticmethod
    def tree_scrollbars(parent: ttk.Frame, tree: ttk.Treeview) -> None:
        vertical = ttk.Scrollbar(parent, orient='vertical', command=tree.yview)
        horizontal = ttk.Scrollbar(parent, orient='horizontal', command=tree.xview)
        tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        tree.grid(row=0, column=0, sticky='nsew')
        vertical.grid(row=0, column=1, sticky='ns')
        horizontal.grid(row=1, column=0, sticky='ew')
        parent.rowconfigure(0, weight=1)
        parent.columnconfigure(0, weight=1)

    def make_text(self, parent: ttk.Frame, title: str, height: int, editable: bool, font=('Segoe UI', 11)) -> ScrolledText:
        ttk.Label(parent, text=title, style='Section.TLabel' if editable else 'Muted.TLabel').pack(anchor='w', pady=(2, 3))
        widget = ScrolledText(parent, width=30, height=height, wrap='word', undo=editable, font=font,
                              padx=12, pady=8, spacing1=2, spacing3=3)
        widget.pack(fill='x', expand=False)
        if not editable:
            widget.configure(state='disabled')
        return widget

    def set_text(self, widget: ScrolledText, text: str, readonly: bool = False) -> None:
        widget.configure(state='normal')
        widget.delete('1.0', 'end')
        widget.insert('1.0', text)
        widget.edit_modified(False)
        if readonly:
            widget.configure(state='disabled')

    def _scene_label(self, meta: dict) -> str:
        tot = meta['linhas']
        tr = meta['traduzidas']
        pct = (100.0 * tr / tot) if tot else 0.0
        tag = meta['id'].split('/', 1)[1]
        return f"{meta['titulo']} [{tag}] ({tr}/{tot} · {pct:.0f}%)"

    def populate_scene_tree(self) -> None:
        query = self.scene_filter.get().strip().casefold() if hasattr(self, 'scene_filter') else ''
        hide_stubs = self.hide_stubs_var.get() if hasattr(self, 'hide_stubs_var') else True
        prev_selected = self.current_scene

        self.scene_tree.delete(*self.scene_tree.get_children())
        self.scene_nodes.clear()
        self.group_nodes.clear()

        grp_meta = {g['id']: g for g in self.manifest.get('groups', [])}
        groups_created: dict[str, str] = {}

        ordered_scenes = sorted(
            self.manifest['scenes'].values(),
            key=lambda m: (
                next((i for i, g in enumerate(self.manifest['groups']) if g['id'] == m['grupo']), 99),
                m.get('ordem', 9999),
                m['id'],
            ),
        )

        for meta in ordered_scenes:
            if hide_stubs and meta.get('is_stub') and not query:
                continue
            gid = meta['grupo']
            gm = grp_meta.get(gid, {})
            g_label = gm.get('rotulo', gid)
            sid = meta['id']
            if query and (
                query not in meta['titulo'].casefold()
                and query not in sid.casefold()
                and query not in g_label.casefold()
            ):
                continue
            if gid not in groups_created:
                g_tot = gm.get('linhas', 0)
                g_tr = gm.get('traduzidas', 0)
                g_pct = (100.0 * g_tr / g_tot) if g_tot else 0.0
                g_txt = f"{g_label}  ({g_tr:,}/{g_tot:,} · {g_pct:.0f}%)".replace(',', '.')
                node_g = self.scene_tree.insert('', 'end', text=g_txt, open=bool(query) or gid == '00_prologo')
                groups_created[gid] = node_g
                self.group_nodes[gid] = node_g

            node_s = self.scene_tree.insert(
                groups_created[gid],
                'end',
                text=self._scene_label(meta),
                values=(sid,),
            )
            self.scene_nodes[sid] = node_s

        if prev_selected and prev_selected in self.scene_nodes:
            self.scene_tree.selection_set(self.scene_nodes[prev_selected])
            self.scene_tree.see(self.scene_nodes[prev_selected])

    def _update_tree_counters(self) -> None:
        self.manifest = scripts.read_json(self.work / 'manifesto.json')
        self.header_summary.set(self._progress_summary_text())
        grp_meta = {g['id']: g for g in self.manifest.get('groups', [])}
        for gid, node_g in self.group_nodes.items():
            if self.scene_tree.exists(node_g) and gid in grp_meta:
                gm = grp_meta[gid]
                g_tot = gm.get('linhas', 0)
                g_tr = gm.get('traduzidas', 0)
                g_pct = (100.0 * g_tr / g_tot) if g_tot else 0.0
                self.scene_tree.item(
                    node_g,
                    text=f"{gm['rotulo']}  ({g_tr:,}/{g_tot:,} · {g_pct:.0f}%)".replace(',', '.'),
                )
        for sid, node_s in self.scene_nodes.items():
            if self.scene_tree.exists(node_s) and sid in self.manifest['scenes']:
                self.scene_tree.item(node_s, text=self._scene_label(self.manifest['scenes'][sid]))

    def toggle_theme(self) -> None:
        self.theme = 'claro' if self.theme == 'escuro' else 'escuro'
        self.apply_theme()
        try:
            scripts.atomic_write(self.work / '.preferencias.json', (json.dumps({'tema': self.theme}) + '\n').encode('utf-8'))
        except OSError as exc:
            self.status.set(f'Tema aplicado, mas não foi possível salvar a preferência: {exc}')

    def apply_theme(self) -> None:
        dark = self.theme == 'escuro'
        p = ({
            'bg': '#171d2a', 'surface': '#20293a', 'field': '#273247', 'readonly': '#1d2636',
            'text': '#e6edf8', 'muted': '#acb8cd', 'border': '#3b4860', 'accent': '#b5c5ff',
            'button': '#546db5', 'hover': '#647ec8', 'selected': '#3d527b', 'error': '#ffacb1', 'ok': '#98d5ba',
        } if dark else {
            'bg': '#edf1f7', 'surface': '#ffffff', 'field': '#ffffff', 'readonly': '#f1f4f9',
            'text': '#25324a', 'muted': '#5e6d83', 'border': '#cbd4e3', 'accent': '#405ba0',
            'button': '#405da2', 'hover': '#344e8d', 'selected': '#dce5fa', 'error': '#af303e', 'ok': '#27694e',
        })
        self.palette = p
        style = self.style
        self.root.configure(background=p['bg'])
        style.configure('.', font=('Segoe UI', 10), background=p['bg'], foreground=p['text'],
                        bordercolor=p['border'], lightcolor=p['border'], darkcolor=p['border'],
                        troughcolor=p['bg'], focuscolor=p['accent'])
        style.configure('TFrame', background=p['bg'])
        style.configure('Surface.TFrame', background=p['surface'])
        style.configure('TLabel', background=p['surface'], foreground=p['text'])
        style.configure('Muted.TLabel', foreground=p['muted'], background=p['bg'])
        style.configure('Section.TLabel', font=('Segoe UI', 10, 'bold'), foreground=p['accent'], background=p['surface'])
        style.configure('Title.TLabel', font=('Segoe UI', 22, 'bold'), foreground=p['text'], background=p['bg'])
        style.configure('Error.TLabel', background=p['bg'], foreground=p['error'])
        style.configure('Success.TLabel', background=p['bg'], foreground=p['ok'])
        style.configure('Warn.TLabel', background=p['surface'], foreground='#edc784' if dark else '#845400')
        style.configure('RulerErr.TLabel', background=p['surface'], foreground=p['error'])
        style.configure('RulerOk.TLabel', background=p['surface'], foreground=p['ok'])
        style.configure('TButton', padding=(10, 6), background=p['surface'], foreground=p['text'], borderwidth=1)
        style.map('TButton', background=[('active', p['field']), ('pressed', p['selected'])], foreground=[('disabled', p['muted'])])
        style.configure('Primary.TButton', background=p['button'], foreground='#ffffff', font=('Segoe UI', 10, 'bold'))
        style.map('Primary.TButton', background=[('disabled', p['border']), ('active', p['hover']), ('pressed', p['button'])],
                  foreground=[('disabled', p['muted']), ('!disabled', '#ffffff')])
        style.configure('TCheckbutton', background=p['bg'], foreground=p['text'])
        style.map('TCheckbutton', background=[('active', p['bg'])])
        style.configure('TEntry', fieldbackground=p['field'], foreground=p['text'], padding=5, insertcolor=p['text'])
        style.configure('TCombobox', fieldbackground=p['field'], foreground=p['text'], background=p['surface'])
        style.configure('Treeview', background=p['surface'], fieldbackground=p['surface'], foreground=p['text'],
                        rowheight=26, font=('Segoe UI', 9.5), borderwidth=0)
        style.map('Treeview', background=[('selected', p['selected'])], foreground=[('selected', p['text'])])
        style.configure('Treeview.Heading', background=p['field'], foreground=p['muted'], font=('Segoe UI', 9, 'bold'),
                        padding=(6, 5), relief='flat')
        style.configure('TNotebook', background=p['bg'], borderwidth=0, tabmargins=(0, 0, 0, 0))
        style.configure('TNotebook.Tab', background=p['bg'], foreground=p['muted'], padding=(16, 8))
        style.map('TNotebook.Tab', background=[('selected', p['surface']), ('active', p['field'])],
                  foreground=[('selected', p['text'])])
        style.configure('TPanedwindow', background=p['bg'])
        style.configure('Sash', sashthickness=7, background=p['bg'])
        style.configure('TScrollbar', background=p['border'], arrowcolor=p['muted'], troughcolor=p['surface'], borderwidth=0)
        style.configure('TProgressbar', background=p['button'], troughcolor=p['bg'], borderwidth=0)

        for widget in (self.en, self.pt, self.raw):
            readonly = (widget is self.en)
            widget.configure(
                background=p['readonly'] if readonly else p['field'],
                foreground=p['text'],
                insertbackground=p['text'],
                selectbackground=p['selected'],
                selectforeground=p['text'],
                relief='flat',
                borderwidth=0,
                highlightthickness=1,
                highlightbackground=p['border'],
                highlightcolor=p['accent'],
            )
            widget.frame.configure(background=p['surface'])
            widget.vbar.configure(background=p['border'], activebackground=p['selected'],
                                  troughcolor=p['surface'], borderwidth=0, highlightthickness=0)

        self.issues.tag_configure('erro', foreground=p['error'])
        self.issues.tag_configure('ok', foreground=p['ok'])
        self.issues.tag_configure('aviso', foreground='#edc784' if dark else '#845400')
        self.theme_button.configure(text='Modo claro' if dark else 'Modo noturno')
        if os.name == 'nt':
            self.root.after_idle(self.theme_titlebar)

    def theme_titlebar(self) -> None:
        try:
            import ctypes
            user32 = ctypes.windll.user32
            user32.GetParent.restype = ctypes.c_void_p
            user32.GetParent.argtypes = [ctypes.c_void_p]
            handle = user32.GetParent(self.root.winfo_id())
            value = ctypes.c_int(self.theme == 'escuro')
            ctypes.windll.dwmapi.DwmSetWindowAttribute(ctypes.c_void_p(handle), 20, ctypes.byref(value), 4)
        except (AttributeError, OSError):
            pass

    def log(self, message: str, issue: scripts.Issue | None = None, ok: bool = False) -> None:
        node = self.issues.insert(
            '',
            'end',
            values=(
                issue.row_id or '' if issue else '',
                issue.scene if issue else '',
                issue.field if issue else '',
                message,
            ),
            tags=('ok' if ok else issue.severity if issue else '',),
        )
        if issue:
            self.issue_map[node] = issue
        self.issues.see(node)

    def on_scene_select(self, _=None) -> None:
        selection = self.scene_tree.selection()
        if selection:
            values = self.scene_tree.item(selection[0], 'values')
            if values and values[0] != self.current_scene:
                self.open_scene(values[0])

    def open_scene(self, sid: str, row_id: int | str | None = None) -> bool:
        if self.busy:
            return False
        if not self.save_current():
            return False
        meta = self.manifest['scenes'].get(sid)
        if not meta:
            return False

        self.current_scene = sid
        self.path = self.work / meta['path']
        self.po_path = scripts.ROOT / meta['po']
        self.current_index = None
        self.dirty = self.raw_dirty = False
        self.rendering = True
        try:
            # Se o .po foi editado externamente (ex.: Poedit / glossario.py), reimporta antes de abrir
            if self.po_path.exists() and (not self.path.exists() or self.po_path.stat().st_mtime > self.path.stat().st_mtime + 0.5):
                scripts.build_work_tree(self.work)
            raw_json = self.path.read_bytes()
            self.fingerprint = scripts.sha(raw_json)
            self.data = json.loads(raw_json.decode('utf-8-sig'))
            if self.po_path.exists():
                self.set_text(self.raw, self.po_path.read_text(encoding='utf-8-sig'))
            self.notebook.select(0)
        except Exception as exc:
            self.data = None
            self.log(f'{sid}: falha ao carregar cena ({exc})')
        self.rendering = False

        self.search.set('')
        self.fill_rows(row_id)
        self.status.set(f'{sid}  •  {meta["po"]}  •  {meta["path"]}')
        if sid not in self.scene_nodes and self.hide_stubs_var.get():
            self.hide_stubs_var.set(False)
            self.populate_scene_tree()
        if sid in self.scene_nodes:
            self.scene_tree.selection_set(self.scene_nodes[sid])
            self.scene_tree.see(self.scene_nodes[sid])
        return True

    @staticmethod
    def _format_tipo(rec: dict) -> str:
        med = rec.get('medida')
        mb = rec.get('max_bytes')
        parts = []
        if med:
            lim = medida.LIMITS.get(med, '')
            parts.append(f'{med} {lim}px')
        elif rec.get('tipo'):
            parts.append(str(rec['tipo']))
        if mb is not None and f'max {mb}' not in str(rec.get('tipo', '')):
            parts.append(f'<= {mb}B')
        if rec.get('comum'):
            parts.append('comum')
        return ' · '.join(parts) or '-'

    def fill_rows(self, row_id: int | str | None = None) -> None:
        self.rows_tree.delete(*self.rows_tree.get_children())
        self.visible_indices.clear()
        if not isinstance(self.data, dict) or not isinstance(self.data.get('linhas'), list):
            return

        query = self.search.get().strip().casefold()
        mode = self.row_filter_var.get()

        for index, rec in enumerate(self.data['linhas']):
            if not isinstance(rec, dict):
                continue
            pt_val = str(rec.get('pt', '') or '')
            if mode == 'Exclusivas da cena' and rec.get('comum'):
                continue
            if mode == 'Faltando tradução' and pt_val.strip():
                continue
            if mode == 'Traduzidas' and not pt_val.strip():
                continue
            if query:
                hay = ' '.join(str(rec.get(k, '')) for k in ('id', 'msgctxt', 'tipo', 'en', 'pt')).casefold()
                if query not in hay:
                    continue

            self.visible_indices.append(index)
            self.rows_tree.insert(
                '',
                'end',
                iid=str(index),
                values=(
                    rec.get('id', '?'),
                    rec.get('msgctxt', ''),
                    self._format_tipo(rec),
                    str(rec.get('en', '')).replace('\n', ' ↵ '),
                    pt_val.replace('\n', ' ↵ '),
                ),
            )

        target = None
        if row_id is not None:
            target = next(
                (str(i) for i in self.visible_indices if self.data['linhas'][i].get('id') == row_id or str(self.data['linhas'][i].get('msgctxt')) == str(row_id)),
                None,
            )
            if target is None and mode != 'Todas':
                self.row_filter_var.set('Todas')
                return self.fill_rows(row_id)

        children = self.rows_tree.get_children()
        if target in children:
            self.rows_tree.selection_set(target)
            self.rows_tree.see(target)
            self.select_record(int(target))
        elif children:
            self.rows_tree.selection_set(children[0])
            self.select_record(int(children[0]))
        else:
            self.current_index = None
            self.rendering = True
            self.set_text(self.en, '', True)
            self.set_text(self.pt, '')
            self.ruler_var.set('Nenhuma linha visível no filtro atual.')
            self.rendering = False

    def on_row_select(self, _=None) -> None:
        selection = self.rows_tree.selection()
        if selection:
            self.select_record(int(selection[0]))

    def select_record(self, index: int) -> None:
        if self.data is None:
            return
        rec = self.data['linhas'][index]
        self.current_index = index
        self.rendering = True
        self.set_text(self.en, str(rec.get('en', '')), True)
        self.set_text(self.pt, str(rec.get('pt', '') or ''))
        title = self.data.get('titulo', self.current_scene)
        rep = rec.get('repeticoes', 1)
        rep_txt = f' · repete em {rep} arquivos' if rep > 1 else ' · exclusiva desta cena'
        preload_txt = ' · TRAVADO EM PRELOAD.PAK' if self.data.get('preload_fixo') else ''
        self.line_label.configure(
            text=f"{title} — linha {rec.get('id', '?')}/{len(self.data['linhas'])} (msgctxt {rec.get('msgctxt', '?')}{rep_txt}{preload_txt})"
        )
        self.rendering = False
        self.update_ruler()

    def update_ruler(self) -> None:
        if self.data is None or self.current_index is None:
            self.ruler_var.set('')
            return
        rec = self.data['linhas'][self.current_index]
        pt_val = self.pt.get('1.0', 'end-1c')
        if not pt_val.strip():
            kind = rec.get('medida')
            mb = rec.get('max_bytes')
            info = []
            if kind:
                mx = medida.MAX_LINES.get(kind)
                lim = medida.LIMITS.get(kind)
                info.append(f'Régua ({kind}): máx {lim}px' + (f', até {mx} linha(s)' if mx else ''))
            if mb is not None:
                info.append(f'Limite fixo: {mb} bytes')
            self.ruler_label.configure(style='Muted.TLabel')
            self.ruler_var.set('  |  '.join(info) if info else 'Vazio — o texto em inglês será mantido no jogo.')
            return

        errs = []
        warns = []
        is_utf8 = bool(self.data.get('utf8', False))
        # largura em pixels
        kind = rec.get('medida')
        px_summary = []
        if kind:
            stripped_lines = medida.strip_for_measure(pt_val).split('\n')
            max_lines = medida.MAX_LINES.get(kind)
            if max_lines and len(stripped_lines) > max_lines:
                errs.append(f'{len(stripped_lines)}/{max_lines} linhas')
            for i, ln in enumerate(stripped_lines):
                last = (i == len(stripped_lines) - 1)
                lim = medida.LIMITS['dialog_last'] if (kind == 'dialog' and last and len(stripped_lines) > 1) else medida.LIMITS[kind]
                w = medida.measure(ln)
                px_summary.append(f'L{i + 1}:{w}/{lim}px')
                if w > lim:
                    errs.append(f'L{i + 1} estoura ({w}>{lim}px)')

        # bytes
        mb = rec.get('max_bytes')
        if mb is not None or not is_utf8:
            try:
                enc = pt_val.encode('utf-8') if is_utf8 else fatetext.encode(pt_val)
                if mb is not None:
                    pad = 4 - (len(enc) % 4)
                    sid = self.data.get('id', '')
                    used = len(enc) if (is_utf8 or sid in ('historia/main', 'sistema/eboot')) else (len(enc) + pad - 1)
                    px_summary.append(f'{used}/{mb} bytes')
                    if used > mb:
                        errs.append(f'Excede limite de bytes ({used} > {mb})')
            except UnicodeEncodeError as exc:
                errs.append(f'Caractere sem glifo: {exc}')

        # tags e caixa alta proibida
        if any(ch in pt_val for ch in ('Â', 'Ã', 'Ê', 'Ô', 'Õ')) and not is_utf8:
            errs.append('Caixa alta acentuada (ÂÃÊÔÕ) não existe na fonte')
        tag_err = scripts.check_tags(str(rec.get('en', '')), pt_val)
        if tag_err:
            errs.append(tag_err)

        # gênero
        if not self.data.get('is_stub') and self.data.get('id') != 'historia/main' and not rec.get('comum'):
            suspects = genero.suspects(pt_val)
            if suspects:
                warns.append(f'Checar #[masc][fem]#: {", ".join(suspects)}')

        prefix = f"OK ({' · '.join(px_summary)})" if px_summary else 'OK'
        if errs:
            self.ruler_label.configure(style='RulerErr.TLabel')
            px_part = f"   [{' · '.join(px_summary)}]" if px_summary else ''
            self.ruler_var.set('ERRO: ' + ' ; '.join(errs) + px_part)
        elif warns:
            self.ruler_label.configure(style='Warn.TLabel')
            self.ruler_var.set(f"{prefix}   •   AVISO: {' ; '.join(warns)}")
        else:
            self.ruler_label.configure(style='RulerOk.TLabel')
            self.ruler_var.set(prefix)

    def insert_gender_selector(self) -> None:
        if self.busy or self.current_index is None:
            return
        try:
            sel = self.pt.get('sel.first', 'sel.last')
            snippet = f'#[{sel}][{sel}]#'
            self.pt.delete('sel.first', 'sel.last')
            self.pt.insert('insert', snippet)
        except tk.TclError:
            self.pt.insert('insert', '#[masc][fem]#')
        self.pt.focus_set()

    def copy_en_to_pt(self) -> None:
        if self.busy or self.current_index is None:
            return
        en_val = self.data['linhas'][self.current_index].get('en', '')
        self.pt.delete('1.0', 'end')
        self.pt.insert('1.0', en_val)
        self.pt.focus_set()

    def clear_pt(self) -> None:
        if self.busy or self.current_index is None:
            return
        self.pt.delete('1.0', 'end')
        self.pt.focus_set()

    def insert_missing_tags(self) -> None:
        if self.busy or self.current_index is None:
            return
        en_val = str(self.data['linhas'][self.current_index].get('en', ''))
        pt_val = self.pt.get('1.0', 'end-1c')
        en_tags = TAGS_EXTRACT_RE.findall(en_val)
        missing = [t for t in en_tags if t not in pt_val]
        if not missing:
            self.status.set('Todos os códigos de controle do inglês já estão no campo PT-BR.')
            return
        self.pt.insert('insert', ''.join(missing))
        self.pt.focus_set()

    def on_pt_modified(self, _=None) -> None:
        if not self.pt.edit_modified():
            return
        self.pt.edit_modified(False)
        if self.rendering or self.current_index is None or self.busy:
            return
        new_val = self.pt.get('1.0', 'end-1c')
        self.data['linhas'][self.current_index]['pt'] = new_val
        self.dirty = True
        node = str(self.current_index)
        if self.rows_tree.exists(node):
            self.rows_tree.set(node, 'pt', new_val.replace('\n', ' ↵ '))
        self.update_ruler()
        self.status.set(f'{self.current_scene}: alterações pendentes')
        self.validation_state.set('Alterações pendentes')
        self.validation_label.configure(style='Muted.TLabel')
        self.schedule_autosave()

    def on_raw_modified(self, _=None) -> None:
        if self.raw.edit_modified():
            self.raw.edit_modified(False)
            if not self.rendering:
                self.raw_dirty = True
                self.schedule_autosave()

    def schedule_autosave(self) -> None:
        self.cancel_autosave()
        if not self.busy:
            self.autosave_job = self.root.after(1500, self.autosave_current)

    def cancel_autosave(self) -> None:
        if self.autosave_job is not None:
            self.root.after_cancel(self.autosave_job)
            self.autosave_job = None

    def autosave_current(self) -> None:
        self.autosave_job = None
        if self.busy or not (self.dirty or self.raw_dirty):
            return
        if self.notebook.index('current') == 1 and self.raw_dirty:
            return  # não aplica .po bruto automaticamente durante digitação no texto bruto
        if self.save_current():
            self.status.set(f'Salvo automaticamente: {self.current_scene}')

    def apply_raw_po(self) -> bool:
        if self.data is None or not self.raw_dirty:
            return True
        try:
            raw_txt = self.raw.get('1.0', 'end-1c')
            self.data = scripts.apply_po_text_to_scene(self.data, raw_txt)
            self.dirty = True
            self.raw_dirty = False
            self.fill_rows()
            if self.save_current():
                self.status.set(f'.po aplicado e sincronizado com trabalho/: {self.current_scene}')
            return True
        except Exception as exc:
            self.log(f'.po inválido em {self.current_scene}: {exc}')
            self.root.bell()
            self.status.set('Corrija a sintaxe do .po antes de aplicar.')
            return False

    def sync_raw_po_view(self) -> None:
        if self.po_path and self.po_path.exists():
            self.rendering = True
            self.set_text(self.raw, self.po_path.read_text(encoding='utf-8-sig'))
            self.rendering = False
            self.raw_dirty = False

    def on_tab_changed(self, _=None) -> None:
        if self.rendering:
            return
        idx = self.notebook.index('current')
        if idx == 1:
            if self.dirty:
                self.save_current()
            self.sync_raw_po_view()
        elif idx == 0 and self.raw_dirty:
            if not self.apply_raw_po():
                self.notebook.select(1)

    def save_current(self) -> bool:
        self.cancel_autosave()
        if self.busy:
            return False
        if self.raw_dirty and not self.apply_raw_po():
            return False
        if self.data is None or not self.dirty or self.path is None:
            return True
        try:
            prop = bool(self.propagate_var.get())
            self.fingerprint, prop_n = scripts.save_scene(
                self.work, self.path, self.data, self.fingerprint, propagate=prop
            )
            self.dirty = False
            self.sync_raw_po_view()
            self._update_tree_counters()
            extra = f' (+{prop_n} repetida(s) propagadas)' if prop_n else ''
            self.status.set(f'Cena salva e sincronizada: {self.current_scene}{extra}')
            return True
        except Exception as exc:
            issue = scripts.Issue(f'Falha ao salvar: {exc}', str(self.path), self.current_scene or '')
            self.log(issue.message, issue)
            self.status.set('Erro ao salvar cena. Veja o log inferior.')
            return False

    def reload_scene(self) -> None:
        if self.busy or not self.current_scene:
            return
        self.cancel_autosave()
        self.dirty = self.raw_dirty = False
        self.open_scene(self.current_scene)

    def open_global_search(self) -> None:
        extras.open_global_search(self, self.tree_scrollbars)

    def check_glossary(self) -> None:
        if self.busy or not self.current_scene or self.data is None or self.path is None:
            return
        if not self.save_current():
            return
        terms = extras.load_ccc_glossary_terms(scripts.STANDARDS)
        if not terms:
            self.log('Glossário não encontrado em standards/.')
            return
        self.issues.delete(*self.issues.get_children())
        self.issue_map.clear()
        found = extras.check_scene_glossary(self.data, self.current_scene, self.path, terms, scripts.Issue)
        for iss in found:
            self.log(iss.message, iss)
        if not found:
            self.log(f'Glossário OK em {self.current_scene}: nenhum desvio encontrado.', ok=True)
        self.status.set(f'Glossário conferido em {self.current_scene}: {len(found)} aviso(s).')

    def update_spreadsheet(self) -> None:
        if self.busy or not self.save_current():
            return
        try:
            sys.path.insert(0, str(TOOLS_DIR))
            import gerar_planilha_progresso
            xlsx_p, _ = gerar_planilha_progresso.build_spreadsheet(preserve_team=True)
            self.log(f'Planilha atualizada preservando revisores: {xlsx_p.name}', ok=True)
            self.status.set(f'Planilha atualizada: {xlsx_p.name}')
        except Exception as exc:
            self.log(f'Falha ao atualizar planilha: {exc}')

    def run_sync_repeats(self) -> None:
        if self.busy or not self.save_current():
            return
        self.set_busy(True, 'Propagando traduções repetidas e atualizando planilha…')

        def worker():
            try:
                n = scripts.propagate_translations(self.work)
                import gerar_planilha_progresso
                gerar_planilha_progresso.build_spreadsheet(preserve_team=True)
                self.messages.put(('synced', n))
            except Exception as exc:
                self.messages.put(('failed', str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def set_busy(self, state: bool, msg: str = 'Validando projeto…') -> None:
        self.busy = state
        if state:
            self.progress.start(12)
            self.validation_state.set(msg)
            self.validation_label.configure(style='Muted.TLabel')
        else:
            self.progress.stop()
        for btn in (self.save_button, self.validate_button, self.generate_only_btn, self.generate_full_btn):
            btn.configure(state='disabled' if state else 'normal')
        self.pt.configure(state='disabled' if state else 'normal')
        self.raw.configure(state='disabled' if state else 'normal')

    def run_validation(self, build_mode: str | None = None) -> None:
        if self.busy or not self.save_current():
            return
        self.issues.delete(*self.issues.get_children())
        self.issue_map.clear()

        if build_mode == 'only' and not self.current_scene:
            return
        label = (
            f'Validando e gerando ISO (--only {self.current_scene})…' if build_mode == 'only'
            else ('Validando e gerando ISO completa (output/ccc-ptbr.iso)…' if build_mode == 'full'
                  else 'Validando 292 scripts (pixels, bytes, tags, glifos e gênero)…')
        )
        self.set_busy(True, label)
        self.status.set(label)
        target_scene = self.current_scene

        def worker():
            try:
                result = scripts.inspect_project(self.work)
                build_out = None
                if build_mode and not result.errors:
                    cmd = [sys.executable, '-X', 'utf8', str(TOOLS_DIR / 'build.py')]
                    if build_mode == 'only' and target_scene:
                        cmd.extend(['--only', target_scene])
                    proc = subprocess.run(cmd, cwd=str(scripts.ROOT), capture_output=True, text=True, encoding='utf-8', errors='replace')
                    if proc.returncode != 0:
                        raise RuntimeError((proc.stderr or proc.stdout or 'build.py falhou').strip())
                    build_out = proc.stdout.strip()
                log_p = scripts.save_log(self.work, result, build_out or '')
                self.messages.put(('validated', result, build_out, build_mode, log_p))
            except Exception as exc:
                self.messages.put(('failed', str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def poll(self) -> None:
        try:
            while True:
                msg = self.messages.get_nowait()
                self.set_busy(False)
                kind = msg[0]
                if kind == 'failed':
                    self.root.bell()
                    self.validation_state.set('Operação interrompida')
                    self.validation_label.configure(style='Error.TLabel')
                    self.log(msg[1])
                    self.status.set('Operação falhou. Veja detalhes abaixo.')
                elif kind == 'synced':
                    n = msg[1]
                    self._update_tree_counters()
                    if self.current_scene:
                        cur_rid = self.data['linhas'][self.current_index]['id'] if (self.data and self.current_index is not None) else None
                        self.open_scene(self.current_scene, cur_rid)
                    self.validation_state.set('Sincronizado')
                    self.validation_label.configure(style='Success.TLabel')
                    self.log(f'Sincronização concluída: {n} entrada(s) repetida(s) propagada(s) e planilha atualizada.', ok=True)
                    self.status.set(f'Sincronizadas {n} entradas repetidas.')
                elif kind == 'validated':
                    _, result, build_out, build_mode, log_p = msg
                    for iss in result.issues:
                        self.log(iss.message, iss)
                    self._update_tree_counters()
                    if result.errors:
                        self.root.bell()
                        self.validation_state.set(f'{len(result.errors)} erro(s)')
                        self.validation_label.configure(style='Error.TLabel')
                        first = self.issues.get_children()[0]
                        self.issues.selection_set(first)
                        self.issues.see(first)
                        self.status.set(f'{len(result.errors)} erro(s) encontrado(s). ISO bloqueada. Log: {log_p.name}')
                    elif build_out is not None:
                        self.validation_state.set('ISO gerada com sucesso')
                        self.validation_label.configure(style='Success.TLabel')
                        last_lines = ' | '.join(ln.strip() for ln in build_out.splitlines()[-4:] if ln.strip())
                        self.log(f'Build concluído ({build_mode}): {last_lines}', ok=True)
                        self.status.set(f'output/ccc-ptbr.iso atualizado ({build_mode}). Log: {log_p.name}')
                    else:
                        notices = len(result.warnings)
                        self.validation_state.set(f'Válido • {notices} aviso(s)' if notices else 'Projeto válido')
                        self.validation_label.configure(style='Muted.TLabel' if notices else 'Success.TLabel')
                        self.log(f"Validação OK: {result.manifest['scene_count']} arquivos, 0 erros ({notices} aviso(s)).", ok=True)
                        self.status.set(f'Validação concluída sem erros. Log: {log_p.name}')
        except queue.Empty:
            pass
        self.root.after(80, self.poll)

    def jump_issue(self, _=None) -> None:
        sel = self.issues.selection()
        if not sel:
            return
        iss = self.issue_map.get(sel[0])
        if not iss or not iss.scene:
            return
        if self.open_scene(iss.scene, iss.row_id):
            self.notebook.select(0)
            self.pt.focus_set()

    def open_logs(self) -> None:
        folder = self.work / 'logs'
        folder.mkdir(exist_ok=True)
        if os.name == 'nt':
            os.startfile(folder)

    def close(self) -> None:
        if self.busy:
            messagebox.showinfo('Aguarde', 'Uma operação em segundo plano ainda está em andamento.')
            return
        if self.save_current():
            self.root.destroy()


def main() -> None:
    root = tk.Tk()
    ReviewPanel(root)
    root.mainloop()


if __name__ == '__main__':
    main()
