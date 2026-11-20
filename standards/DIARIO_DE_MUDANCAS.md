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
| Cobertura do catálogo | 67.797 / 67.797 entradas cobertas em 292 unidades, incluindo as exceções do catálogo |
| Textos nativos | 545 campos de item e 2.057 segmentos de legenda localizados |
| Textos em texturas | Aviso de abertura e menu Sistema/Arquivos (`patch_ui.py`) e lotes 1–4 em `ptbr/graficos/lote*.json`, aplicados pelo `build.py`. Falta o lote 5 (tutoriais e créditos) |
| Acentos | 19 letras funcionando na fonte |
| Boot | A ISO de teste anterior chegou ao aviso e ao menu Sistema no PPSSPP. A v2 foi verificada por extração e comparação binária |

Unidades de texto cobertas: história (`dat`), menus (`misc`), Secret Gardens
(`sg`), Info Matrix (`infomatrix`), in-dungeon, EBOOT.

Pendências identificadas: triagem dos rótulos residuais do EBOOT e tradução do
texto gravado nas outras texturas (inventário de 2026-11-18). As mensagens de
instalação de dados foram traduzidas, mas ainda não entraram numa ISO de teste. A cobertura
do catálogo de texto é independente da cobertura das texturas da interface.

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

### 2026-11-18 — Créditos do Fate Café (logo nos créditos finais, aviso no boot e mensagem de instalação)

- Adicionada a logo oficial do Fate Café em `ptbr/graficos/fate_cafe_logo.png` (1000×1000 RGBA) e integrada à cadeia de build em três pontos:
  - **Créditos finais (`interface/staffroll/staffroll_03.txb`, textura #4):** novo módulo `tools/creditos_ui.py`, chamado automaticamente por `tools/build.py` (`patched_textures`). Desloca o bloco `--- CCC TRANSLATION TEAM ---` 46 px à esquerda (preservando 100% dos pixels e das 107 cores originais) e insere a logo colorida (114×114) à direita usando os 149 slots livres da paleta RGBA8888 (120 cores opacas + 8 níveis de alfa para suavizar a borda circular). Mantém o tamanho exato de `staffroll_03.txb` (1.193.072 bytes) e entra nos dois PAKs de créditos (`ev_scn_c07_credit.pak` e `ev_scn_staffroll.pak`).
  - **Tela de aviso no boot (`interface/logo/0000.txb`, textura #4):** `tools/patch_ui.py` (`notice_pixels`) sobe ligeiramente as 6 linhas do `<Aviso>` (`y = 32, 66, 85, 104, 123, 158`) e desenha a logo do Fate Café em escala de cinza (64×64) centralizada em `y = 194`, dentro da paleta original de 16 tons e mantendo o tamanho exato (110.704 bytes).
  - **Aviso de Instalação de Dados (`ptbr/menus/interface__title__msg.po`):** `msgctxt "1"` atualizado para `"desativada nesta versão PT-BR do Fate Café."` (`medida.py` e `genero.py`: 0 problemas).
- Nota técnica sobre o logo da tela de título (`interface/title/0000.txb`, textura #6): todos os 157 blocos armazenados já estão ocupados pelo logo oficial `Fate/EXTRA CCC` (paleta magenta/branca de 256 cores), então a logo oficial da tela de título foi mantida intacta.
- **ISO final gerada e verificada:** `output/ccc-ptbr.iso` (1,34 GiB, SHA-256 `5C6939774D91102F9332739CE6A891F79BED75B87A5A9D6498AEB888B3291430`), produzida pela cadeia completa (`build.py` → `native_text.py` → `patch_ui.py`) com 0 avisos. Reextração direta confirmou `PRELOAD.pak` inalterado em tamanho (2.793.760 bytes), 545 itens e 2.057 legendas nativas, `logo/0000.txb` (110.704 bytes) e `title/msg.bin` em `title.pak`, e `staffroll_03.txb` (1.193.072 bytes) nos dois PAKs de créditos (`ev_scn_c07_credit.pak` e `ev_scn_staffroll.pak`).

### 2026-11-18 — Texturas, lote 4 desenhado (aberturas de capítulo e poema final)

- O catálogo é `ptbr/graficos/lote4-aberturas.json`, com 106 texturas. Ele sai da planilha revisada `Fate_Extra_CCC_Lote4_Aberturas.xlsx` via `python tools/lote4_planilha.py`, que usa a coluna "Sua revisão" quando preenchida. Para mudar um verso, edite a planilha e rode o script de novo.
- Como foi desenhado:
  - poemas em Garamond (`GARA.TTF`, chave `garamond`), com o preenchimento no tom claro (`percentil` 90), brilho e sem contorno, iguais em todas as linhas;
  - texturas com mais de uma linha viram uma parte por linha, com o corte na linha de menor tinta entre elas;
  - título traduzido em `quadrada_fina`; "CHAPTER" virou "CAPÍTULO".
- `ui_labels.py` ganhou a fonte `garamond_b` (GARABD) e o recurso de trocar `garamond_b` por `garamond` quando o texto não cabe. O negrito acabou não sendo usado, porque misturava pesos entre as linhas.
- A ISO de teste v5 está em `output/ccc-ptbr-teste-v5.iso`, com SHA-256 `82573979c10251b21bae79cd25ab71869b16ec93ec82dea7e7021a2c75d7d938`. Ela é a v4 mais o lote 4, gerada pela cadeia completa. A reextração conferiu as 83 cópias de TXB catalogadas em 67 PAKs, e o PRELOAD manteve o tamanho de todas as entradas.
- Falta o teste no PPSSPP das aberturas: elas aparecem no início de cada capítulo e no final.

### 2026-11-18 — Texturas, lote 4: tradução proposta em planilha

- Transcrevi o texto das aberturas de capítulo (`interface/poem/cpt_00` a `cpt_08.txb`), do poema final (`poem_ex_tex.txb`) e dos títulos estilizados (`poem.txb`). A tradução proposta está em `Fate_Extra_CCC_Lote4_Aberturas.xlsx`, para revisão: são 134 linhas, 106 delas para traduzir.
- Ficam em inglês: o kanji e o subtítulo estilizado de cada título ("- Backyard of Eden -", "- Alter Ego / M -"…), "- BAD END. -" e os títulos de `poem.txb`, que são arte original. Traduz-se a linha que traduz o kanji ("Jardim da Subordinação", "Prisão do Cálculo"…).
- `cpt_07` e `cpt_08` ficam no mesmo PAK (`ev_scn_c07_000.pak`): são as duas rotas do capítulo 7. `poem_ex_tex.txb` está em 4 PAKs.
- Próximo passo: depois da revisão, criar `ptbr/graficos/lote4-aberturas.json` e renderizar. Os textos têm várias linhas por textura e a fonte é serifada, então o desenho precisará de suporte a mais de uma linha por parte.

### 2026-11-18 — Texturas, lotes 2 e 3, e texturas integradas ao `build.py`

- Novos catálogos:
  - `ptbr/graficos/lote2-menus.json`, com 218 texturas: menu principal, comandos de exploração, plaquinhas de nome, Meu Quarto, armário e cores, loja, equipamento, itens, status, Matriz de Dados (abas, parâmetros e 25 placas de habilidade com os nomes já traduzidos nas fichas), Secret Garden, galeria, fim do dia, passagem do tempo, caçadas, triggers, castigo e game over;
  - `ptbr/graficos/lote3-batalha.json`, com 133 texturas: avisos de batalha (">CRÍTICO<", ">VENENO<"…), estados, resultados, missão, seleção de andar, nome da camada nos 22 `loca_NN` e tela de VS.
  - O inventário foi feito por leitura de folhas de contato de todas as texturas candidatas.
- Seguem as regras de nome do projeto: as plaquinhas em ordem ocidental viraram ordem japonesa (Tohsaka Rin, Matou Sakura, Matou Shinji, Fujimura Taiga, Ryuudou Issei, Sessyoin Kiara). Servant/Master/Sentinel viraram Servo/Mestre/Sentinela.
- Ficam em inglês, como no texto do jogo ou por serem arte do original japonês:
  - comandos de batalha (ATTACK, GUARD, BREAK, SKILL, EXTRA, WAIT, CODE CAST, C·CAST, EX-SKILL, CHAIN), que o tutorial já cita em inglês;
  - Code Cast, Secret Garden, Sakurament, STATUS, SG, MP, EXP, TOTAL, CENTRAL, Launcher, Potnia Theron, Aurea Poculum e Trash & Crash;
  - subtítulos estilizados de cada andar ("Escape From New Moon.", "Gold Trash."…);
  - telas DEAD END/BAD END/NEVER END/Fin/TO BE CONTINUED, logo Channel e a tela de erro de instalação do patch inglês;
  - textos em placa ou em fonte de 8 px que não ficam legíveis: ESCAPE, POINT1–3;
  - itens que dependem de redesenho, como PLAYER'S LIFE em duas linhas e as letras soltas de GAME OVER, HUNTING e EXTRA TURN.
- Mudanças em `tools/ui_labels.py`:
  - suporta texturas sem tabela de blocos (`PlainTexture`, como as plaquinhas de nome);
  - estilo `placa` para texto vazado;
  - percentil de cor do preenchimento configurável;
  - troca automática para a fonte condensada quando o texto não cabe;
  - se a textura não tem blocos de reserva suficientes, tenta de novo com o texto mais estreito;
  - uma textura que falha fica em inglês com aviso, sem derrubar as outras;
  - a conferência final compara a cor visível, com blocos `-1` transparentes.
- **Limite importante:** o número de blocos guardados em cada textura é fixo. Na loja, BUY ocupa um único bloco de 32 px, por isso a loja usa COMPRA/VENDA.
- **As texturas agora entram pelo `build.py`** (`patched_textures`): viram arquivos de jogo comuns, e `rebuild_paks` os grava em todos os PAKs que os contêm. Isso inclui os comprimidos no CPK (beginning, mission, hunting, trigger…), que a gravação direta na ISO não aceita. `ui_labels.py BASE SAIDA` continua disponível só para PAKs sem compressão.
- A cadeia oficial para gerar a ISO passa a ser: `python tools/build.py` → `python tools/native_text.py ETAPA1.iso ETAPA2.iso` → `python tools/patch_ui.py ETAPA2.iso FINAL.iso`. Ela inclui todos os textos, as mensagens de instalação, itens e legendas nativos, aviso de abertura, menu Sistema e os lotes 1–3.
- A ISO de teste v4 está em `output/ccc-ptbr-teste-v4.iso`, com SHA-256 `05469b4c0e4f7c7cb687a276f48e5d23bb34c0168e31f084bcbd36f235247bc9`. Os passos intermediários ficaram em `output/ccc-ptbr-etapa1.iso` e `etapa2.iso`.
  - O CPK cresceu 7,9 MiB por causa dos PAKs que antes eram comprimidos e agora vão sem compressão, e a ISO foi reconstruída inteira.
  - A reextração conferiu as 70 cópias dos TXBs catalogados nos 55 PAKs que os contêm, byte a byte contra a renderização esperada, sem nenhum PAK ainda comprimido.
  - O PRELOAD manteve o tamanho de todas as entradas, e o `install.bin` traduzido tem os 656 bytes.
  - O `native_text.py` aplicou 545 campos de item e 2.057 segmentos de legenda, e o `patch_ui.py` verificou a ISO final.
- Falta o teste no PPSSPP.

### 2026-11-18 — Texturas, lote 1 (abertura e configuração)

- O catálogo `ptbr/graficos/lote1-abertura.json` tem 54 rótulos em 7 TXBs:
  - tela de título (`interface/title/0000.txb`): INICIAR/NOVO JOGO, CARREGAR/CONTINUAR, DADOS/INSTALAR, APERTE START, INFORMAÇÕES e APAGAR;
  - aviso de ficção e conselho de salvar (`interface/advice/0000.txb`);
  - dificuldade (`interface/modeselect/modeselect.txb`);
  - opções (`interface/option/option_00.txb`);
  - criação do protagonista (`interface/nameentry/0000.txb`);
  - ESCOLHA O SERVO (`interface/svtselect/svt_select.txb`);
  - as oito "Primeira… Última seleção" do prólogo (`interface/beginning/0000.txb`).
- Ficaram como no original:
  - nomes de classe e GILGAMESH;
  - as etiquetas de dificuldade SWEET/NORMAL/MANIAC, que o texto do jogo também mantém como nome (como "Maniac" na escolha do Servo);
  - ✕>OK, SELECT>AUTO, ひらがな/カタカナ/ABC e OK;
  - FEMALE/MALE dentro dos ícones ♀/♂: o rótulo fica sobre o círculo e o português não cabe sem redesenhar o ícone;
  - `interface/charsel/svt_select.txb`, com descrições em japonês e provavelmente resto do Extra; falta confirmar no PPSSPP se aparece.
- `tools/ui_labels.py` é a ferramenta genérica para rótulos em textura. Ela mede o texto inglês na arte: altura da maiúscula, linha de base, largura relativa à fonte escolhida e alinhamento. Também lê as cores: preenchimento com degradê por linha, contorno escuro e brilho colorido. O português é desenhado com a mesma métrica e as mesmas camadas e quantizado para a paleta da textura. Use `--preview PASTA` para gerar PNGs de antes/depois e `BASE.iso SAIDA.iso` para aplicar sobre uma ISO.
- `ChunkedTexture.relayout` (em `tools/ui_textures.py`) reconstrói a tabela de blocos da textura sem mudar o tamanho do arquivo. O resultado tem blocos transparentes como `-1`, blocos iguais compartilhados e o contador atualizado. A ferramenta só usa o relayout quando o texto novo não cabe no arranjo original de blocos.
- `beginning.pak` está **comprimido** no CPK. A gravação direta na ISO (`native_text.read_iso_paks`/`write_iso`) só aceita PAKs sem compressão, então as oito "seleções" estão prontas no catálogo, mas ainda não entram na ISO. Para aplicá-las, é preciso recomprimir o PAK ou fazer a troca pelo `build.py`. `read_iso_paks` aceita um conjunto `skipped` para registrar os comprimidos em vez de abortar.
- A ISO de teste v3 (a v2 mais o lote 1) está em `C:/Users/Thiago/Documents/Codex/2026-11-18/fate-extra-ccc-pt-br/outputs/ccc-ptbr-teste-v3.iso`, SHA-256 `b6f83f2f25cfc159a41dbeecf143eb0a573c6c3cfae16e182d003a26160ce12f`.
  - A reextração conferiu as 46 texturas trocadas byte a byte contra a renderização esperada.
  - As outras entradas dos PAKs ficaram idênticas, e `write_iso` confirmou que nada mudou fora deles.
  - A v3 **não** inclui as mensagens de instalação traduzidas, porque elas exigem a cadeia completa (`build.py` → `native_text.py` → `patch_ui.py` → `ui_labels.py`).
- Falta ver no PPSSPP o encaixe dos textos mais longos: VELOCIDADE DO TEXTO, CONTROLE DA CÂMERA e ESCOLHA O SERVO.

### 2026-11-18 — Mensagens de instalação de dados em PT-BR

- As cinco mensagens de `interface/cmn/install.bin` (sem erros, dados danificados, falha de leitura, Memory Stick ausente e instalação interrompida pelo modo de espera) foram traduzidas em `ptbr/menus/interface__cmn__install.po`. A decisão anterior de manter o inglês partia da ideia de que cada frase precisava caber no tamanho da frase inglesa. Na verdade, o limite é o arquivo inteiro: 656 bytes no `PRELOAD.pak`. O português ficou com 592 bytes, com todos os acentos (em UTF-8, cada acento ocupa 2 bytes), e o `build.py` completa o restante com NUL.
- `binfile.pad_to_size` agora preserva o registro final `[índice 0][tamanho 0]` quando sobram 8 bytes ou mais, como no arquivo original. Antes, a sobra era absorvida pela última entrada e a tabela ficava sem terminador. A reconstrução do `PRELOAD.pak` em memória manteve o tamanho de todas as entradas.
- `scripts_ccc.py` deixou de tratar essas frases como invariáveis e de recusar a tradução. Agora confere o tamanho do arquivo inteiro (`INSTALL_BIN_SIZE = 656`) na validação. O título da unidade perdeu o "manter EN", e o JSON de trabalho passou a ser `trabalho/12_menus_interface/008_menus_instalacao_de_dados_preload__interface__cmn__install.json`.
- `catalogo_ccc.py` ignora `ptbr/nativo/`, que é aplicado por `tools/native_text.py`. Sem isso, o catálogo, o `--build-work` e o painel quebravam com "Categoria desconhecida".
- A régua passou em 64.446 textos sem problemas, e o validador registrou 0 erros nas 292 unidades. Falta gerar a próxima ISO de teste (`build.py` → `native_text.py` → `patch_ui.py`). Essas mensagens só aparecem quando a instalação de dados falha, então dificilmente surgem numa jogatina normal no PPSSPP.

### 2026-11-18 — Inventário de texto em texturas após a ISO v2

- A auditoria visual comparou 47 arquivos TXB da extração com os correspondentes na ISO v2. Confirmou texto em inglês nas artes de título, opções, seleção de Servo, nome do jogador, menu principal, itens, equipamento, loja, status, Meu Quarto, Matriz de Dados, Labirinto, batalha, resultados e outros avisos. A presença no arquivo ainda não comprova que todo recurso seja exibido em jogo.
- O título e o aviso de ficção/recomendação de salvar ficam em title.pak. Os comandos de exploração e as plaquinhas de personagens ficam em interface/cmn/i_bpt.txb, i_con.txb e i_con_name.txb. Esses TXBs, interface/cmn/i_load.txb e as artes do menu principal/locomoção ficam em PRELOAD.pak, sujeitos ao tamanho fixo. Os rótulos de batalha e resultados ficam em dungeon_resident.pak.
- As aberturas de capítulo cpt_00 a cpt_08 em interface/poem incluem texto narrativo em inglês gravado nas imagens. Também há texto japonês nos tutoriais amostrados e texto em inglês e japonês nos créditos. A auditoria não reempacotou a ISO nem alterou imagens.

### 2026-11-18 — Aviso de abertura e menu Sistema/Arquivos

- O teste no PPSSPP mostrou o aviso de abertura, o cabeçalho e as duas colunas de opções do menu em inglês, mesmo com a ajuda do rodapé em PT-BR. O aviso fica em interface/logo/0000.txb, textura 4 de title.pak. Os rótulos ficam em interface/save/0000.txb e 0001.txb de savemenu.pak, incluindo a variante Arquivos.
- O catálogo editável está em ptbr/graficos/abertura-e-sistema.json. A arte mantém a disposição, as dimensões, a paleta e a tabela de blocos do jogo. Os glifos foram renderizados com Verdana, Segoe UI Semibold e Square721 no lugar dos glifos em inglês.
- Para reproduzir sobre a ISO de teste com itens e legendas, execute `python tools/patch_ui.py ISO_BASE.iso ISO_V2.iso`. As fontes específicas podem ser indicadas via `--font-dir`. A ferramenta valida a edição das texturas por SHA-256 e a imagem de saída mantém os tamanhos e os offsets das entradas no CPK.
- A v2 está em C:/Users/Thiago/Documents/Codex/2026-11-18/fate-extra-ccc-pt-br/outputs/ccc-ptbr-teste-v2.iso. Reextraídos e conferidos os pixels de 18 texturas em três TXBs. A comparação confirmou que o PRELOAD, o EBOOT e todos os bytes fora de title.pak e savemenu.pak correspondem à ISO de teste anterior. SHA-256 da v2 700930ba5d8ba4110a06946f80176dbc3cc8e2512e08f7934cb08fed30cae128.

### 2026-11-18 — Itens e legendas nativas em PT-BR

- Os catálogos editáveis em ptbr/nativo/itens.po e ptbr/nativo/legendas.po cobrem os 545 campos de item com texto (424 textos distintos) e os 2.057 segmentos com texto dos 1.365 eventos de legenda. Os outros 231 campos de item e 254 segmentos são brancos ou pausas. A contagem anterior de 626 campos de item incluía 81 campos ocupados por um único espaço.
- tools/native_text.py aplica os catálogos à ISO integrada em uma imagem de saída separada. Uso com caminhos de origem e destino: python tools/native_text.py BASE.iso TESTE.iso. Para validar sem gravar uma ISO, use python tools/native_text.py BASE.iso --check. A ferramenta exige o módulo inglês original da edição 08/12/2023 no PRELOAD da ISO de origem.
- Os textos couberam nos espaços já reservados do módulo ligado, com 14.472 de 16.928 bytes para itens e 80.396 de 92.172 bytes para legendas. Foi possível manter o código nativo, as coordenadas, todos os tempos e modos de exibição, as pausas e os tamanhos de cada entrada do PRELOAD, sem recompilar o patch nem modificar o EBOOT.
- A ISO de teste está em C:/Users/Thiago/Documents/Codex/2026-11-18/fate-extra-ccc-pt-br/outputs/ccc-ptbr-itens-legendas-teste.iso. O PRELOAD reextraído confirmou todos os textos dos dois catálogos. A comparação da imagem confirmou igualdade byte a byte fora dele, e só os dois arquivos de parâmetros de item e hax/patch.o mudaram dentro dele. O SHA-256 da ISO é 0452416e4946db958d144a7d81e6e7c202206b37f69717f0dfc3f13056a2f6ac.
- A régua global verificou 64.441 traduções sem estouros. As 25 sinalizações de gênero nas legendas nativas foram triadas pelo contexto. O boot e a apresentação das legendas e dos itens ainda precisam ser testados no PPSSPP.

### 2026-11-18 — Extração dos itens e das legendas do patch nativo

- Na ISO inglesa, hax/patch.o é a última entrada de PRELOAD.pak e contém o binário nativo já ligado. A base calculada segundo CccAsmPatcher é 0x08FE1D60 para esta edição, com 160.608 bytes de conteúdo. A inspeção resolveu os 776 marcadores de item de cmn/item_param_01.bin e cmn/item_param_04.bin. São 626 campos não vazios e 425 textos ingleses distintos, contando nomes e descrições. Essa identificação corrige a tentativa anterior registrada no histórico.
- A tabela nativa de legendas tem 1.365 eventos de áudio e 2.311 segmentos, incluindo pausas sem texto. Todos os identificadores foram associados aos caminhos ou aos códigos dos bancos de som do toolkit inglês. São 970 eventos cv/btl, 209 cv/fld, 182 de bancos de efeitos e quatro de outras categorias. Os registros do binário permitem extrair texto, duração em quadros, posição e modos de exibição.
- Próximo teste técnico é extrair e regravar um lote pequeno mantendo tamanhos, campos de controle e endereços de entrada. Caso os textos PT-BR não caibam no espaço disponível, o caminho de compilação é regenerar generated.cpp e remontar patch.o, marcadores dos itens e pontos de entrada do EBOOT em conjunto, conforme CccAsmPatcher e SubsTranslationProcessor.


### 2026-11-18 — Escola (Hub) concluída e ISO integrada

- Fechados os dez roteiros pendentes do Hub, 024–029, 031 e 035–037. Das 5.686 entradas em aberto, 1.115 vieram do 030, 2.460 foram integradas dos lotes W1–W6, 1.995 foram traduzidas nos lotes W7–W11 e 116 foram preenchidas por correspondência entre os mapas. O Hub soma 11 de 11 roteiros e 16.320 entradas cobertas.
- O manifesto e os .po conferem em 292 de 292 unidades e 67.797 de 67.797 entradas. O validador registrou zero erros e 1.062 avisos. A régua global passou em 61.839 textos, com zero ocorrências de corte ou excesso de linhas.
- A ISO integrada foi gerada sem avisos em C:/Users/Thiago/Documents/Codex/2026-11-18/fate-extra-ccc-pt-br/outputs/ccc-ptbr.iso, no volume com espaço disponível. As 16.320 entradas da Escola foram verificadas nos DATs extraídos da ISO. O CPK manteve seus 14.851 itens, com 200 PAKs alteradas e PRELOAD.pak e EBOOT.BIN com os tamanhos originais.
- A revisão humana e o teste no PPSSPP continuam pendentes. Os itens e as legendas de batalha no código nativo seguem fora do catálogo de 292 unidades.


### 2026-11-18 — Escola (Hub), conclusão do `030` e integração

- Concluídas as etapas 2 a 10, IDs 208–5235 da Sala do Grêmio. Foram preenchidas 4.384 entradas que estavam pendentes. A cena tem **5.235 de 5.235 entradas cobertas**, incluindo 28 nomes e controles que usam o original. Régua e seletores de gênero foram conferidos com os validadores. O glossário foi aplicado aos SGs, à nomenclatura do Moon Cell e aos tratamentos de Hakuno.
- Na etapa 11, o `024` recebeu 1.217 falas compartilhadas e está em **1.678/2.180**. O `035` recebeu 1.698 e está em **2.046/2.082**. Foram preservados os campos de tradução já preenchidos nesses espelhos. As 538 pendências restantes dos dois roteiros pertencem a trechos próprios.
- `medida.py` passou nos três roteiros com zero problemas. `scripts_ccc.py --validate` verificou 292 scripts com zero erros. Os avisos destes três roteiros são da triagem de gênero, que também sinaliza falas sobre outros personagens e expressões como “dar certo”.
- A ISO parcial está em `output/030-completo/ccc-ptbr.iso`. Conferidas pelo DAT da ISO as 9.497 entradas dos três roteiros. A comparação dos 14.851 itens do CPK identificou as três PAKs de roteiro e a `PRELOAD.pak` de fonte, esta com o tamanho original. Falta teste em jogo no PPSSPP.


### 2026-11-18 — Capítulos 4, 5, 6 e 7 / Finais concluídos (`beta-ia` — `281/292`)

- **`04_capitulo_4` (9/9), `05_capitulo_5` (6/6), `06_capitulo_6` (11/11) e `07_capitulo_7_final` (17/17, `beta-ia`):** traduzidos integralmente os `42` arquivos pendentes (mais `115.po` já completo no Cap. 5), cobrindo Jinako/Karna (`#NICK`, `Launcher` mantido, `#ROFS0001#RUBSÓ Sol, Curva-te à Morte#RUBEVasavi Shakti#REND`), Elizabeth/Shinji (`#[porquinho][esquilinho]#`, `#RUBS   Demonesa de Sangue Fresco#RUBEBáthory Erzsébet#REND`), Meltlilith/Alice (`Meltlilith` preservado, `#RUBS Biwa de Cinco Cordas de Benzaiten#RUBESaraswati Meltout#REND`, `#[irmãozão][irmãzona]#`), Núcleo do Moon Cell / BB (`Senpai`, `#RUBSCursed Cutting Crater#RUBEC. C. C.#REND`), Rota CCC (`Sessyoin Kiara`, `Hans Christian Andersen`, `Bodhisattva Demoníaca`), todos os epílogos dos Servos (`Nero`, `EMIYA`, `Tamamo`, `Gilgamesh`) e chefe secreto (`136`, Enkidu).
- **Auditoria & Validação:** varredura direta nas `51.477` entradas dos 14 grupos concluídos fechou com **`pending=0 | issues=0`** (zero caracteres inválidos/proibidos, zero `Praetor`, zero `Spiriton`, zero `Meltryllis`, zero inversões de nomes japoneses). `tools/medida.py` passou globalmente (`51.750` verificados | **`0` problemas**) e `tools/scripts_ccc.py --validate` fechou em **`292` scripts | `0` erro(s) | `876` aviso(s)**.
- **Planilhas & Pendências:** atualizados `Fate_Extra_CCC_Progresso_Geral.xlsx`, CSV e Google Sheet oficial para **`281 / 292` cenas (`96,2%`)** | **`57.708 / 67.797` linhas**. Não foi executado `--sync-repeats` nem geração da ISO para não interferir com `030.po` em andamento no outro agente; resta exclusivamente **`08_escola_hub` (`0/11`)**.

### 2026-11-18 — Capítulos 1, 2 e 3 + Meu Quarto e BB (`beta-ia`)

- **`01_capitulo_1` (7/7), `02_capitulo_2` (7/7) e `03_capitulo_3` (7/7, `beta-ia`):** traduzidos integralmente os arquivos de história e chefes dos três capítulos (`092, 079, 150, 090, 062, 051, 091`, `093, 094, 095, 114, 052, 063, 151` e `096, 097, 098, 064, 053, 108, 152`), seguindo `GLOSSARIO_CCC_OPERACIONAL.json` (incluindo `Maestro`, `#NICK` para Passionlip, SGs e Fantasmas Nobres oficiais). Em `064.po` foi corrigido também o erro de digitação `Spiriton` → `Spiritron`.
- **`09_meu_quarto_bb` (5/5, `beta-ia`):** concluídos `050`, `058`, `071` e seus espelhos `032` e `033` (totalizando 14.181 linhas no bloco).
- **Validação & Planilha:** `tools/medida.py` passou em todo o projeto (**41.363** verificados, **0 problemas**), `tools/scripts_ccc.py --validate` fechou em **292 scripts | 0 erro(s) | 657 aviso(s)**, e a Google Sheet oficial subiu para **`239 / 292` cenas (`81,8%`)**. Não foi executado `--sync-repeats` após o Cap. 3 nem build de ISO para não conflitar com o agente paralelo trabalhando em `030.po`.

### 2026-11-18 — Escola (Hub), `030`, etapa 1

- Traduzidos os 152 campos pendentes dos IDs 50–207 da Sala do Grêmio. As seis entradas que já tinham PT-BR foram mantidas após leitura em contexto. O painel e o `.po` estão sincronizados, com 851 de 5.235 entradas cobertas no `030`.
- O trocadilho `Tenterest` ficou como “juros de dez em dez”, em referência ao prazo na fala de Leo. `Commissary` segue o uso de “Cantina” em `071`.
- Zero problemas de largura no `030` e zero erros no validador do projeto. Os três alertas de gênero no intervalo são de contexto (Leo, Shinji e o presente conhecido). Build parcial sem avisos em `output/030-etapa-1/ccc-ptbr.iso`, com as 158 entradas do lote conferidas no DAT extraído da ISO. Falta teste no PPSSPP.
- Próximo trecho confirmado no ID 208 (`msgctxt 826024`). O reaproveitamento de falas em `024` e `035` fica para a integração.

### 2026-11-18 — Secret Gardens (`62/62`, `beta-ia`), correção Windows em `atomic_write`

- **`10_sg_jardins_secretos` (62/62 arquivos, `beta-ia`):** todos os 61 `.po` pendentes traduzidos (`medida.py "sg/*"`: 181 textos validados com 0 problemas `<= 415px`; `fixedbin.build`: 62/62 OK; `interface__sg__sg_ner.po[16]` usando `Maestro`; títulos `sg_titulos` idênticos ao glossário).
- **`tools/scripts_ccc.py` (`atomic_write` e `is_line_done`):** adicionadas até 5 tentativas + fallback em `atomic_write` para contornar bloqueio temporário de `os.replace` no Windows (`PermissionError`), além de detecção automática de medidas/CJK em `sg/`. Planilha [FATE EXTRA CCC PROGRESSO](https://docs.google.com/spreadsheets/d/19bG6X5DlVW9i6jmshKZgKnm87rUZGE3ByTqLRH8O5rY/edit) atualizada para **`213 / 292 (72,9%)`** (incluindo `historia/092` já fechada no Cap. 1).

### 2026-11-18 — Padronização `Maestro`, conclusão de Info Matrix, Menus e Sistema (`beta-ia`) + Nova Planilha

1. **`Praetor` → `Maestro` (padrão Fate Café / Fate Extra Record):**
   - Atualizados `standards/GLOSSARIO_CCC_OPERACIONAL.json`, `standards/PROMPT_TRADUCAO_CCC.md`, `tools/glossario.py` e **319** linhas `msgstr` em **107** arquivos `.po` de `ptbr/` (`#[meu][minha]# Maestro`, `#RUBS#[Mestre][Mestra]##RUBEMaestro#REND`).
   - Confirmado em `GLOSSARIO_CCC_OPERACIONAL.json` (`sg_titulos`): `Breast Valley` = **`Vale dos Seios`** (`infomatrix_d_02.po` alinhado); `High Servant` = **`Servo Composto`**; `dust data` = **`dados residuais`**.
2. **`11_lore_matriz` (16/16), `12_menus_interface` (26/26) e `13_sistema_comum` (13/13) — 100% traduzidos e validados (`beta-ia`):**
   - `infomatrix_d_07.po[13]` (`Blank Page` → `Página em Branco`) concluído; `infomatrix_t_01..08.po` integralmente reescritos a partir do inglês original sem resumos e quebrados em `<= 423px` (60 caracteres/linha).
   - `menus/interface__mainmenu__help.po` (`interface/mainmenu/help.bin` dentro de `PRELOAD.pak`) traduzido integralmente com os 36 `sg_titulos` exatos e mantendo **exatos `1.232` bytes** (`diff=0` no `PRELOAD.pak`).
   - Todos os demais menus (`status`, `nameentry`, `gallery` com `Punição!` em Title Case sem maiúscula acentuada ausente, `dungeonselect`, `infomatrixex`, `myroom`, `osioki` `<= 350px` 1 linha, `dungeon` `<= 396px` máx. 2 linhas sem `'º'` na fonte) e `sistema/eboot` (`[66] 'My Room'` corrigido de `'Meu Quarto'` 10B para `'Quarto'` 6B <= 9B; 55 entradas aplicadas, 0 puladas), além de `historia/141, 900-905, 995, 996, 999`.
3. **Melhorias no ferramental e planilhas:**
   - `tools/medida.py`: regex `#. ` opcional para cobrir arquivos `.bin` sem comentário de tipo e mapeamento automático de `infomatrix_t_*` (`423px`), `sg/*_text*` (`415px`), `interface__dungeon__msg` (`inDungeon` = `396px`) e `interface__osioki__msg` (`choice` = `350px`). `medida.py`: **0 problemas**; `scripts_ccc.py --validate`: **0 erros**.
   - `tools/scripts_ccc.py`: suporte em `is_line_done` a placeholders/teclado `nameentry`, dummies de `osioki` / `sg` e slots CJK/realocados via MIPS em `sistema/eboot`.
   - `tools/gerar_planilha_progresso.py`: adicionado status **`beta-ia`** (`#D9D2E9`) na validação/fórmulas; atualizada a planilha oficial [FATE EXTRA CCC PROGRESSO](https://docs.google.com/spreadsheets/d/19bG6X5DlVW9i6jmshKZgKnm87rUZGE3ByTqLRH8O5rY/edit) com `151 / 292` cenas concluídas (`51,7%` — Prólogo em `Revisado` e Info Matrix / Menus / Sistema / Mapas Base / `sg_0000` em `beta-ia`).

### 2026-11-17 — Padronização de tratamentos/apelidos/termos CCC, glossário comum expandido e Prólogo (`001` e `002`)

Definidas em `standards/GLOSSARIO_CCC_OPERACIONAL.json` e `standards/PROMPT_TRADUCAO_CCC.md` todas as convenções recorrentes antes da tradução em sequência:

- **Tratamentos ao protagonista (`tratamentos_protagonista`):**
  - Tamamo no Mae (`Darling`): **`#[Querido][Querida]#`** (e `#RUBS#[Mestre][Mestra]##RUBE#[Querido][Querida]##REND` no rubi).
  - Elizabeth Báthory (`#[piggy][squirrely]#`): **`#[porquinho][esquilinho]#`** (`#[Porquinho][Esquilinho]#`, `#[porco][esquilo]#`, `#[Mestre porquinho][Mestra esquilinho]#`); `puppy` para Servos = **`cachorrinho`**.
  - Nero: `Praetor` / `#[meu][minha]# Praetor`; EMIYA: `#[Mestre][Mestra]#`; Gilgamesh: `#[mestiço][mestiça]#` / `verme`; BB: `Senpai`; Jinako/Passionlip/Meltlilith: `#NICK`; Sakura/Rani/Leo/Kotomine: `#[Sr.][Srta.]# #FAMILY`.
- **Apelidos de Servos e códigos:**
  - Mantidos em inglês: **`Goldy`**, **`Gorgeous`**, **`AUO`**, **`Launcher`**. Traduzidos: `Green Archer` = **`Archer Verde`**, `Green Tea` / `Greenchee` = **`Chá Verde`** / **`Chazinho Verde`**, `Red Lancer` = **`Lancer Vermelha`**.
  - Documentados `#NICK` e `#SVT[Saber][Archer][Caster][Gilgamesh]#`.
- **Termos do mundo virtual:** **`Wizard`** / **`Wizards`** e **`checkpoint`** mantidos em inglês; `Noise` = **`Ruído`**; **`o Moon Cell`** sempre no masculino (`Núcleo do Moon Cell`); `Sakura Labyrinth` = **`Labirinto de Sakura`**; `Old School Building` = **`Prédio Antigo da Escola`**; `Relief` = **`Relevo`**; mais 36 títulos dos Secret Gardens (`sg_titulos`) e NPs/Skills da Info Matrix (`infomatrix_np_skills`).
- **Correção em `tools/catalogo_ccc.py`:** rótulo de `sg_ksk` corrigido para **`BB (Black Sakura)`**.
- **`tools/glossario.py` expandido (186 termos):** adicionados `'Servant': 'Servo'`, `'King of Heroes': 'Rei dos Heróis'`, `'Green Archer': 'Archer Verde'` e ~60 prompts/falas recorrentes de exploração do Labirinto, checkpoints e retorno ao Meu Quarto — aplicando **5.137 textos em 189 arquivos** sem estouros (`medida.py`: 0 problemas; `PRELOAD.pak` / `field_new/main/0000.dat` preservado em exatos 14.528 bytes).
- **Tradução em ordem (Etapa 1 do Prólogo):** `ptbr/historia/002.po` integralmente traduzido nas suas falas de cena (59 entradas + revisado `historia/001.po`), alcançando **12.941 / 67.797 (~19,1%)** linhas traduzidas no projeto. Build parcial `build.py --only historia/001,historia/002` gerado com 0 avisos (`output/ccc-ptbr.iso`, 1,34 GiB).

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
   arquivo. *(Revisto em 2026-11-18: o arquivo foi traduzido; ver o histórico.)*

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
