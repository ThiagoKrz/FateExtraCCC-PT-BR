"""Procura concordância de gênero que precisa do seletor #[masc][fem]#.

O jogo deixa o jogador escolher o gênero do protagonista. Em inglês isso não
aparece, mas em português todo adjetivo ou particípio que se refere a ele muda
de forma. Onde isso acontecer, o texto precisa do seletor `#[a][b]#`
(primeira opção masculina, segunda feminina).

Este verificador não decide sozinho: ele levanta suspeitas para revisão humana,
porque a mesma palavra pode estar se referindo a outro personagem.

Uso:  python tools/genero.py            # varre tudo que está traduzido
      python tools/genero.py historia/007
"""
import glob
import os
import re
import sys

# adjetivos e particípios comuns que mudam com o gênero de quem fala ou de quem
# é falado; a lista cresce conforme a tradução avança
GENDERED = [
    'acostumado', 'cansado', 'preparado', 'pronto', 'sozinho', 'obrigado',
    'certo', 'seguro', 'surpreso', 'bobo', 'direto', 'estranho', 'esquisito',
    'perdido', 'confuso', 'calado', 'quieto', 'ocupado', 'livre', 'solto',
    'nervoso', 'curioso', 'sério', 'honesto', 'sincero', 'burro', 'idiota',
    'louco', 'maluco', 'chato', 'velho', 'novo', 'alto', 'baixo', 'gordo',
    'magro', 'forte', 'fraco', 'bonito', 'feio', 'famoso', 'conhecido',
    'assustado', 'animado', 'satisfeito', 'decidido', 'disposto', 'apaixonado',
    'ferido', 'morto', 'vivo', 'salvo', 'escolhido', 'chamado', 'aceito',
]

# marcas de que a frase fala COM ou SOBRE o protagonista
ABOUT_PLAYER = ['#GIVEN', '#FAMILY', 'você', 'Você', 'te ', ' lhe ']


def _entries(path):
    txt = open(path, encoding='utf-8').read()
    return re.findall(r'#\. ([^\n]*)\nmsgctxt "([^"]+)"\nmsgid "(.*)"\nmsgstr "(.*)"', txt)


def _unescape(s):
    return (s.replace('\\n', '\n').replace('\\"', '"')
             .replace('\\t', '\t').replace('\\\\', '\\'))


def suspects(text):
    """Palavras com gênero fora de um seletor #[a][b]#."""
    # o que já está dentro de um seletor está resolvido
    outside = re.sub(r'#\[(.*?)\]\[(.*?)\]#', '', text)
    if not any(k in outside for k in ABOUT_PLAYER):
        return []
    found = []
    low = outside.lower()
    for w in GENDERED:
        for m in re.finditer(r'\b%s\b' % re.escape(w), low):
            found.append(w)
    return sorted(set(found))


def sweep(target=None):
    root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ptbr')
    pattern = os.path.join(root, target + '.po') if target else os.path.join(root, '*', '*.po')
    n = 0
    for path in sorted(glob.glob(pattern)):
        rel = os.path.relpath(path, root).replace(os.sep, '/')[:-3]
        for types, ctx, src, tr in _entries(path):
            if not tr:
                continue
            got = suspects(_unescape(tr))
            if not got:
                continue
            n += 1
            print('%s [%s]  suspeitas: %s' % (rel, ctx, ', '.join(got)))
            for line in _unescape(tr).split('\n'):
                print('   | %s' % line)
    print()
    print('entradas para revisar: %d' % n)
    print('Regra: se a palavra se refere ao protagonista, troque por #[masc][fem]#.')
    return n


if __name__ == '__main__':
    sweep(sys.argv[1] if len(sys.argv) > 1 else None)
