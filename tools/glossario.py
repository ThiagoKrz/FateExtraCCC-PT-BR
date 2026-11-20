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

    # interface/cmn/install.bin (PRELOAD.pak, UTF-8) e traduzido a mao: o
    # arquivo inteiro precisa caber nos 656 bytes originais, entao nao entra
    # na troca automatica de termos.

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
    'Servant': 'Servo',
    'King of Heroes': 'Rei dos Heróis',
    'Green Archer': 'Archer Verde',

    # --- prompts e falas comuns de exploracao / checkpoints (mapas do Labirinto) ---
    'Activate the switch?': 'Ativar o interruptor?',
    'Press.': 'Pressionar.',
    "Don't press.": 'Não pressionar.',
    'HP & MP fully restored.': 'HP e MP totalmente restaurados.',
    'Save?': 'Salvar?',
    'Save current progress?': 'Salvar o progresso atual?',
    'Retry battle?': 'Tentar a batalha novamente?',
    'Try again?': 'Tentar novamente?',
    'Checkpoint unlocked.': 'Checkpoint desbloqueado.',
    'Return to the old school?': 'Voltar ao prédio antigo?',
    'Return to the old school.': 'Voltar ao prédio antigo.',
    'Continue to the next floor?': 'Seguir para o próximo andar?',
    'Continue to the next floor.': 'Seguir para o próximo andar.',
    'Head to the next floor?': 'Ir para o próximo andar?',
    'Return to the previous floor?': 'Voltar ao andar anterior?',
    'Return to previous floor.': 'Voltar ao andar anterior.',
    'Stay here.': 'Ficar aqui.',
    'Talk': 'Conversar',
    'I have no preference.': 'Não tenho preferência.',
    'Change into this outfit.': 'Trocar para este traje.',
    'Skip to this scene?': 'Pular para esta cena?',
    'Yes': 'Sim',
    'acquired. View now?': 'adquirido. Ver agora?',
    'has been obtained.': 'foi obtido.',
    'Even in cyberspace, you need proper rest.':
        'Mesmo no ciberespaço, você precisa\ndescansar direito.',
    'Is there a checkpoint in that area?':
        'Será que há um checkpoint nessa área?',
    "#C236196003Sakura#CDEF is right.\nLet's head back to #C000246204My Room#CDEF now.":
        '#C236196003Sakura#CDEF tem razão.\nVamos voltar ao #C000246204Meu Quarto#CDEF agora.',
    "#C236196003#SVT#CDEF is right.\nLet's head back to #C000246204My Room#CDEF and get some rest.":
        '#C236196003#SVT#CDEF tem razão.\nVamos voltar ao #C000246204Meu Quarto#CDEF e descansar.',
    "#C236196003BB#CDEF is right there.\nLet's #C000246204press on#CDEF.":
        '#C236196003BB#CDEF está logo ali.\nVamos #C000246204seguir em frente#CDEF.',
    "We obtained the #C000246204SG#CDEF.\nLet's go back to #C000246204My Room#CDEF and rest.":
        'Obtivemos o #C000246204SG#CDEF.\nVamos voltar ao #C000246204Meu Quarto#CDEF e descansar.',
    "Praetor, I've grown tired. Let us return\nto My Room and have ourselves a bath.":
        'Maestro, já me cansei.\nVoltemos ao Meu Quarto para um bom banho.',
    "I know how you feel, but knowing\nwhen to rest is also part of the battle.\nLet's head back to My Room.":
        'Sei como se sente, mas saber a hora\nde descansar também faz parte da luta.\nVamos voltar ao Meu Quarto.',
    "Darling, now is the time for rest.\nLet's return to our room and\nrecover our strength.":
        '#[Querido][Querida]#, agora é hora de descansar.\nVamos voltar para o nosso quarto\ne recuperar as forças.',
    "What an impatient #[man][woman]#. Laboring away\nis not all there is to life, you know?\nWhen it's time to rest, rest.":
        'Que #[homem][mulher]# impaciente. A vida não\nse resume a labutar, sabia?\nNa hora de descansar, descanse.',
    "Surely you aren't thinking of WALKING back?\nDo you intend to make me march for no purpose?\nLook for that #C000246204checkpoint#CDEF!":
        'Não vai querer voltar A PÉ, não é?\nQuer me fazer marchar à toa?\nProcure aquele #C000246204checkpoint#CDEF!',
    'After making a shortcut to the old school from\nthe #C000246204checkpoint#CDEF, please return to base.':
        'Após abrir um atalho do #C000246204checkpoint#CDEF\nao prédio antigo, volte à base.',
    '#C236196003#FAMILY#CDEF, you appear to have accumulated\na lot of fatigue. I recommend that\nyou return for the moment to take a rest.':
        '#C236196003#FAMILY#CDEF, parece que acumulou muita\nfadiga. Recomendo que retorne\npor ora para descansar.',
    "I'm concerned about #C236196003Rin#CDEF.":
        'Estou preocupad#[o][a]# com a #C236196003Rin#CDEF.',
    'Searching the Labyrinth is nice and all,\nbut I should #C000246204return to the old school#CDEF to\nbriefly speak with #C236196003Kiara#CDEF.':
        'Explorar o Labirinto ajuda, mas preciso\n#C000246204voltar ao prédio antigo#CDEF e falar rápido\ncom #C236196003Kiara#CDEF.',
    "I obtained the first #C000246204SG#CDEF.\nLet's briefly return to #C000246204My Room#CDEF and sort\nout the situation.":
        'Obtive o primeiro #C000246204SG#CDEF.\nVamos voltar ao #C000246204Meu Quarto#CDEF e organizar\na situação.',
    "First thing to do is activate the #C000246204checkpoint#CDEF.\nThat'll help move our search along.":
        'Primeiro, vamos ativar o #C000246204checkpoint#CDEF.\nIsso vai agilizar a nossa busca.',
    "What's wrong, Praetor?\nLet's #C000246204continue onward#CDEF!":
        'O que houve, Maestro?\nVamos #C000246204seguir em frente#CDEF!',
    "Don't worry. I'll protect you, Darling.\nSo, continue on #C000246204ahead#CDEF.":
        'Não se preocupe. Vou proteger você,\n#[Querido][Querida]#. Siga em #C000246204frente#CDEF.',
    "Surely you're not telling me that you're\nfrightened? Even you understand that stopping\nhere is impermissible, yes?":
        'Não me diga que ficou com medo?\nMesmo você sabe que parar\naqui é inadmissível, não sabe?',
    '#C236196003#FAMILY#CDEF. After you activate the #C000246204checkpoint#CDEF,\nplease have yourself a rest in your\nprivate room.':
        '#C236196003#FAMILY#CDEF. Após ativar o #C000246204checkpoint#CDEF,\ndescanse um pouco em seu\nquarto particular.',
    "Once you activate the #C000246204checkpoint#CDEF,\nuse it to get back here.\nI'll bet you're exhausted, #C236196003#NICK#CDEF.":
        'Ative o #C000246204checkpoint#CDEF e use-o\npara voltar aqui.\nDeve estar exaust#[o][a]#, #C236196003#NICK#CDEF.',
    "#[Mr.][Ms.]##C236196003 #NICK#CDEF, return to base for now.\nLet's discuss our plan\nin the #C000246204Student Council Room#CDEF.":
        '#[Sr.][Srta.]##C236196003 #NICK#CDEF, volte à base agora.\nDiscutiremos o plano\nna #C000246204Sala do Grêmio#CDEF.',
    "#C236196003#GIVEN#CDEF, please come back.\nYou've accumulated a lot of fatigue;\nany more will be dangerous!":
        '#C236196003#GIVEN#CDEF, por favor, volte.\nVocê acumulou muita fadiga;\ncontinuar será perigoso!',
    "#C236196003Sakura#CDEF's worried state gets across to\nme even over the transmission.":
        'A preocupação da #C236196003Sakura#CDEF fica clara\naté pela transmissão.',
    "She's right, it would be best if\nwe returned to the #C000246204Old School Building#CDEF.":
        'Ela tem razão, melhor voltarmos\nao #C000246204Prédio Antigo da Escola#CDEF.',
    "We got the #C000246204SG#CDEF.\nMission complete.\nLet's head home and get some rest.":
        'Pegamos o #C000246204SG#CDEF.\nMissão cumprida.\nVamos voltar e descansar.',
    "Where are you going? We secured the #C000246204SG#CDEF.\nThere's nothing urgent to tend to.\nBack to #C000246204My Room#CDEF, now.":
        'Onde vai? Já garantimos o #C000246204SG#CDEF.\nNão há mais urgência alguma.\nDe volta ao #C000246204Meu Quarto#CDEF, agora.',
    'Hrrrm? Where are you going, #C236196003#FAMILY\n#GIVEN#CDEF? Where are you going,\nleaving me behind?':
        'Hummm? Onde vai, #C236196003#FAMILY\n#GIVEN#CDEF? Para onde está indo,\nme deixando para trás?',
    "Wait, Praetor. If we're going to head back,\nit'll behoove us for the future to have\nthe #C000246204checkpoint#CDEF activated.":
        'Espere, Maestro. Antes de voltarmos,\nconvém ativar o #C000246204checkpoint#CDEF\npara facilitar daqui em diante.',
    "Master, let's look for the #C000246204checkpoint#CDEF.\nIt should be around here somewhere…":
        '#[Mestre][Mestra]#, procuremos o #C000246204checkpoint#CDEF.\nDeve estar por aqui em algum lugar…',
    "We don't need to walk all the way back.\nWe can use the #C000246204checkpoint#CDEF to reach the\nold school in a flash. Very nifty.":
        'Não precisamos voltar tudo a pé.\nCom o #C000246204checkpoint#CDEF chegamos num\npiscar ao prédio antigo. Bem prático.',
    "We're in a race against time.\nWe need to hurry to the #C000246204Moon Cell's Core#CDEF――!":
        'Corremos contra o tempo.\nTemos que ir rápido ao\n#C000246204Núcleo do Moon Cell#CDEF――!',
    "I can't let #C236196003Shinji#CDEF's hopes go to waste.\nLet's press on so we can catch up to #C236196003Meltlilith#CDEF!":
        'Não posso desperdiçar as esperanças\ndo #C236196003Shinji#CDEF. Vamos alcançar\na #C236196003Meltlilith#CDEF!',
    "We took more damage from our fight with #C236196003Lancer#CDEF\nthan I expected. Now would be a good time to head\nback to the old school.\nLuckily, there's a #C000246204checkpoint#CDEF near us.":
        'Sofremos mais dano contra a #C236196003Lancer#CDEF\ndo que eu previa. Melhor voltar ao prédio\nantigo; por sorte há um #C000246204checkpoint#CDEF perto.',
    "We obtained the #C000246204SG#CDEF. Let's return to the\n#C000246204Old School Building#CDEF for the time being.\nWe can come again after we recover.":
        'Obtivemos o #C000246204SG#CDEF. Vamos voltar por ora\nao #C000246204Prédio Antigo da Escola#CDEF\ne retornar depois de nos recuperarmos.',
    "Before we go to the next floor,\nlet's #C000246204head back to the Student Council Room#CDEF.\nWe need to hand over the data we got from #C236196003Green Archer#CDEF.\nHe gave his life to entrust us with it.":
        'Antes de ir ao próximo andar,\n#C000246204voltemos à Sala do Grêmio#CDEF para entregar\nos dados que #C236196003Archer Verde#CDEF nos confiou.',
    "For a second there, I was thinking about\nleaving #C236196003Gatou#CDEF and heading back,\nbut it probably won't rest easy on my conscience,\nso let's turn back.":
        'Pensei por um segundo em deixar #C236196003Gatou#CDEF\ne ir embora, mas minha consciência não\nme deixaria em paz. Vamos voltar.',
    "Huh? You're still in the #C000246204Sakura Labyrinth#CDEF?\nCome on, there's nothing to do there.\nGet your butt back here!":
        'Hã? Ainda no #C000246204Labirinto de Sakura#CDEF?\nNão tem nada para fazer aí.\nTrate de voltar logo pra cá!',
    "We'll talk about what comes next tomorrow,\nso #C000246204come back and get some rest#CDEF.\nAfter, drop by the Student Council Room.":
        'Falamos do próximo passo amanhã,\nentão #C000246204volte e vá descansar#CDEF.\nDepois, passe na Sala do Grêmio.',
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
