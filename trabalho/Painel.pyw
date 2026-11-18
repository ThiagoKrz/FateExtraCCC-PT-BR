"""Atalho sem terminal para abrir o Painel de Traducao e Revisao do Fate/Extra CCC PT-BR."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / 'tools'
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import painel_ccc

if __name__ == '__main__':
    painel_ccc.main()
