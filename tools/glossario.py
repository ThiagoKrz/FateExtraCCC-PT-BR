"""Apply a glossary of exact English -> pt-BR strings across every .po file.

Matching is by exact msgid, so a string that shows up in several files is
translated the same way everywhere - that is the point of keeping it here
instead of editing each file by hand.

Only empty msgstr entries are filled, so nothing you translated by hand is
ever overwritten. Run it again after adding entries below.

Usage:  python tools/glossario.py            # fill empty entries
        python tools/glossario.py --dry-run  # only report
        python tools/glossario.py --force    # also replace existing text that
                                             # disagrees with the glossary
"""
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fatetext

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PTBR = os.path.join(ROOT, 'ptbr')

# Terms kept in English on purpose: Servant class names (Saber, Archer, Savior, ...),
# system labels (Clear Data, Secret Garden, Info Matrix) and proper names follow the
# Fate Cafe / Type-Moon convention. Full Japanese names follow surname-first order
# without macrons; general Type-Moon terms (Servant -> Servo, Master -> Mestre,
# Mystic Code -> Artefato Mistico, Noble Phantasm -> Fantasma Nobre) are translated.
GLOSSARY = {
    # --- botoes e respostas comuns ---
    'Yes': 'Sim',
    ' No': ' Não',
    'Exit': 'Sair',
    'Buy': 'Comprar',
    'Sell': 'Vender',
    'Items': 'Itens',

    # --- batalha ---
    "Master's Support Command": 'Comando de Apoio do Mestre',
    'Required MP': 'MP Necessário',
    'below %': 'abaixo de %',
    'Escape?': 'Fugir?',
    'Heal & scan enemy. Cost: One Turn': 'Cura e escaneia o inimigo. Custo: 1 turno',
    'Command Seal': 'Selo de Comando',

    # --- avisos curtos ---
    'Partner with this Servant?': 'Formar parceria com este Servo?',
    'acquired!': 'adquirido!',
    '\nis no longer effective.': '\nnão surte mais efeito.',
    'Return to Title Screen?': 'Voltar à tela de título?',

    # --- equipamento ---
    'Change which Mystic Code?': 'Trocar qual Artefato Místico?',
    'Change into this Mystic Code?': 'Trocar para este Artefato Místico?',
    'Not equipped.': 'Não equipado.',
    'Slot 1 has been locked.': 'Espaço 1 bloqueado.',
    'Slot 2 has been locked.': 'Espaço 2 bloqueado.',

    # --- selecao de modo ---
    'This mode is for those who are new to the RPG genre.\n'
    'Better rates for enemy data, money, and items.':
        'Modo para quem está começando no gênero RPG.\n'
        'Melhores taxas de dados de inimigo, dinheiro e itens.',
    'This mode is for those who wish to fully enjoy the experience.':
        'Modo para quem quer aproveitar a experiência por completo.',
    'This mode is for those who enjoy severe gameplay.\n'
    'Enemy ATK raised and Boss HP also increased.':
        'Modo para quem gosta de desafio pesado.\n'
        'ATK dos inimigos e HP dos chefes aumentados.',
    '#C255120120Clear Data has been loaded.#CDEF':
        '#C255120120Clear Data carregado.#CDEF',
    'Skip the prologue and start from\nthe Servant selection event.':
        'Pula o prólogo e começa a partir do\nevento de escolha do Servo.',

    # --- selecao de servant / estilo ---
    'Standard - A balanced set of combat abilities.':
        'Standard - Conjunto equilibrado de habilidades de combate.',
    'Technical - Fight by reinforcing Projection Skills.':
        'Technical - Luta reforçando Habilidades de Projeção.',
    'Maniac - Strong skills but physically weak.':
        'Maniac - Habilidades fortes, mas fisicamente fraco.',
    'Cheat - Overwhelm enemies with unlimited weapons.':
        'Cheat - Esmaga inimigos com armas ilimitadas.',
    'Partner with #SVT?': 'Formar parceria com #SVT?',
    'In choosing a male Master, some events\nwill become unavailable. Is that okay?':
        'Ao escolher um Mestre homem, alguns eventos\nficam indisponíveis. Tudo bem?',

    # --- opcoes ---
    'Change the text display speed.': 'Altera a velocidade do texto.',
    'Turn event voices ON/OFF.': 'Liga e desliga as vozes dos eventos.',
    'Change the BGM volume.': 'Altera o volume da música.',
    'Change SE and voice volumes.': 'Altera o volume de efeitos e vozes.',
    'Change camera controls in Arena.': 'Altera os controles de câmera na Arena.',
    'Change the game difficulty.': 'Altera a dificuldade do jogo.',
    'Save into the installed data.': 'Salva nos dados instalados.',
    'Save settings and return to System Menu.':
        'Salva e volta ao Menu do Sistema.',

    # --- save ---
    'Save your progress.': 'Salva seu progresso.',
    'Load saved data.': 'Carrega dados salvos.',
    'Delete saved data.': 'Apaga dados salvos.',
    'Change in-game settings.': 'Altera as configurações do jogo.',
    'Return to title without saving.': 'Volta ao título sem salvar.',
    'Cannot be used.': 'Não pode ser usado.',
    'Return to title without saving?': 'Voltar ao título sem salvar?',

    # --- nomes e rotulos que reaparecem em quase toda cena ---
    'Green Tea': 'Chá Verde',
    'Newscaster': 'Apresentador',
    "Rin's Archer": 'Archer da Rin',
    'Father Kotomine': 'Padre Kotomine',
    'Male Student': 'Aluno',
    'Female Student': 'Aluna',
    'Young Man': 'Rapaz',
    'Rin Tohsaka': 'Tohsaka Rin',
    'Shinji Matou': 'Matou Shinji',
    'Sakura Matou': 'Matou Sakura',
    'Taiga Fujimura': 'Fujimura Taiga',
    'Issei Ryuudou': 'Ryuudou Issei',
    'Kiara Sessyoin': 'Sessyoin Kiara',
    'Jinako Carigiri': 'Carigiri Jinako',

    # --- avisos de item e save (repetem em toda cena) ---
    'Obtained': 'Obtido',
    '　Obtained\n#C000246204#TITM0001#CDEF.':
        '　Obtido:\n#C000246204#TITM0001#CDEF.',
    '　You cannot carry any more\n#C000246204#TITM0001#CDEF.':
        '　Você não pode carregar mais\n#C000246204#TITM0001#CDEF.',
    'You may now save your current game data\n            as #C000246204Clear Data#CDEF.':
        'Agora você pode salvar seus dados\n         como #C000246204Clear Data#CDEF.',
    '     You may use this data to carry\nover elements to the start of a new game.':
        '     Você pode usar esses dados para levar\nelementos ao início de um novo jogo.',
    'Please be careful to not overwrite\n  the data while you are saving.':
        'Tome cuidado para não sobrescrever\n  os dados ao salvar.',
    'Would you like to save your Clear Data?': 'Deseja salvar seus Clear Data?',
    'Are you sure you wish to exit': 'Tem certeza de que deseja sair',
    'Access to #C000246204System#CDEF granted.':
        'Acesso ao #C000246204Sistema#CDEF concedido.',
    'You may access it via the △ button.': 'Acesse pelo botão △.',

    # --- locais (aparecem em varios arquivos) ---
    'School Building 1F': 'Escola - Andar 1',
    'School Building 2F': 'Escola - Andar 2',
    'School Building 3F': 'Escola - Andar 3',
    'Classroom 2-A': 'Sala 2-A',
    '1st & 2nd Year Classroom': 'Salas do 1o e 2o Ano',
    '3rd Year Classroom': 'Salas do 3o Ano',
    "Janitor's Closet": 'Depósito do Zelador',
    'School Building 1st Floor': 'Escola - Andar 1',
    'School Building 2nd Floor': 'Escola - Andar 2',
    'Schoolyard': 'Pátio',
    'My Room': 'Meu Quarto',
    'Student Council Room': 'Sala do Grêmio',
    'Where would you like to go?': 'Para onde deseja ir?',
    'Rooftop': 'Terraço',
    'Storeroom': 'Depósito',
    'Garden': 'Jardim',
    'Library': 'Biblioteca',
    'Search': 'Procurar',
    'Infirmary': 'Enfermaria',
    'Main gate': 'Portão principal',

    # --- tela de titulo (aviso do patch) ---
    'Data Install is disabled for the patched': 'A Instalação de Dados está',
    'version of Fate/Extra CCC.': 'desativada nesta versão.',
    'It provides no benefits because the game data':
        'Não traz vantagem: os dados do jogo são',
    'is always loaded from the memory stick.': 'sempre lidos do memory stick.',

    # interface/cmn/install.bin fica em ingles de proposito. Ele vive no
    # PRELOAD.pak (nao pode mudar de tamanho), o texto ingles ja ocupa os 656
    # bytes exatos, e o arquivo e gravado em UTF-8, onde cada acento custa 2
    # bytes. So caberia portugues sem acento, o que e pior do que deixar em
    # ingles numa mensagem de erro de instalacao que quase nunca aparece.

    # --- loja ---
    "It looks like it's sold out.\nI'll try again later.":
        'Parece que está esgotado.\nVou tentar mais tarde.',
    'How many would you like to buy?': 'Quantos você quer comprar?',
    'How many would you like to sell?': 'Quantos você quer vender?',
    "It's too expensive… I'll pass.": 'Está caro demais… Vou passar.',
    'Mystic Codes': 'Artefatos Místicos',

    # --- abertura (cena 071) ---
    'This virtual space is #RUBSLunar-Sea Fields#RUBETsukumihara#REND Academy,\n'
    'generated by the psuedo-Spiritron\nworld known as the #C000246204SERIAL PHANTASM#CDEF―――':
        'Este espaço virtual é a Academia #RUBSLunar-Sea Fields#RUBETsukumihara#REND,\n'
        'gerada pelo mundo pseudo-Spiritron\nconhecido como #C000246204SERIAL PHANTASM#CDEF―――',
    'We apologize for the imposition,\n'
    'but protocol requires that your#RUBS   merits#RUBE values#REND\nbe scanned now.':
        'Desculpe o incômodo,\n'
        'mas o protocolo exige que seus#RUBS   méritos#RUBE valores#REND\nsejam escaneados agora.',
    'Label    : Transfer Student\nCategory : Not Allowed To Refuse Scans\nQuality  : E-':
        'Rótulo    : Aluno Transferido\nCategoria : Proibido Recusar Escaneamento\nQualidade : E-',
    "Scan complete.\nNow accessing the Near Side's records.":
        'Escaneamento concluído.\nAcessando os registros do Near Side.',
    'Our sincerest apologies.\nRecord access attempt    failed.':
        'Nossas sinceras desculpas.\nO acesso aos registros    falhou.',
    'Your #RUBS name#RUBEidentity#REND will need to be verified.\n'
    'Your #ROFS0003#RUBS heart #RUBEidentity#REND will need to be verified.\n'
    'Your #RUBS proof #RUBEidentity#REND will need to be verified.':
        'Seu #RUBS nome#RUBEidentidade#REND precisará ser verificado.\n'
        'Seu #ROFS0003#RUBS  ser #RUBEidentity#REND precisará ser verificado.\n'
        'Sua #RUBS prova#RUBEidentidade#REND precisará ser verificada.',
    "We're terribly sorry, but we must ask you\n"
    'to once again input your name, your gender,\nand your contracted Servant.':
        'Sentimos muito, mas precisamos pedir que\n'
        'informe outra vez seu nome, seu gênero\ne o Servo com quem tem contrato.',
    '―――Verification complete.\n'
    "We're looking forward to having you,\n#[Mister][Miss]# #C236196003#FAMILY #GIVEN#CDEF.":
        '―――Verificação concluída.\n'
        'Será um prazer recebê-#[lo][la]#,\n#[Sr.][Srta.]# #C236196003#FAMILY #GIVEN#CDEF.',
    'I enter the private room #C236196003Sakura#CDEF prepared for us.\n'
    'This is a space totally just for my Servant and me.':
        'Entro no quarto particular que #C236196003Sakura#CDEF preparou.\n'
        'É um espaço só meu e do meu Servo.',
    "Outside the window, it's nighttime.\n"
    'Apparently this indicates all communication with\nthe Student Council Room has been severed.':
        'Do lado de fora da janela, é noite.\n'
        'Pelo visto isso indica que toda comunicação com\na Sala do Grêmio foi cortada.',
    "Here, we can talk about things we don't\nwant others listening to.":
        'Aqui podemos falar de coisas que não\nqueremos que ninguém escute.',
    'Phew. Finally we can rest.\n'
    "We hardly get any chances to even breathe,\nthough that's how it always goes.":
        'Ufa. Enfim podemos descansar.\n'
        'Mal temos chance de respirar,\nmas é sempre assim mesmo.',
    'Another room with some nice ambiance. A school\n'
    'in sunset glow, a private room at night. Well,\nas long as I can rest, I have no complaints.':
        'Outro quarto de clima agradável. Uma escola\n'
        'no brilho do pôr do sol, um quarto à noite.\nSe dá para descansar, não reclamo.',
    'Wow! A fine private room! Good job,\n'
    '#C236196003Sakura#CDEF! I was hoping for a room with this\ntype of mood!':
        'Uau! Que belo quarto! Muito bem,\n'
        '#C236196003Sakura#CDEF! Eu queria um quarto com\nesse clima mesmo!',
    'Since this will be our base from now on,\n#C236196003#SVT#CDEF cautiously checks the room.':
        'Como esta será nossa base daqui em diante,\n#C236196003#SVT#CDEF inspeciona o quarto com cautela.',
    'As for me… pathetically, the moment I entered the room,\nI was drained of my strength.':
        'Quanto a mim… que vergonha: assim que\nentrei no quarto, minhas forças se esvaíram.',
    'Would you like to try loading it again?': 'Deseja tentar carregar de novo?',
    'read successfully.': 'lido com sucesso.',
    'by reading save data from Fate/EXTRA.': 'lendo os dados salvos de Fate/EXTRA.',
    'without saving the Clear Data?': 'sem salvar os Clear Data?',
}

# Entradas antigas que violavam o glossario central (ex.: classes de Servo) e
# devem voltar para msgstr "" quando encontradas.
CLEAR_FORCED = {
    'Savior': 'Salvador',
}

# field_new/main/0000.dat mora no PRELOAD.pak e nao pode mudar de tamanho nem 1 byte.
# Estas variantes curtas preservam os slots de 4 bytes em historia/main.po.
MAIN_SHORT = {
    'Newscaster': 'Locutor',
    'My Room': 'Quarto',
    'Main gate': 'Portão',
    'Library': '',
}


def po_escape(s):
    s = s.replace('\\', '\\\\').replace('"', '\\"')
    return s.replace('\r', '\\r').replace('\n', '\\n').replace('\t', '\\t')


def po_unescape(s):
    out = []
    i = 0
    while i < len(s):
        c = s[i]
        if c == '\\' and i + 1 < len(s):
            n = s[i + 1]
            out.append({'n': '\n', 'r': '\r', 't': '\t',
                        '"': '"', '\\': '\\'}.get(n, n))
            i += 2
        else:
            out.append(c)
            i += 1
    return ''.join(out)


def main():
    dry = '--dry-run' in sys.argv
    force = '--force' in sys.argv
    escaped = {po_escape(k): po_escape(v) for k, v in GLOSSARY.items()}
    escaped_clear = {po_escape(k): po_escape(v) for k, v in CLEAR_FORCED.items()}
    escaped_main_short = {po_escape(k): po_escape(v) for k, v in MAIN_SHORT.items()}
    total = 0
    touched = 0
    replaced = 0
    per_file = {}

    for path in sorted(glob.glob(os.path.join(PTBR, '*', '*.po'))):
        rel = os.path.relpath(path, PTBR).replace(os.sep, '/')
        is_main = (rel == 'historia/main.po')
        lines = open(path, encoding='utf-8').read().split('\n')
        out = []
        cur_id = None
        n = 0
        for ln in lines:
            m = re.match(r'msgid "(.*)"$', ln)
            if m:
                cur_id = m.group(1)
            ms = re.match(r'msgstr "(.*)"$', ln)
            if ms and cur_id in escaped_clear:
                have = ms.group(1)
                if have and (force or have == escaped_clear[cur_id]):
                    replaced += 1
                    out.append('msgstr ""')
                    n += 1
                else:
                    out.append(ln)
                cur_id = None
                continue
            if ms and cur_id in escaped:
                want = escaped[cur_id]
                if is_main:
                    if cur_id in escaped_main_short:
                        want = escaped_main_short[cur_id]
                    if want:
                        slot = (len(fatetext.encode(po_unescape(cur_id))) + 4) & ~3
                        if len(fatetext.encode(po_unescape(want))) + 1 > slot:
                            want = ''
                have = ms.group(1)
                if have == want:
                    cur_id = None
                    out.append(ln)
                    continue
                if have and not force:
                    cur_id = None
                    out.append(ln)
                    continue
                if have:
                    replaced += 1
                out.append('msgstr "%s"' % want)
                n += 1
                cur_id = None
                continue
            out.append(ln)
        if n:
            per_file[rel] = n
            total += n
            touched += 1
            if not dry:
                with open(path, 'w', encoding='utf-8', newline='\n') as f:
                    f.write('\n'.join(out))

    print('glossario: %d termos' % len(GLOSSARY))
    print('%s %d textos em %d arquivos (%d substituidos por divergencia)'
          % ('seriam preenchidos:' if dry else 'preenchidos:', total, touched, replaced))
    for f, n in sorted(per_file.items(), key=lambda kv: -kv[1])[:15]:
        print('   %-52s %d' % (f, n))


if __name__ == '__main__':
    main()
