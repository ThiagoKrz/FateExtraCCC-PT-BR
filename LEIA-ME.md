# Fate/Extra CCC — Tradução PT-BR

Ambiente pronto. A base é a **sua ISO já em inglês** (`EnglishBase/ccc-patched.iso`):
tudo que você não traduzir continua aparecendo em inglês no jogo.

O resultado é sempre uma **ISO pronta** em `output/ccc-ptbr.iso` — não é um patch.

---

## Como funciona (resumo)

A ISO guarda quase tudo dentro de um arquivo só, `PSP_GAME/INSDIR/GAME.DNS`,
que é um arquivo **CPK** com 14.851 itens. Dentro dele há 1.641 arquivos **PAK**,
e é dentro dos PAKs que ficam os textos:

```
ccc-patched.iso
└── GAME.DNS  (CPK)
    └── pack/*.pak
        ├── field_new/NNN/0000.dat   <- história e diálogos
        └── interface/**/*.bin       <- menus e interface
```

O fluxo de trabalho é:

```
ptbr/*.po  →  .dat / .bin  →  .pak  →  GAME.DNS  →  output/ccc-ptbr.iso
```

---

## Ciclo de trabalho

```bash
# 1. traduza: edite os arquivos em ptbr/ (no Poedit ou em qualquer editor)

# 2. gere a ISO
python tools/build.py

# 3. teste output/ccc-ptbr.iso no PPSSPP

# 4. volte ao passo 1
```

Para gerar mais rápido enquanto testa uma parte específica:

```bash
python tools/build.py --only menus/interface__shop__msg
python tools/build.py --only historia/024,historia/025
```

---

## Onde está cada coisa

| Pasta | Conteúdo |
|---|---|
| `ptbr/historia/` | **187 arquivos** — a história. Um arquivo por cena (`024.po` = cena 024) |
| `ptbr/menus/` | **37 arquivos** — loja, status, opções, save, mapa, galeria, etc. |
| `ptbr/sg/` | **62 arquivos** — Secret Gardens (perfis e episódios dos Servos) |
| `ptbr/lore/` | **16 arquivos** — Info Matrix (dados de inimigos e enciclopédia) |
| `ptbr/sistema/` | **1 arquivo** — textos dentro do executável (nomes de classe, inimigos) |
| `ptbr/_INDICE.md` | Tabela com todos os arquivos, quantos textos cada um tem e uma amostra |

**Total: 67.826 textos**, ~2,7 milhões de caracteres.

### Campos de largura fixa

Os textos de `sg/`, `lore/` e alguns de `menus/` ficam em campos de tamanho
fixo no arquivo. Nesses, o `.po` traz um comentário com o limite:

```po
#. max 47 bytes
msgctxt "0"
```

Se a tradução não couber, o `build.py` avisa e **mantém aquele arquivo em
inglês** em vez de gerar um arquivo corrompido. Acentos custam 1 byte cada
(são bytes de controle), então contam como uma letra normal.

Comece pelos menus — são poucos, aparecem o tempo todo e dão retorno visual rápido.

### Formato dos arquivos

São arquivos `.po` padrão (o mesmo do Poedit / Weblate):

```po
msgctxt "0"
msgid "Buy"
msgstr "Comprar"
```

- `msgid` = inglês original. **Não mexa.**
- `msgstr` = sua tradução. **Vazio = mantém o inglês.**
- `msgctxt` = identificador interno. **Não mexa.**
- Códigos como `#CDEF`, `#RUBS`, `#RUBE`, `#REND`, `#ROFS` são comandos de
  formatação do jogo — copie-os junto, na mesma posição.

Rodar `python tools/dump.py` de novo **preserva** o que você já traduziu.

---

## Acentos

O jogo não usa UTF-8. A equipe inglesa desenhou letras acentuadas na fonte e as
ligou a bytes de controle não usados. Fizemos o mesmo para o português.

**Funcionam (19):**

```
á é í ó É Ç          <- já vinham do patch inglês
ç ã õ â ê ô ú à      <- adicionados (minúsculas)
Á Í Ó Ú À            <- adicionados (maiúsculas)
```

**Degradam para a letra sem acento (5):** `Â` `Ã` `Ê` `Ô` `Õ`

Só restavam 13 slots de byte livres e o português precisa de 18 letras novas,
então as cinco maiúsculas menos frequentes caem para `A`/`E`/`O`. Na prática
isso quase não aparece: são letras que praticamente só surgem em texto
todo em maiúsculas. **Prefira Caixa Alta Apenas na Inicial** (`Opções`, não
`OPÇÕES`) e o problema desaparece.

O `tools/build.py` avisa sempre que encontra um caractere sem glifo.

### ⚠️ Regra que não pode ser quebrada

**Nenhum arquivo dentro do `PRELOAD.pak` pode mudar de tamanho** — nem um byte.

O patch inglês carrega o código nativo dele na memória logo depois do conteúdo
do `PRELOAD.pak`, num endereço calculado como
`base + soma(tamanho de cada arquivo + 0x40)` e **gravado dentro do EBOOT**.
Se algum arquivo cresce, o código nativo desloca, o EBOOT continua pulando para
o endereço antigo e o jogo dá **tela preta no boot**.

Foi exatamente o que aconteceu quando a `kanzi.bin` cresceu 80 bytes. Por isso
o `accents.py` **substitui** entradas da tabela de glifos (kanji que nenhum
texto do jogo usa — `tools/unusedglyphs.py` encontra 433 deles) em vez de
acrescentar. Há travas automáticas em `accents.py` e em `build.py` que abortam
o build se algum arquivo do `PRELOAD.pak` mudar de tamanho.

### Como os glifos foram feitos

`tools/accents.py` monta cada letra a partir da própria fonte do jogo: pega a
letra base e o diacrítico "emprestado" de um glifo que já existia (o agudo sai
de `á`, o grave de `è`, a cedilha de `Ç`), então o traço combina com o resto da
fonte. O til é desenhado à mão porque reduzir o `～` o achatava, e o circunflexo
é o agudo mais seu espelho. Nas maiúsculas a letra é comprimida um pouco para
abrir espaço, mantendo a linha de base.

Os glifos novos ocupam células que sobravam no fim do atlas e a `kanzi.bin`
passou de 3040 para 3053 entradas. Para gerar de novo:

```bash
python tools/accents.py --preview    # grava work/accents_preview.png
```

Se um dia precisar de mais letras, `tools/freeslots.py` varre todo o texto do
jogo e diz quais bytes ainda estão livres de verdade.

---

## As ferramentas

| Arquivo | Função |
|---|---|
| `tools/dump.py` | Lê o jogo e (re)gera os `.po` em `ptbr/` |
| `tools/build.py` | Lê os `.po` e gera `output/ccc-ptbr.iso` |
| `tools/accents.py` | Monta os glifos acentuados e grava a fonte em `work/font-ptbr/` |
| `tools/verify.py` | Abre uma ISO gerada e confere fonte e texto lá dentro |
| `tools/validate.py` | Confere nossa extração contra os ponteiros oficiais da equipe |
| `tools/cpk.py` | Leitor/gravador do CPK (`GAME.DNS`) + CRILAYLA |
| `tools/pak.py` | Leitor/gravador de PAK e CMP (IECP) |
| `tools/fatetext.py` | Codec CP932 + acentos, e o leitor dos scripts `.dat` |
| `tools/binfile.py` | Leitor/gravador dos `.bin` de menu |
| `tools/tex.py` / `kanzi.py` | Textura TXB e tabela de glifos da fonte |
| `tools/fontgrid.py` / `fontcells.py` | Renderizam o atlas da fonte para inspeção |
| `tools/freeslots.py` | Diz quais bytes de controle ainda estão livres |

Tudo foi portado para Python a partir das ferramentas oficiais da equipe inglesa
([ccc-tl/translation-tools](https://github.com/ccc-tl/translation-tools)), então
os formatos seguem exatamente a mesma especificação.

### Detalhes técnicos que importam

- **Texto maior que o original não é problema.** Nos scripts `.dat` cada fala é
  acessada por um ponteiro; quando a tradução não cabe no espaço original, ela é
  gravada no fim do arquivo e o ponteiro é reapontado. Nos `.bin` o arquivo
  inteiro é remontado.
- **A ISO não incha.** O espaço liberado pelos PAKs substituídos é reaproveitado,
  então o `GAME.DNS` continua com o mesmo tamanho e a ISO é gravada por cima da
  cópia da original. Se um dia o lote não couber, o `build.py` avisa em vez de
  gerar uma ISO quebrada.
- O `build.py` **sempre parte da sua ISO original**, nunca de uma já modificada.

---

## Refazer o ambiente do zero

`work/` é 100% regenerável a partir da sua ISO:

```bash
python -c "import sys; sys.path.insert(0,'tools'); \
  from cpk import Cpk; ..."          # extrai GAME.DNS  → work/cpk
python tools/pak.py extract work/cpk work/pak
python tools/dump.py
```

(Os passos de extração da ISO usam o 7-Zip: `7z x EnglishBase/ccc-patched.iso -owork/iso`.)

---

## Status

- [x] Formatos decifrados (CPK, PAK, CMP, DAT, BIN, TXB, fonte)
- [x] Extração completa da ISO
- [x] História exportada — conferida contra os ponteiros oficiais da equipe (0 faltando)
- [x] Geração de ISO validada de ponta a ponta
- [x] Acentos do português na fonte (19 letras)
- [x] PSP SDK instalado (`C:\pspsdk`, psp-gcc 4.3.5)
- [x] Secret Gardens, Info Matrix, entrada de nome, seleção de local (+899 textos)
- [x] `eboot` (186 textos) — strings dentro do `EBOOT.BIN`
- [ ] `items` (~493) e legendas de batalha (~1.365) — o texto vive em espaço
      compilado no código nativo; exigem reconstruir o `patch.o` com o PSP SDK
- [ ] Traduzir
- [ ] Texturas com texto (`.txb`) — menus desenhados como imagem
