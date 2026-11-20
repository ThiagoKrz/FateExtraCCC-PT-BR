"""Gera a planilha de progresso do Fate/Extra CCC PT-BR no padrão FHA/FSN/Mahoyo.

Saídas na raiz do projeto:
  - `Fate_Extra_CCC_Progresso_Geral.xlsx` (aba 'Geral' com resumo COUNTIFS/IFERROR/SUMIF)
  - `FATE EXTRA CCC PROGRESSO - Geral.csv` (espelho CSV UTF-8-SIG)

Uso: python -X utf8 tools/gerar_planilha_progresso.py
"""
from __future__ import annotations

import csv
import os
from pathlib import Path
import sys

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

TOOLS_DIR = Path(__file__).resolve().parent
ROOT = TOOLS_DIR.parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import catalogo_ccc as cat
import scripts_ccc

XLSX_OUT = ROOT / 'Fate_Extra_CCC_Progresso_Geral.xlsx'
CSV_OUT = ROOT / 'FATE EXTRA CCC PROGRESSO - Geral.csv'

GROUP_PASTEL = [
    'EAD1DC', 'FCE5CD', 'FFF2CC', 'D9EAD3', 'C9DAF8',
    'F4CCCC', 'CFE2F3', 'D0E0E3', 'D9D2E9', 'FFE599',
    'B6D7A8', 'F9CB9C', 'EA9999', 'CCCCCC', 'E2E8F0',
]

STATUS_FILL = {
    'Pendente': 'F3F4F6',
    'Em tradução': 'FFF2CC',
    'Em revisão': 'CFE2F3',
    'Auto-sincronizado': 'E2E8F0',
    'Revisado': 'D9EAD3',
    'beta-ia': 'D9D2E9',
}


def _read_existing_assignments(xlsx_path: Path) -> dict[str, tuple[str, str, str]]:
    """Preserva revisores, testadores e status 'Revisado' ao atualizar a planilha."""
    saved: dict[str, tuple[str, str, str]] = {}
    if not xlsx_path.exists():
        return saved
    try:
        wb = openpyxl.load_workbook(xlsx_path, data_only=False)
        if 'Geral' not in wb.sheetnames:
            return saved
        ws = wb['Geral']
        for r in range(3, ws.max_row + 1):
            script_val = ws.cell(r, 2).value
            if not script_val:
                continue
            rev = str(ws.cell(r, 4).value or '')
            est = str(ws.cell(r, 5).value or '')
            test = str(ws.cell(r, 7).value or '')
            # extrai po_id entre parênteses no final, ou usa string inteira
            m_id = script_val.rsplit('(', 1)
            key = m_id[1].rstrip(')').strip() if len(m_id) == 2 and script_val.endswith(')') else str(script_val)
            saved[key] = (rev, est, test)
    except Exception:
        pass
    return saved


def build_spreadsheet(preserve_team: bool = True) -> tuple[Path, Path]:
    existing = _read_existing_assignments(XLSX_OUT) if preserve_team else {}
    manifest = scripts_ccc.refresh_manifest(scripts_ccc.WORK)
    scenes_by_group: dict[str, list[dict]] = {gid: [] for gid, *_ in cat.GRUPOS}
    for sid, meta in manifest['scenes'].items():
        scenes_by_group[meta['grupo']].append(meta)
    for gid in scenes_by_group:
        scenes_by_group[gid].sort(key=lambda m: (m['ordem'], m['id']))

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Geral'
    ws.freeze_panes = 'A3'
    ws.views.sheetView[0].showGridLines = True

    thin = Side(border_style='thin', color='CBD5E1')
    border_cell = Border(left=thin, right=thin, top=thin, bottom=thin)
    thick_bottom = Side(border_style='medium', color='334155')
    border_hdr = Border(left=thin, right=thin, top=thin, bottom=thick_bottom)

    # Banner superior A1:H1
    ws.merge_cells('A1:H1')
    ws['A1'] = (
        'FATE/EXTRA CCC — PLANILHA DE PROGRESSO PT-BR | '
        'Use Ctrl+F para buscar pelo código do arquivo (ex.: 024, 150, sg_ner) ou nome da cena'
    )
    ws['A1'].fill = PatternFill('solid', fgColor='1F2937')
    ws['A1'].font = Font(name='Segoe UI', size=11, bold=True, color='FFFFFF')
    ws['A1'].alignment = Alignment(horizontal='left', vertical='center', wrap_text=True, indent=1)
    ws.row_dimensions[1].height = 36

    headers = ['Título / Capítulo e Cena', 'SCRIPT', 'Linhas', 'REVISORES', 'Estado', 'CAPÍTULO', 'Testado Por', 'OBS']
    hdr_fill = PatternFill('solid', fgColor='334155')
    hdr_font = Font(name='Segoe UI', size=10, bold=True, color='FFFFFF')
    for col_idx, h in enumerate(headers, 1):
        cell = ws.cell(2, col_idx, h)
        cell.fill = hdr_fill
        cell.font = hdr_font
        cell.border = border_hdr
        cell.alignment = Alignment(horizontal='center' if col_idx in (3, 5, 6) else 'left', vertical='center')
    ws.row_dimensions[2].height = 24

    # Cabeçalho do painel lateral J1:M1
    sum_headers = ['Capítulo', 'Scripts Revisados/Total', 'Progresso%', 'Total de Linhas']
    sum_hdr_fill = PatternFill('solid', fgColor='D9EAD3')
    sum_hdr_font = Font(name='Segoe UI', size=10, bold=True, color='111827')
    for offset, title in enumerate(sum_headers):
        c = ws.cell(1, 10 + offset, title)
        c.fill = sum_hdr_fill
        c.font = sum_hdr_font
        c.border = border_hdr
        c.alignment = Alignment(horizontal='center' if offset > 0 else 'left', vertical='center')

    # Preencher linhas da tabela principal com divisores de capítulo
    cur_row = 3
    csv_rows: list[list] = [headers]
    for g_idx, (gid, rotulo, cap_name, desc) in enumerate(cat.GRUPOS):
        color = GROUP_PASTEL[g_idx % len(GROUP_PASTEL)]
        sec_fill = PatternFill('solid', fgColor=color)
        sec_font = Font(name='Segoe UI', size=10, bold=True, color='111827')

        # Linha divisória de capítulo (B..H vazias para não interferir em COUNTA/COUNTIFS)
        ws.cell(cur_row, 1, f'▶ {rotulo} — {desc}')
        for col_idx in range(1, 9):
            c = ws.cell(cur_row, col_idx)
            c.fill = sec_fill
            c.font = sec_font
            c.border = border_cell
            c.alignment = Alignment(vertical='center')
        ws.row_dimensions[cur_row].height = 22
        cur_row += 1

        for meta in scenes_by_group[gid]:
            tot = int(meta['linhas'])
            uniq = int(meta['exclusivas'])
            tr = int(meta['traduzidas'])
            pct = (100.0 * tr / tot) if tot else 0.0

            if tr >= tot:
                if gid == '00_prologo':
                    estado = 'Revisado'
                else:
                    estado = 'beta-ia'
            elif meta['is_stub']:
                estado = 'Auto-sincronizado'
            elif tr == 0:
                estado = 'Pendente'
            else:
                estado = 'Em tradução'

            obs_parts = [f'{uniq} únicas | {tr}/{tot} traduzidas ({pct:.0f}%)']
            if meta.get('nota'):
                obs_parts.append(meta['nota'])
            obs = ' · '.join(obs_parts)

            prev_rev, prev_est, prev_test = existing.get(meta['id'], ('', '', ''))
            if prev_est in ('Revisado', 'beta-ia'):
                estado = prev_est

            script_ref = f"trabalho/{meta['path']} ({meta['id']})"
            row_vals = [meta['titulo'], script_ref, tot, prev_rev, estado, cap_name, prev_test, obs]
            csv_rows.append(row_vals)

            row_fill = PatternFill('solid', fgColor='FFFFFF' if cur_row % 2 else 'F8FAFC')
            st_fill = PatternFill('solid', fgColor=STATUS_FILL.get(estado, 'FFFFFF'))
            for col_idx, val in enumerate(row_vals, 1):
                c = ws.cell(cur_row, col_idx, val)
                c.font = Font(name='Segoe UI', size=9.5, color='111827')
                c.fill = st_fill if col_idx == 5 else row_fill
                c.border = border_cell
                if col_idx == 3:
                    c.number_format = '#,##0'
                    c.alignment = Alignment(horizontal='right', vertical='center')
                elif col_idx in (5, 6):
                    c.alignment = Alignment(horizontal='center', vertical='center')
                else:
                    c.alignment = Alignment(horizontal='left', vertical='center')
            ws.row_dimensions[cur_row].height = 20
            cur_row += 1

    last_row = cur_row - 1

    # Resumo lateral J2:M16 + TOTAL em J17:M17
    for idx, (gid, rotulo, cap_name, _desc) in enumerate(cat.GRUPOS):
        r = 2 + idx
        c_fill = PatternFill('solid', fgColor=GROUP_PASTEL[idx % len(GROUP_PASTEL)])
        c_font = Font(name='Segoe UI', size=9.5, color='111827')

        cj = ws.cell(r, 10, cap_name)
        ck = ws.cell(
            r, 11,
            f'=(COUNTIFS($F$3:$F${last_row},J{r},$E$3:$E${last_row},"Revisado",$B$3:$B${last_row},"<>")'
            f'+COUNTIFS($F$3:$F${last_row},J{r},$E$3:$E${last_row},"beta-ia",$B$3:$B${last_row},"<>"))'
            f'&" / "&COUNTIFS($F$3:$F${last_row},J{r},$B$3:$B${last_row},"<>")',
        )
        cl = ws.cell(
            r, 12,
            f'=IFERROR((COUNTIFS($F$3:$F${last_row},J{r},$E$3:$E${last_row},"Revisado",$B$3:$B${last_row},"<>")'
            f'+COUNTIFS($F$3:$F${last_row},J{r},$E$3:$E${last_row},"beta-ia",$B$3:$B${last_row},"<>"))'
            f'/COUNTIFS($F$3:$F${last_row},J{r},$B$3:$B${last_row},"<>"),0)',
        )
        cm = ws.cell(r, 13, f'=SUMIF($F$3:$F${last_row},J{r},$C$3:$C${last_row})')

        cl.number_format = '0.0%'
        cm.number_format = '#,##0'
        for col_i, cell in enumerate((cj, ck, cl, cm)):
            cell.fill = c_fill
            cell.font = c_font
            cell.border = border_cell
            cell.alignment = Alignment(horizontal='left' if col_i == 0 else ('right' if col_i >= 2 else 'center'), vertical='center')

    total_row = 2 + len(cat.GRUPOS)
    tot_fill = PatternFill('solid', fgColor='C9DAF8')
    tot_font = Font(name='Segoe UI', size=10, bold=True, color='111827')
    tj = ws.cell(total_row, 10, 'TOTAL')
    tk = ws.cell(total_row, 11, f'=(COUNTIF($E$3:$E${last_row},"Revisado")+COUNTIF($E$3:$E${last_row},"beta-ia"))&" / "&COUNTA($B$3:$B${last_row})')
    tl = ws.cell(total_row, 12, f'=IFERROR((COUNTIF($E$3:$E${last_row},"Revisado")+COUNTIF($E$3:$E${last_row},"beta-ia"))/COUNTA($B$3:$B${last_row}),0)')
    tm = ws.cell(total_row, 13, f'=SUM($C$3:$C${last_row})')
    tl.number_format = '0.0%'
    tm.number_format = '#,##0'
    for col_i, cell in enumerate((tj, tk, tl, tm)):
        cell.fill = tot_fill
        cell.font = tot_font
        cell.border = border_hdr
        cell.alignment = Alignment(horizontal='left' if col_i == 0 else ('right' if col_i >= 2 else 'center'), vertical='center')

    # Validação de lista suspensa na coluna E (Estado)
    dv = DataValidation(
        type='list',
        formula1='"Pendente,Em tradução,Em revisão,Auto-sincronizado,Revisado,beta-ia"',
        allow_blank=True,
    )
    ws.add_data_validation(dv)
    dv.add(f'E3:E{last_row}')

    widths = {
        'A': 56, 'B': 54, 'C': 10, 'D': 16, 'E': 18, 'F': 18, 'G': 16, 'H': 54,
        'I': 3, 'J': 22, 'K': 24, 'L': 13, 'M': 15,
    }
    for col_letter, w in widths.items():
        ws.column_dimensions[col_letter].width = w

    wb.save(XLSX_OUT)

    with open(CSV_OUT, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(csv_rows)

    return XLSX_OUT, CSV_OUT


if __name__ == '__main__':
    xlsx_p, csv_p = build_spreadsheet()
    print(f'Gerado: {xlsx_p.name} e {csv_p.name}')
