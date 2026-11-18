# Diário de Mudanças e Descobertas

Estado atual do projeto e histórico das decisões. **Leia este arquivo antes de
começar qualquer trabalho.** Ele existe para que uma sessão nova continue de
onde a anterior parou sem redescobrir nada.

## Como usar

Ao terminar qualquer mudança maior, decisão de arquitetura ou descoberta sobre o
formato do jogo, acrescente uma entrada no topo de **Histórico**, com data, o
que mudou e **por quê**. Se a descoberta virar uma regra permanente, promova-a
também para a seção **Regras duras** ou para o glossário.

Entrada não registrada = trabalho incompleto.

---

## Estado atual

| | |
|---|---|
| Base | `EnglishBase/ccc-patched.iso` (patch inglês do ccc-tl) |
| Saída | `output/ccc-ptbr.iso` — ISO pronta, não é patch |
| Textos exportados | 67.797 em 292 arquivos |
| Traduzidos | 7.745 (~11,4%) |
| Acentos | 19 letras funcionando na fonte |
| Boot | testado e funcionando no PPSSPP |

Unidades de texto cobertas: história (`dat`), menus (`misc`), Secret Gardens
(`sg`), Info Matrix (`infomatrix`), in-dungeon, EBOOT.

Unidades **bloqueadas**: `items` (~493) e `subs` (~1.365). O texto delas vive em
espaço de relocação compilado no código nativo (`hax/patch.o`). Exigem
reconstruir o nativo com o PSP SDK, já instalado em `C:/pspsdk` (psp-gcc 4.3.5,
`PSPSDK_HOME` configurado).

---

## Regras duras

Violar qualquer uma destas quebra o jogo.

### 1. `PRELOAD.pak` não pode mudar de tamanho

Nem um byte. O `CccAsmPatcher` da equipe calcula:

```kotlin
val preloadInjectStart = baseLoadAddress + pakEntries.sizeInGame()  // soma de (tamanho + 0x40)
val patchStart = preloadInjectStart + 0x40
```

e grava esse endereço **dentro do EBOOT**. Se um arquivo do PRELOAD cresce, o
código nativo desloca, o EBOOT continua pulando para o endereço antigo e o jogo
dá tela preta.

Proteções automáticas em `tools/accents.py` (aborta) e `tools/build.py`
(mantém o arquivo em inglês e avisa).

Arquivos afetados: `font.txb`, `kanzi.bin`, `interface/cmn/install.bin`,
`field_new/main/0000.dat`, entre outros.

### 2. Acentos são bytes de controle, não UTF-8

A equipe inglesa ligou glifos acentuados a bytes de controle não usados
(mapa em `CccTranslation.kt`). Nós continuamos o mesmo esquema.

- Funcionam: `á é í ó ú â ê ô ã õ ç à Á É Í Ó Ú À Ç`
- Rebaixam para a letra sem acento: `Â Ã Ê Ô Õ`

`TextMeasure` mede a faixa `0x07–0x1F` com largura de ASCII (7px) e códigos de
2 bytes com largura cheia (15px) — por isso acento **tem** que ser byte de
controle, senão sai com espaçamento duplo.

### 3. Texto da história pode crescer; campo fixo não

- `ptbr/historia/`: cada fala tem ponteiro (`ptrLoc`), então texto maior é
  gravado no fim do arquivo e o ponteiro é reapontado. Sem limite.
- `sg`, `lore`, `eboot` e parte de `menus`: campos de largura fixa. O `.po` traz
  `#. max N bytes`. Estourou, o build mantém em inglês e avisa.

---

## Mapa dos formatos

```
ccc-patched.iso
├── PSP_GAME/SYSDIR/EBOOT.BIN   ELF já descriptografado (186 strings)
└── PSP_GAME/INSDIR/GAME.DNS    CPK puro, 14.851 itens
    └── pack/*.pak              PAK (ou CMP = PAK comprimido IECP)
        ├── field_new/NNN/*.dat bytecode com strings inline (4-byte align)
        ├── interface/**/*.bin  índice+tamanho+string, ou campos fixos
        └── font.txb + kanzi.bin
```

- **CPK**: tabela `@UTF`, compressão CRILAYLA. Porte em `tools/cpk.py`.
- **PAK**: `u16 count, u16 flag(0x8000 = tem paths), u32 tamanhos[], align16,
  [path(64) + dados]`. Porte em `tools/pak.py`.
- **CMP**: LZSS com magic `IECP`.
- **DAT**: bytecode. As strings são achadas por varredura de opcodes
  (porte de `DatScriptJsonDumper`). Cada uma tem `ptrLoc` e `textLoc`.
- **kanzi.bin**: `u32 count` + entradas de 6 bytes
  `[código SJIS 2 bytes][o caractere em UTF-8, 4 bytes]`. Código de 1 byte vira
  `00 XX`; de 2 bytes é little-endian.
  **O índice da entrada É a célula do glifo** em `font.txb`:
  textura = `índice // 256`, célula 16×16, 16 por linha, 12 texturas de 256×256.
- **font.txb**: PAK de 12 texturas 4bpp, sem swizzle, paleta = rampa de alfa
  branco (índice = opacidade). Copiar pixels entre texturas é seguro.

---

## Histórico

### 2026-11-17 — Organização em capítulos (`trabalho/`), Planilha de Progresso e Painel Gráfico

Replicado no projeto Fate/Extra CCC o mesmo fluxo de trabalho em equipe dos projetos irmãos (`FHA-Remastered-PT-BR`, `FSN-Remastered-PT-BR`, `mahoyo-pt-br` e `TsukihimeRE-fatecafe`), adaptado aos formatos `.po`/`.dat`/`.bin` e travas do PSP:

- **`tools/catalogo_ccc.py` e pasta `trabalho/` (`00_prologo` a `14_mapas_base_auto`)**:
  - Os 292 arquivos `.po` de `ptbr/` (67.797 entradas; 30.016 strings únicas em inglês) foram catalogados em 15 pastas por capítulo/categoria e espelhados como JSONs legíveis em `trabalho/` com `trabalho/manifesto.json`.
  - Mapeados separadamente os **81 mapas sem falas exclusivas** em `14_mapas_base_auto/` (só cabeçalho comum do motor) e os **espelhos de Meu Quarto** (`071` → `032` e `033`, com 4.096 strings compartilhadas).
- **`tools/scripts_ccc.py`**:
  - Sincronização bidirecional entre `trabalho/*.json` e `ptbr/*.po` (preservando cabeçalho, `msgctxt` e `msgid` originais), propagação automática de traduções repetidas (`--sync-repeats`) e validador completo (`--validate`: largura em pixels via `medida.py`, limites de bytes de `fixedbin`/`eboot.py`/`PRELOAD.pak`, integridade de códigos `#C...#CDEF`/`#[masc][fem]#`, caixa alta sem glifo e alertas de gênero via `genero.py`).
  - Ajuste técnico documentado: `sistema/eboot` e `historia/main` usam terminação simples de 1 byte NUL (`len(enc) <= max_bytes`), diferente do alinhamento em 4 bytes dos arquivos `fixedbin`.
- **`Fate_Extra_CCC_Progresso_Geral.xlsx`, `FATE EXTRA CCC PROGRESSO - Geral.csv` e Google Sheets (`tools/gerar_planilha_progresso.py`)**:
  - Planilha no padrão FHA/Mahoyo (aba `Geral`, congelada em `A3`, colunas `A:H`, resumo lateral em `J1:M17` com `COUNTIFS`/`IFERROR`/`SUMIF` por capítulo, validação suspensa em `Estado` e preservação automática de `REVISORES`, `Testado Por` e `Revisado` ao atualizar).
  - Publicada no Google Sheets em [FATE EXTRA CCC PROGRESSO](https://docs.google.com/spreadsheets/d/1sML42bCigiHD25WuX4kTvQTPa5vRphshMTX5kRlXDsQ/edit).
- **Painel Gráfico (`Abrir painel.cmd`, `trabalho/Painel.pyw`, `tools/painel_ccc.py`, `tools/painel_extras.py`) + `CONTRIBUINDO.md`**:
  - Interface Tkinter dark/light mode com árvore de capítulos, filtro para ocultar os 81 mapas base, tabela de falas, régua em tempo real (pixels + bytes + gênero), botões de tags/`#[masc][fem]#`, editor `.po` bruto, **Busca global (`Ctrl+Shift+F`)**, **Conferir glossário** (`standards/GLOSSARIO_CCC_OPERACIONAL.json` + `GLOSSARIO_TYPEMOON_OPERACIONAL.json`), sincronização de repetidas e compilação direta via `tools/build.py` (`--only` ou ISO completa).

### 2026-11-17 — Alinhamento ao padrão unificado Fate Café / FSN / FHA / Mahoyo / Tsukihime

Auditoria completa do projeto revelou que as regras e o glossário locais (de
17/09/2026) tinham ficado congelados antes da consolidação unificada aplicada
nos projetos irmãos (`fate-cafe-react`, `FSN-Remastered-PT-BR`,
`FHA-Remastered-PT-BR`, `mahoyo-pt-br`, `mahoyo_manga` e `TsukihimeRE-fatecafe`).

Mudanças aplicadas:

1. **Glossário central sincronizado:** copiado
   `C:/Users/Thiago/Desktop/fate-cafe-react/standards/type-moon/GLOSSARIO_TYPEMOON_OPERACIONAL.json`
   (incluindo seções de SE.RA.PH e `regras.convencoes_localizacao`) para
   `standards/GLOSSARIO_TYPEMOON_OPERACIONAL.json` (SHA-256 `C24C2F04C779...`).
2. **Documentação e regras unificadas:** atualizados
   `standards/GLOSSARIO_CCC_OPERACIONAL.json`, `standards/PROMPT_TRADUCAO_CCC.md`,
   `standards/README.md` e `CLAUDE.md`, além da criação de `AGENTS.md` e
   `GEMINI.md` idênticos na raiz:
   - `Servant` → **Servo** (`Servos`); `Master` → **Mestre** (`Mestres` / `Mestra`);
     `Noble Phantasm` → **Fantasma Nobre**; `Mystic Code` → **Artefato Místico**.
   - Classes de Servo (incluindo `Savior`, `Saver`, `Gunner`, `Alter Ego`,
     `Moon Cancer`, `Ruler`, etc.) nunca são traduzidas.
   - Nomes japoneses completos sempre em **ordem japonesa (Sobrenome Nome)**,
     sem mácrons (`Kishinami Hakuno`, `Tohsaka Rin`, `Matou Sakura`,
     `Matou Shinji`, `Ryuudou Issei`, `Fujimura Taiga`, `Aozaki Touko`,
     `Kotomine Kirei`, `Sessyoin Kiara`, `Carigiri Jinako`, `Monji Gatou`),
     mantendo honoríficos (`-san`, `-kun`, `-chan`, `-sensei`, `Senpai`, `Kouhai`).
   - Adicionadas convenções de `Magia Verdadeira` (`魔法`) vs `magia` (`魔術`),
     `Feiticeiro(a)` (`魔法使い`) vs `mago(a)` (`魔術師`), onomatopeias
     abrasileiradas, Lista Negra de tradutês, perfis de voz (escala 1–4) e
     Protocolo Antideriva / Passe Triplo.
3. **`tools/glossario.py` e limpeza em massa (`--force`):**
   - Removido `'Savior': 'Salvador'` via `CLEAR_FORCED` (voltando para `""` nos
     187 arquivos `.po`).
   - Atualizadas as entradas com `Servo`, `Mestre`, `Artefato Místico` e os 7
     nomes japoneses completos em `locationOrName` (`Tohsaka Rin`, `Matou Shinji`,
     `Matou Sakura`, `Fujimura Taiga`, `Ryuudou Issei`, `Sessyoin Kiara`,
     `Carigiri Jinako`). Total aplicado: **1.529 textos em 200 arquivos**
     (204 substituídos por divergência), levando o total traduzido para
     **7.745 / 67.797 (11,4%)**.
   - Adicionada proteção `MAIN_SHORT` + checagem de slot de 4 bytes para
     `historia/main.po`: `field_new/main/0000.dat` agora cabe in-place dentro de
     `PRELOAD.pak` com exatamente **14.528 bytes** (0 bytes de crescimento), sem
     ser descartado pelo build.
4. **Correções manuais pontuais:**
   - `ptbr/historia/001.po`: adicionado seletor `#[masc][fem]#` em `510516`
     (`acostumad#[o][a]#`) e `512464` (`forçá-#[lo][la]#`), e corrigido
     `Ryuudou Issei` em `510860`.
   - `ptbr/historia/007.po`: corrigido `Carigiri Jinako` em `523452` e `525148`.
   - `ptbr/sg/interface__sg__sg_ner_text1.po`: corrigida acentuação em `0`
     (`Amante de Haréns`).
   - `ptbr/sistema/eboot.po`: revertido `6` (`Berserker Gigante` → `""`, classe
     não traduzida e estourava 11 bytes) e corrigida acentuação em `13` (`Efígie
     Saber`) e `14` (`Efígie Archer`). Observação: a entrada `66` (`My Room` →
     `Meu Quarto`) segue pulada pelo `eboot.py` por precisar de 11 bytes onde
     cabem 10.

### 2026-09-17 — Largura de linha e gênero viraram verificação automática

Teste no emulador expôs duas falhas sistêmicas da tradução, não do pipeline:

1. **Linha cortada na tela.** O jogo não quebra linha sozinho: o que passa da
   largura da caixa some. Uma fala de 51 caracteres foi cortada no meio da
   palavra.
2. **Concordância de gênero.** O jogador escolhe o gênero do protagonista.
   Inglês não marca gênero em adjetivo, português marca — saiu "cara de bobo"
   com a protagonista feminina.

Limites reais, tirados do `CccWidthLimit` oficial (cada caractere comum, mesmo
acentuado, mede 7px): diálogo **338px = 48 caracteres**, última linha **319px =
45** (mais estreita por causa da seta de avançar), escolha 350px em 1 linha,
in-dungeon 396px em 2 linhas, Info Matrix 423px, SG 415px. Caracteres largos
(`…` `～` `―` …) medem 15px. Nomes variáveis são medidos no pior caso:
`#FAMILY`/`#GIVEN` contam 11 caracteres, `#SVT` conta 9, e `#[a][b]#` conta pela
variante mais longa.

Ferramentas novas:

- `tools/medida.py` — porte de `TextMeasure` + `CccWidthLimit` +
  `replaceControlCodesForTextMeasure`. Varre tudo e aponta o corte em
  caracteres. **Integrado ao `build.py`**, que agora avisa a cada build.
- `tools/genero.py` — levanta suspeitas de concordância. Não decide sozinho,
  porque a mesma palavra pode falar de outro personagem (`novo jogo`,
  `conhecido como`). A lista `GENDERED` cresce conforme a tradução avança.

A varredura achou **24 falas estourando** em 001, 007, 032, 033 e 071, e 3 casos
reais de gênero. Todos corrigidos; a varredura fecha em zero.

Lição: duas das 24 vinham do glossário e apareciam em três cenas ao mesmo tempo.
Corrigir no glossário e rodar `--force` conserta todas de uma vez — sempre
verifique se a frase é compartilhada antes de editar arquivo por arquivo.

### 2026-09-17 — Cena 007 traduzida e glossário ampliado

`ptbr/historia/007.po` (apresentação da Jinako no depósito) está completo: 106
entradas traduzidas e 42 deixadas de propósito (nomes próprios e um token de
valor, que pelo glossário não se traduzem). 68 textos com acento confirmados
dentro da ISO gerada.

O glossário subiu de 86 para 114 termos ao absorver o que se repete entre cenas:
rótulos de local (`School Building 1F`, `Classroom 2-A`, `Janitor's Closet`),
papéis (`Male Student`, `Father Kotomine`) e os avisos de item e Clear Data.
Efeito: **+4.371 textos preenchidos em 187 arquivos** numa rodada.

Lição de processo: termo que aparece em mais de uma cena vai para
`tools/glossario.py`, nunca traduzido à mão arquivo a arquivo. As variantes
importam — `School Building 1st Floor` e `School Building 1F` são strings
diferentes e ambas precisam estar no glossário.

Limitação que ficou visível: `field_new/main/0000.dat` mora no `PRELOAD.pak` e
já estoura 80 bytes com a tradução atual, então continua em inglês. À medida que
o glossário crescer, esse arquivo vai precisar de traduções propositalmente mais
curtas para caber.

### 2026-09-17 — Til resolvido: três linhas esparsas

Foram três tentativas até acertar, e a lição vale para qualquer diacrítico novo.

1. **Reduzir o `～` do próprio jogo por interpolação** — não funciona em direção
   nenhuma. Reduzir na vertical achata a onda; reduzir só na horizontal e depois
   fundir linhas achata igual. Sempre vira macron (`ā`).
2. **Três linhas com traço encorpado** — a onda aparece, mas o acento fica
   pesado demais e desproporcional à letra.
3. **Três linhas esparsas, um pixel de traço por coluna** ← foi esta.
   Crista à esquerda (linha 0), passagem pelo meio (linha 1), vale à direita
   (linha 2), voltando ao meio no fim. Metade da tinta da tentativa 2, com a
   onda igualmente nítida.

Também ficou provado que **duas linhas não servem para o til**: não há
deslocamento vertical suficiente e a suavização preenche os vãos, devolvendo uma
barra reta.

O circunflexo é um bitmap de 2 linhas com apex baixo. Espelhar o acento agudo
para formar `^` gerava um caret quase tão largo quanto a letra, e 3 linhas o
deixavam pontudo demais.

Método que funcionou para decidir: gerar as variantes lado a lado sobre a letra
`a`, ampliadas, e comparar. Julgar bitmap de 16×16 no olho, um de cada vez, não
funciona.

### 2026-09-17 — Documentação de padrões criada

Criados `standards/` (glossário, README, prompt, este diário) e `CLAUDE.md` na
raiz, herdando o padrão Type-Moon do Fate Café. Instituída a regra de registro
obrigatório.

### 2026-09-17 — ISO passou a ser reconstruída quando não cabe

Com 183 pacotes traduzidos o CPK estourou em 0,8 MiB o espaço original do
`GAME.DNS`, e injetar numa cópia da ISO deixou de funcionar.

`tools/isobuild.py` reconstrói a imagem inteira com pycdlib, copiando os
identificadores de volume do original. O `build.py` escolhe sozinho: injeta
enquanto couber, reconstrói quando não couber. Sem isso a tradução travaria por
volta dos 5%.

Efeito colateral esperado: a ISO reconstruída é menor (1,34 GiB vs 1,41), porque
não replica os espaços vazios do original. PPSSPP aceita normalmente.

### 2026-09-17 — Glossário em massa

`tools/glossario.py`: aplica termos por correspondência exata de `msgid` em
todos os `.po`. Primeira rodada preencheu 2.082 textos em 202 arquivos — locais,
Sim/Não e avisos de save se repetem em quase toda cena.

Modos: padrão (só preenche vazio), `--dry-run`, `--force` (corrige divergência).

### 2026-09-17 — Dois erros de detecção de dados corrigidos

1. `cmn/treasure_*.bin` eram **binário**, não texto: meu heurístico aceitava
   qualquer coisa que decodificasse para caracteres imprimíveis. Traduzi-los
   corromperia dados. `looks_like_text` agora exige sequências reais de letras.
2. `interface/cmn/install.bin` é **UTF-8**, não CP932 (por isso aparecia
   `UMD邃｢` em vez de `UMD™`). A equipe passa charset explícito para esse
   arquivo. Suporte adicionado, mas o arquivo fica em inglês de propósito: está
   no PRELOAD, o inglês já ocupa os 656 bytes exatos, e em UTF-8 cada acento
   custa 2 bytes.

### 2026-09-16 — Tela preta no boot: causa e correção

Sintoma: `Bad memory access: 00000012 / 0000000e` (desreferência de NULL).

Causa: a `kanzi.bin` cresceu 80 bytes ao ganhar 13 entradas para os acentos
novos, deslocando o código nativo (ver **Regra dura 1**).

Correção: `accents.py` passou a **substituir** entradas em vez de acrescentar.
`tools/unusedglyphs.py` varre todo o texto do jogo e cruza com a tabela — há
**433 kanji que nenhum texto usa**. Os 13 novos ocupam índices altos entre eles.

Método de diagnóstico que funcionou, na ordem: log do PPSSPP → `integrity.py`
(descartou o patcher de CPK) → round-trip dos escritores de PAK/TXB (descartou
os escritores) → bissecção com `--only` (isolou a fonte) → leitura do código
Kotlin da equipe (achou a causa).

### 2026-09-16 — Acentos PT-BR na fonte

13 letras novas compostas a partir da própria fonte do jogo: letra base +
diacrítico extraído por diferença de um glifo existente (agudo de `á`, grave de
`è`, cedilha de `Ç`). Maiúsculas são comprimidas verticalmente para abrir espaço,
mantendo a linha de base.

`tools/freeslots.py` mediu quais bytes de controle estão livres de verdade:
sobraram **13** (e `0x03` está em uso, ao contrário do que a estimativa inicial
supunha). Por isso `Â Ã Ê Ô Õ` ficaram de fora.

### 2026-09-16 — Cobertura de texto verificada contra os dados da equipe

Os 29.485 ponteiros do `dat-pointers.json` oficial resolvem 100% contra os
arquivos da nossa ISO. Textos únicos: 29.357 oficial vs 29.360 nossos, e **zero**
presentes no oficial e ausentes no nosso. A extração da história é superconjunto
da deles.

Descobertas do mesmo levantamento:

- A unidade `indungeon` já sai junto da história (tipo `inDungeon` do scan).
- Os `.bin` de item não contêm texto, só marcadores `!rmap>!<endereço>`. Procurei
  no `patch.o` inclusive por força bruta em 143 mil bases possíveis: não está lá.
  O texto é gerado na compilação do nativo.
- Os offsets de `eboot/pointers.json` continuam válidos no EBOOT já patcheado,
  porque a equipe sobrescreve no lugar.
- `BOOT.BIN` é só zeros; só o `EBOOT.BIN` importa.

### 2026-09-16 — Arquitetura definida

Decidido **não** usar o toolkit Kotlin como build system: ele vai de ISO japonesa
para traduzida, exige a ISO JP (não temos) e reaplica patches de ASM num EBOOT
que já está patcheado. Os formatos foram portados para Python, operando direto
sobre a ISO inglesa, de modo que o não traduzido continue em inglês.

O toolkit deles segue sendo a especificação dos formatos e foi compilado com
sucesso (precisa do plugin `foojay-resolver-convention` no `settings.gradle`
para baixar o JDK 11).

---

## Pegadinhas do ambiente

- O `pip` desta instalação do Python 3.11 está quebrado (truststore + pygments).
  `pycdlib` foi instalado extraindo o wheel direto no `site-packages`.
- O console precisa de `PYTHONIOENCODING=utf-8` para imprimir acentos.
- WSL não funciona nesta máquina: virtualização desabilitada no firmware.
- PPSSPP em `C:/Program Files/PPSSPP/PPSSPPWindows64.exe`, aceita `--log=<arquivo>`.
