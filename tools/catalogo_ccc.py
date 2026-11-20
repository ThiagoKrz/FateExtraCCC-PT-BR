"""Catálogo completo de capítulos, rotas e arquivos do Fate/Extra CCC PT-BR.

Organiza os 292 arquivos `.po` de `ptbr/` em 15 pastas lógicas dentro de
`trabalho/`, mantendo títulos descritivos em português para o painel de revisão
e para a planilha de progresso da equipe.
"""
from __future__ import annotations

import glob
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PTBR_DIR = os.path.join(ROOT, 'ptbr')

# (grupo_id, rotulo_painel, nome_planilha, descricao)
GRUPOS = [
    ('00_prologo', '00 · Prólogo — Lado Próximo e Queda', 'Prólogo',
     'Cenas de abertura na escola do Lado Próximo, queda ao Lado Distante e despertar com o Servo.'),
    ('01_capitulo_1', '01 · Capítulo 1 — Tohsaka Rin e Lancer', 'Capítulo 1',
     'Andares 1F–3F do Labirinto de Sakura, psique e confronto do Capítulo 1.'),
    ('02_capitulo_2', '02 · Capítulo 2 — Rani VIII e Berserker', 'Capítulo 2',
     'Andares 4F–6F do Labirinto de Sakura, psique e chefe do Capítulo 2.'),
    ('03_capitulo_3', '03 · Capítulo 3 — Passionlip', 'Capítulo 3',
     'Andares 7F–9F do Labirinto de Sakura, psique e núcleo de Passionlip.'),
    ('04_capitulo_4', '04 · Capítulo 4 — Carigiri Jinako e Karna', 'Capítulo 4',
     'Andares 10F–12F do Labirinto de Sakura, psique e núcleo de Jinako/Karna.'),
    ('05_capitulo_5', '05 · Capítulo 5 — Elizabeth Bathory', 'Capítulo 5',
     'Andares 13F–15F do Labirinto de Sakura, psique e confronto do Capítulo 5.'),
    ('06_capitulo_6', '06 · Capítulo 6 — Meltlilith', 'Capítulo 6',
     'Andares 16F–18F do Labirinto de Sakura, memórias e núcleo de Meltlilith.'),
    ('07_capitulo_7_final', '07 · Capítulo 7, Rota CCC e Epílogos', 'Cap. 7 e Finais',
     'Reta final no Labirinto (19F–20F), Núcleo da Moon Cell, BB, Kiara, epílogos e chefes secretos.'),
    ('08_escola_hub', '08 · Escola (Hub — Capítulos 1 a 7)', 'Escola (Hub)',
     'Corredores, Sala 2-A, Terraço, Enfermaria, Grêmio, Jardim e Biblioteca entre explorações.'),
    ('09_meu_quarto_bb', '09 · Meu Quarto (Servos) e BB Channel', 'Meu Quarto e BB',
     'Diálogos privados em Meu Quarto (variantes espelhadas), BB Channel e Sala de Punição.'),
    ('10_sg_jardins_secretos', '10 · Jardins Secretos (SG)', 'Secret Gardens',
     'Menus e textos dos Secret Gardens de todos os personagens (arquivos .bin de largura fixa).'),
    ('11_lore_matriz', '11 · Matriz de Dados (Info Matrix)', 'Info Matrix',
     'Perfis e entradas de lore da Info Matrix dos capítulos/chefes 1 a 8 (largura fixa).'),
    ('12_menus_interface', '12 · Menus e Interface', 'Menus e Interface',
     'Telas de sistema, batalha, loja, galeria, opções, salvamento, missões e status.'),
    ('13_sistema_comum', '13 · Sistema, Executável e Transições', 'Sistema e Comuns',
     'EBOOT.BIN, historia/main (PRELOAD.pak — tamanho fixo) e mapas curtos de evento/teste.'),
    ('14_mapas_base_auto', '14 · Mapas Base (Auto-Sincronizados)', 'Mapas Base (Auto)',
     'Mapas sem falas exclusivas (apenas cabeçalho comum do motor); preenchidos automaticamente.'),
]

GRUPO_INFO = {gid: {'id': gid, 'rotulo': rot, 'planilha': plan, 'descricao': desc}
              for gid, rot, plan, desc in GRUPOS}

# Cenas nomeadas de ptbr/historia/*.po em ordem narrativa dentro de cada grupo
HISTORIA_MAP: dict[str, tuple[str, int, str, str]] = {
    # 00_prologo
    '001': ('00_prologo', 1, 'Prólogo — Caminho da Escola e Portão (Shinji e Issei)', ''),
    '002': ('00_prologo', 2, 'Prólogo — Pátio da Escola (Rin e Kotomine)', ''),
    '003': ('00_prologo', 3, 'Prólogo — Corredor do 1º Andar (Loop Escolar)', ''),
    '004': ('00_prologo', 4, 'Prólogo — Corredor do 2º Andar (Anomalia e Noise)', ''),
    '005': ('00_prologo', 5, 'Prólogo — Corredor do 3º Andar e Salas do 3º Ano', ''),
    '007': ('00_prologo', 6, 'Prólogo — Sala 2-A (Encontro com Fujimura Taiga)', ''),
    '008': ('00_prologo', 7, 'Prólogo — Pátio e Portão Principal (Kiara, Shinji e Gatou)', ''),
    '009': ('00_prologo', 8, 'Prólogo — Enfermaria (Sakura no Lado Próximo)', ''),
    '010': ('00_prologo', 9, 'Prólogo — Terraço da Escola (Tohsaka Rin)', ''),
    '011': ('00_prologo', 10, 'Prólogo — Jardim e Despedida no Sonho', ''),
    '023': ('00_prologo', 11, 'Prólogo — Colapso da Arena e Queda no Lado Distante', ''),
    '069': ('00_prologo', 12, 'Prólogo — Despertar no Labirinto e Reencontro com o Servo', ''),
    '070': ('00_prologo', 13, 'Prólogo — Primeiro Encontro com BB e Alter Egos', ''),
    '078': ('00_prologo', 14, 'Prólogo — Despertar e Contrato com Gilgamesh', ''),

    # 01_capitulo_1
    '090': ('01_capitulo_1', 1, 'Cap. 1 — Labirinto 1F: Abertura e Primeira Exploração', 'Compartilha linhas base com 905'),
    '091': ('01_capitulo_1', 2, 'Cap. 1 — Labirinto 2F: Busca pelos SGs da Rin e Guardião', ''),
    '092': ('01_capitulo_1', 3, 'Cap. 1 — Labirinto 3F: Fuga de Lancer e Resgate de Rin', ''),
    '062': ('01_capitulo_1', 4, 'Cap. 1 — Relevo e SGs de Tohsaka Rin no Labirinto', ''),
    '051': ('01_capitulo_1', 5, 'Cap. 1 — Psique da Sentinela: Consciência de Tohsaka Rin', ''),
    '079': ('01_capitulo_1', 6, 'Cap. 1 — Confronto com Gawain e Libertação de Rin', ''),
    '150': ('01_capitulo_1', 7, 'Cap. 1 (Chefe) — Núcleo de Tohsaka Rin e Lancer', ''),

    # 02_capitulo_2
    '093': ('02_capitulo_2', 1, 'Cap. 2 — Labirinto 4F: Barreira de Rani VIII', ''),
    '094': ('02_capitulo_2', 2, 'Cap. 2 — Labirinto 5F: Porta da Desnudez e SGs da Rani', ''),
    '095': ('02_capitulo_2', 3, 'Cap. 2 — Labirinto 6F: Emboscada de Robin Hood e Dan Blackmore', ''),
    '114': ('02_capitulo_2', 4, 'Cap. 2 — Labirinto 6F: Confronto com Lancer e Rani', ''),
    '063': ('02_capitulo_2', 5, 'Cap. 2 — Relevo e SGs de Rani VIII no Labirinto', ''),
    '052': ('02_capitulo_2', 6, 'Cap. 2 — Psique da Sentinela: Consciência de Rani VIII', ''),
    '151': ('02_capitulo_2', 7, 'Cap. 2 (Chefe) — Núcleo de Rani VIII e Berserker', ''),

    # 03_capitulo_3
    '096': ('03_capitulo_3', 1, 'Cap. 3 — Labirinto 7F: Esconde-Esconde com Passionlip', ''),
    '097': ('03_capitulo_3', 2, 'Cap. 3 — Labirinto 8F: Armadilha e Segredos de Passionlip', ''),
    '098': ('03_capitulo_3', 3, 'Cap. 3 — Labirinto 9F: Campo Envenenado e Sombra de Lancer', ''),
    '064': ('03_capitulo_3', 4, 'Cap. 3 — Relevo e SGs de Passionlip no Labirinto', ''),
    '053': ('03_capitulo_3', 5, 'Cap. 3 — Psique da Sentinela: Consciência de Passionlip', ''),
    '108': ('03_capitulo_3', 6, 'Cap. 3 — Memórias do Passado e Confronto Interior', ''),
    '152': ('03_capitulo_3', 7, 'Cap. 3 (Chefe) — Núcleo de Passionlip', ''),

    # 04_capitulo_4
    '099': ('04_capitulo_4', 1, 'Cap. 4 — Labirinto 10F: Quarto Fechado de Jinako', ''),
    '100': ('04_capitulo_4', 2, 'Cap. 4 — Labirinto 10F (Interior): Enigmas de Jinako e Karna', ''),
    '101': ('04_capitulo_4', 3, 'Cap. 4 — Labirinto 11F: Loop de Teleporte de Jinako', ''),
    '112': ('04_capitulo_4', 4, 'Cap. 4 — Labirinto 12F: Tesouro Dourado e Pacto de Elizabeth', ''),
    '122': ('04_capitulo_4', 5, 'Cap. 4 — Labirinto 12F: Pânico de Jinako antes do Núcleo', ''),
    '124': ('04_capitulo_4', 6, 'Cap. 4 — Labirinto 12F: Confronto com Karna e Elizabeth', ''),
    '065': ('04_capitulo_4', 7, 'Cap. 4 — Relevo e SGs de Carigiri Jinako no Labirinto', ''),
    '054': ('04_capitulo_4', 8, 'Cap. 4 — Psique da Sentinela: Consciência de Carigiri Jinako', ''),
    '153': ('04_capitulo_4', 9, 'Cap. 4 (Chefe) — Núcleo de Carigiri Jinako e Karna', ''),

    # 05_capitulo_5
    '102': ('05_capitulo_5', 1, 'Cap. 5 — Labirinto 13F: Palco de Concerto de Elizabeth', ''),
    '103': ('05_capitulo_5', 2, 'Cap. 5 — Labirinto 14F: Banquete e Segredos de Elizabeth', ''),
    '115': ('05_capitulo_5', 3, 'Cap. 5 — Labirinto 15F: Câmara de Tortura de Elizabeth', ''),
    '116': ('05_capitulo_5', 4, 'Cap. 5 — Labirinto 15F: Shinji e Libertação de Meltlilith', ''),
    '055': ('05_capitulo_5', 5, 'Cap. 5 — Psique da Sentinela: Consciência de Elizabeth Bathory', ''),
    '154': ('05_capitulo_5', 6, 'Cap. 5 (Chefe) — Núcleo de Elizabeth Bathory e Matou Shinji', ''),

    # 06_capitulo_6
    '104': ('06_capitulo_6', 1, 'Cap. 6 — Labirinto 16F: Caçada de Meltlilith', ''),
    '105': ('06_capitulo_6', 2, 'Cap. 6 — Labirinto 17F: Massacre de NPCs e Bonecas de Alice', ''),
    '106': ('06_capitulo_6', 3, 'Cap. 6 — Labirinto 17F (Interior): Jogo de Alice', ''),
    '107': ('06_capitulo_6', 4, 'Cap. 6 — Labirinto 18F: Vírus de Meltlilith e Sacrifício', ''),
    '117': ('06_capitulo_6', 5, 'Cap. 6 — Labirinto 18F: Aproximação de BB e Fuga', ''),
    '118': ('06_capitulo_6', 6, 'Cap. 6 — Labirinto 18F: Intervenção do Archer da Rin', ''),
    '067': ('06_capitulo_6', 7, 'Cap. 6 — Relevo e SGs de Meltlilith no Labirinto', ''),
    '056': ('06_capitulo_6', 8, 'Cap. 6 — Psique da Sentinela: Consciência de Meltlilith', ''),
    '109': ('06_capitulo_6', 9, 'Cap. 6 — Recuperação das Memórias com o Servo', ''),
    '110': ('06_capitulo_6', 10, 'Cap. 6 — Prédio Escolar em Colapso e Despedida de Gatou', ''),
    '155': ('06_capitulo_6', 11, 'Cap. 6 (Chefe) — Núcleo de Meltlilith e Matou Shinji', ''),

    # 07_capitulo_7_final
    '068': ('07_capitulo_7_final', 1, 'Cap. 7 — Rumo ao Núcleo do Labirinto de Sakura', ''),
    '119': ('07_capitulo_7_final', 2, 'Cap. 7 — Labirinto 19F: Maratona de Inimigos de BB', ''),
    '123': ('07_capitulo_7_final', 3, 'Cap. 7 — Labirinto 20F: Última Barreira antes do Núcleo', ''),
    '111': ('07_capitulo_7_final', 4, 'Cap. 7 — Descida ao Núcleo (Crônica de Kiara — Parte 1)', 'Compartilha 274 linhas com 121'),
    '121': ('07_capitulo_7_final', 5, 'Cap. 7 — Descida ao Núcleo (Crônica de Kiara — Parte 2)', 'Compartilha 274 linhas com 111'),
    '073': ('07_capitulo_7_final', 6, 'Cap. Final — Confronto com Elizabeth Bathory no Núcleo', ''),
    '162': ('07_capitulo_7_final', 7, 'Cap. Final — Redenção de Elizabeth Bathory', ''),
    '156': ('07_capitulo_7_final', 8, 'Cap. Final (Chefe) — Núcleo de BB (Batalha Final Normal)', ''),
    '059': ('07_capitulo_7_final', 9, 'Cap. Final — Despedida de BB e Resgate de Sakura', ''),
    '157': ('07_capitulo_7_final', 10, 'Rota CCC (Chefe Final) — Sessyoin Kiara e Andersen', ''),
    '060': ('07_capitulo_7_final', 11, 'Epílogo — Desfecho da Rota CCC e Retorno', ''),
    '072': ('07_capitulo_7_final', 12, 'Epílogo — Final Normal (Despertar no Mundo Real)', ''),
    '074': ('07_capitulo_7_final', 13, 'Epílogo — Finais de Servo (Tamamo, Archer e Gilgamesh)', ''),
    '075': ('07_capitulo_7_final', 14, 'Epílogo — Final de Saber (Nero Claudius)', ''),
    '080': ('07_capitulo_7_final', 15, 'Pós-Jogo — Desbloqueio da Rota CCC e Traje de Banho', ''),
    '136': ('07_capitulo_7_final', 16, 'Chefe Secreto — Confronto com Gilgamesh e Enkidu', ''),
    '180': ('07_capitulo_7_final', 17, 'Labirinto — Eventos de Fenda Espacial e Chefe Extra', ''),

    # 08_escola_hub
    '024': ('08_escola_hub', 1, 'Escola — Corredor do 1º Andar (Capítulos 1 a 7)', ''),
    '025': ('08_escola_hub', 2, 'Escola — Corredor do 2º Andar (Capítulos 1 a 7)', ''),
    '026': ('08_escola_hub', 3, 'Escola — Corredor do 3º Andar e Capela (Capítulos 1 a 7)', ''),
    '027': ('08_escola_hub', 4, 'Escola — Sala de Aula 2-A (Capítulos 1 a 7)', ''),
    '028': ('08_escola_hub', 5, 'Escola — Terraço (Gatou e Eventos dos Capítulos 1 a 7)', ''),
    '029': ('08_escola_hub', 6, 'Escola — Enfermaria da Sakura (Capítulos 1 a 7 e SGs)', ''),
    '030': ('08_escola_hub', 7, 'Escola — Sala do Grêmio Estudantil (Reuniões dos Capítulos 1 a 7)', 'Base das reuniões; 1.932 linhas repetem em 035 e 1.569 em 024'),
    '031': ('08_escola_hub', 8, 'Escola — Jardim Central (Shinji, Jinako e Kiara)', ''),
    '035': ('08_escola_hub', 9, 'Escola — Sala do Grêmio Estudantil (Eventos de Transição)', 'Espelho parcial de 030 (1.932 linhas comuns)'),
    '036': ('08_escola_hub', 10, 'Escola — Corredor Escuro (Reta Final)', ''),
    '037': ('08_escola_hub', 11, 'Escola — Biblioteca (Livros e Eventos de Lore)', ''),

    # 09_meu_quarto_bb
    '071': ('09_meu_quarto_bb', 1, 'Meu Quarto (My Room) — Diálogos com o Servo e Bônus', 'Arquivo mestre de My Room (4.096 linhas espelhadas em 032 e 033)'),
    '032': ('09_meu_quarto_bb', 2, 'Meu Quarto (My Room) — Variante A (Espelho de 071)', 'Espelho automático de 071 — traduza em 071 e sincronize'),
    '033': ('09_meu_quarto_bb', 3, 'Meu Quarto (My Room) — Variante B (Espelho de 071)', 'Espelho automático de 071 — traduza em 071 e sincronize'),
    '058': ('09_meu_quarto_bb', 4, 'Estúdio do BB Channel — Todos os Episódios', ''),
    '050': ('09_meu_quarto_bb', 5, 'Sala de Punição (Oshioki) e Game Over da BB', ''),

    # 13_sistema_comum (parte historia)
    'main': ('13_sistema_comum', 2, 'Cabeçalho Global de Nomes e Locais (main)', 'PRELOAD.pak — NUNCA aumentar bytes nem estourar slots de 4 bytes'),
    '066': ('13_sistema_comum', 3, 'Sistema / Mapa — Portal de Retorno à Escola Antiga', ''),
    '141': ('13_sistema_comum', 4, 'Sistema / Transição — Avisos de Clear Data e Grêmio', ''),
    '900': ('13_sistema_comum', 5, 'Protótipo / Debug — Labirinto Inicial de Lancer', ''),
    '901': ('13_sistema_comum', 6, 'Protótipo / Debug — Visão da Consciência de Tohsaka Rin', ''),
    '902': ('13_sistema_comum', 7, 'Protótipo / Debug — Checkpoints e Lembretes (A)', ''),
    '903': ('13_sistema_comum', 8, 'Protótipo / Debug — Checkpoints e Lembretes (B)', ''),
    '904': ('13_sistema_comum', 9, 'Protótipo / Debug — Checkpoints e Lembretes (C)', ''),
    '905': ('13_sistema_comum', 10, 'Protótipo / Debug — Versão Alternativa do Labirinto 1F (905)', 'Compartilha 428 linhas com 090'),
    '995': ('13_sistema_comum', 11, 'Protótipo / Debug — Teste da Loja Estudantil', ''),
    '996': ('13_sistema_comum', 12, 'Protótipo / Debug — Checkpoints e Lembretes (D)', ''),
    '999': ('13_sistema_comum', 13, 'Protótipo / Debug — Checkpoints e Lembretes (E)', ''),
}

SG_CHARS = [
    ('ner', 'Nero (Saber)'),
    ('tam', 'Tamamo-no-Mae (Caster)'),
    ('emi', 'EMIYA (Archer)'),
    ('gil', 'Gilgamesh'),
    ('rin', 'Tohsaka Rin'),
    ('ran', 'Rani VIII'),
    ('psl', 'Passionlip'),
    ('zin', 'Carigiri Jinako'),
    ('ksk', 'BB (Black Sakura)'),
    ('eli', 'Elizabeth Bathory'),
    ('mll', 'Meltlilith'),
    ('kia', 'Sessyoin Kiara'),
]
SG_CHAR_MAP = {k: (idx, nome) for idx, (k, nome) in enumerate(SG_CHARS, 1)}

LORE_CHAPTERS = {
    '01': 'Cap. 1 — Elizabeth (Lancer) / Rin & Rani',
    '02': 'Cap. 2 — Passionlip e BB',
    '03': 'Cap. 3 — Carigiri Jinako e Karna',
    '04': 'Cap. 4 — Elizabeth Bathory e Matou Shinji',
    '05': 'Cap. 5 — Meltlilith e BB',
    '06': 'Cap. 6 — BB (Sakura)',
    '07': 'Cap. 7 / Final — Sessyoin Kiara e Andersen',
    '08': 'Bônus — Gilgamesh e Protagonista',
}

MENUS_MAP: dict[str, tuple[int, str, str]] = {
    'interface__title__msg': (1, 'Menus — Tela de Título (Aviso de Patch)', ''),
    'interface__modeselect__modeselect': (2, 'Menus — Seleção de Dificuldade / Modo de Jogo', ''),
    'interface__nameentry__msg': (3, 'Menus — Entrada de Nome do Protagonista (Mensagens)', ''),
    'interface__nameentry__kanji': (4, 'Menus — Tabela de Kanji da Entrada de Nome', 'Tabela JP de seleção de kanji — manter ou adaptar com cuidado'),
    'interface__svtselect__msg': (5, 'Menus — Seleção de Servo (Estilos e Avisos)', ''),
    'interface__charsel__svt_select': (6, 'Menus — Confirmação de Parceria com o Servo', ''),
    'interface__cmn__dialog': (7, 'Menus — Diálogos Comuns (Sim / Não)', ''),
    'interface__cmn__install': (8, 'Menus — Instalação de Dados (PRELOAD)', 'PRELOAD.pak UTF-8: o arquivo inteiro cabe em 656 bytes (acento = 2 bytes)'),
    'interface__mainmenu__help': (9, 'Menus — Ajuda do Menu Principal', ''),
    'interface__status__msg': (10, 'Menus — Tela de Status e Trajes', ''),
    'interface__equip__msg': (11, 'Menus — Equipamento e Artefatos Místicos', ''),
    'interface__item__msg': (12, 'Menus — Rótulo da Tela de Itens', ''),
    'interface__shop__msg': (13, 'Menus — Loja Estudantil (Compra e Venda)', ''),
    'interface__myroom__msg': (14, 'Menus — Interface e Ações do Meu Quarto (My Room)', ''),
    'interface__select__i_move': (15, 'Menus — Menu de Deslocamento pela Escola', ''),
    'interface__dungeonselect__0000': (16, 'Menus — Seleção de Andar da Arena (Sakura Labyrinth)', ''),
    'interface__dungeon__msg': (17, 'Menus — Objetivos e Missões do Labirinto', ''),
    'interface__dungeon__i_dun_sysmsg': (18, 'Menus — Mensagem de Efeito Expirado no Labirinto', ''),
    'battle__interface__btl_msg': (19, 'Menus — Mensagens de Batalha e Suporte', ''),
    'interface__dayresult__d_result': (20, 'Menus — Tela de Resultado do Dia', ''),
    'interface__osioki__msg': (21, 'Menus — Minijogo de Punição da BB (Oshioki)', ''),
    'interface__infomatrixex__msg': (22, 'Menus — Títulos e Rótulos da Matriz de Dados', ''),
    'interface__gallery__msg': (23, 'Menus — Galeria e Desbloqueáveis', ''),
    'interface__option__msg': (24, 'Menus — Tela de Opções e Configurações', ''),
    'interface__save__msg': (25, 'Menus — Menu de Salvamento e Carregamento', ''),
    'interface__gameover__gov': (26, 'Menus — Tela de Game Over', ''),
}


def slugify(text: str) -> str:
    s = (text.replace('á', 'a').replace('à', 'a').replace('ã', 'a').replace('â', 'a')
             .replace('é', 'e').replace('ê', 'e').replace('í', 'i')
             .replace('ó', 'o').replace('ô', 'o').replace('õ', 'o')
             .replace('ú', 'u').replace('ç', 'c')
             .replace('Á', 'a').replace('É', 'e').replace('Í', 'i')
             .replace('Ó', 'o').replace('Ú', 'u').replace('À', 'a').replace('Ç', 'c'))
    s = re.sub(r'[^a-zA-Z0-9]+', '_', s.lower()).strip('_')
    return s[:46].strip('_') or 'cena'


def _describe_sg(stem: str) -> tuple[int, str, str]:
    if stem == 'interface__sg__0000':
        return 1, 'SG — Índice Geral de Personagens', 'Largura fixa (.bin)'
    m = re.match(r'^interface__sg__sg_([a-z]{3})(?:_(text\d+|textEx))?$', stem)
    if m:
        code, sub = m.group(1), m.group(2)
        c_idx, nome = SG_CHAR_MAP.get(code, (99, code.upper()))
        base_order = c_idx * 10
        if not sub:
            return base_order, f'SG [{nome}] — Menu e Ficha de Segredos', 'Largura fixa (.bin)'
        if sub == 'textEx':
            return base_order + 5, f'SG [{nome}] — Texto Extra (Fantasma Nobre)', 'Largura fixa (.bin)'
        n = int(sub[4:])
        rot = f'Episódio' if n == 4 else f'SG {n} (Texto e Descrição)'
        return base_order + n, f'SG [{nome}] — {rot}', 'Largura fixa (.bin)'
    return 999, f'SG — {stem}', 'Largura fixa (.bin)'


def _describe_lore(stem: str) -> tuple[int, str, str]:
    m = re.match(r'^interface__infomatrixex__infomatrix_([dt])_(\d+)$', stem)
    if m:
        kind, num = m.group(1), m.group(2)
        chap_label = LORE_CHAPTERS.get(num, f'Cap. {num}')
        if kind == 'd':
            return int(num), f'Info Matrix (Ficha {num}) — {chap_label}', 'Largura fixa (.bin)'
        return 100 + int(num), f'Info Matrix (Textos {num}) — {chap_label}', 'Largura fixa (.bin)'
    return 999, f'Info Matrix — {stem}', 'Largura fixa (.bin)'


def catalogar_todos(ptbr_dir: str = PTBR_DIR) -> list[dict]:
    """Descobre todos os arquivos `.po` em `ptbr/` e devolve lista ordenada com metadados."""
    items = []
    map_base_order = 1
    for path in sorted(glob.glob(os.path.join(ptbr_dir, '*', '*.po'))):
        rel_dir_file = os.path.relpath(path, ptbr_dir).replace(os.sep, '/')
        po_id = rel_dir_file[:-3]
        cat, stem = po_id.split('/', 1)
        if cat == 'nativo':
            # itens/legendas do patch nativo: aplicados por tools/native_text.py,
            # fora do pipeline de dump/build e do catálogo de 292 unidades
            continue

        is_stub = False
        if cat == 'historia':
            if stem in HISTORIA_MAP:
                grupo_id, ordem, titulo, nota = HISTORIA_MAP[stem]
            else:
                grupo_id = '14_mapas_base_auto'
                ordem = map_base_order
                map_base_order += 1
                if stem.endswith('-1000'):
                    titulo = f'Mapa Base {stem[:-5]} (1000.dat — Sub-mapa / Arena)'
                else:
                    titulo = f'Mapa Base {stem} (0000.dat — Apenas Cabeçalho Comum)'
                nota = 'Sem falas exclusivas; auto-sincronizado pelo cabeçalho comum'
                is_stub = True
        elif cat == 'sg':
            grupo_id = '10_sg_jardins_secretos'
            ordem, titulo, nota = _describe_sg(stem)
        elif cat == 'lore':
            grupo_id = '11_lore_matriz'
            ordem, titulo, nota = _describe_lore(stem)
        elif cat == 'menus':
            grupo_id = '12_menus_interface'
            ordem, titulo, nota = MENUS_MAP.get(stem, (999, f'Menu — {stem}', ''))
        elif cat == 'sistema':
            grupo_id = '13_sistema_comum'
            ordem = 1
            titulo = 'Sistema — Executável do Jogo (EBOOT.BIN)'
            nota = 'EBOOT.BIN — tamanho fixo por ponteiro (respeitar max bytes)'
        else:
            raise ValueError(f'Categoria desconhecida em ptbr/: {po_id}')

        gmeta = GRUPO_INFO[grupo_id]
        slug = slugify(titulo)
        json_name = f'{ordem:03d}_{slug}__{stem}.json'
        work_rel = f'{grupo_id}/{json_name}'
        preload_fixo = po_id in ('historia/main', 'menus/interface__cmn__install')

        items.append({
            'id': po_id,
            'cat': cat,
            'stem': stem,
            'po_rel': f'ptbr/{rel_dir_file}',
            'grupo_id': grupo_id,
            'grupo_rotulo': gmeta['rotulo'],
            'planilha_cap': gmeta['planilha'],
            'ordem': ordem,
            'titulo': titulo,
            'nota': nota,
            'work_rel': work_rel,
            'is_stub': is_stub,
            'preload_fixo': preload_fixo,
        })

    grp_rank = {gid: i for i, (gid, *_rest) in enumerate(GRUPOS)}
    items.sort(key=lambda x: (grp_rank[x['grupo_id']], x['ordem'], x['id']))
    return items
