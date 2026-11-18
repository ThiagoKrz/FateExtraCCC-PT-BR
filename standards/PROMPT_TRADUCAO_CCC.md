# Padrão de Tradução — Fate/Extra CCC PT-BR

Prompt canônico para traduzir os arquivos `.po` deste repositório, com foco em
integridade técnica, naturalidade literária e fidelidade terminológica ao
universo Type-Moon.

## Leitura obrigatória antes de agir

Nesta ordem:

1. `standards/GLOSSARIO_CCC_OPERACIONAL.json`
2. `standards/GLOSSARIO_TYPEMOON_OPERACIONAL.json` *(cópia sincronizada do Fate Café)*
3. `standards/README.md`
4. `standards/PROMPT_TRADUCAO_CCC.md` *(este arquivo)*
5. `standards/DIARIO_DE_MUDANCAS.md`

Padrão herdado e consolidado entre os projetos ativos:
- Fate Café React (`C:/Users/Thiago/Desktop/fate-cafe-react/standards/type-moon/`)
- FSN Remastered PT-BR (`PROMPT_REVISAO_FSN_REMASTERED_SCRIPTS.md`)
- FHA Remastered PT-BR (`PROMPT_AGENTE_FHA_UNIFICADO.md`)
- Mahoyo VN & Mangá (`glossario.json`, `PADRAO_NOMES.md`, `REGRAS_TRADUCAO_MANGA.md`)
- Tsukihime Remake PT-BR (`GLOSSARIO_TYPEMOON_OPERACIONAL.json`, `HANDOFF.md`)

Se houver conflito entre este prompt e o glossário, **o glossário vence**.
Para termos gerais da Type-Moon, `GLOSSARIO_TYPEMOON_OPERACIONAL.json` vence;
para termos e restrições exclusivas do CCC (PSP), `GLOSSARIO_CCC_OPERACIONAL.json` vence.

## Objetivo

Traduzir para PT-BR natural e literário preservando:

- a estrutura do arquivo `.po`;
- todos os códigos de controle do jogo;
- os limites de bytes de cada campo e a largura em pixels da caixa;
- a personalidade, o registro e a voz individual de cada personagem.

## Escopo

Traduzir **apenas** o conteúdo de `msgstr`.

Nunca alterar:

- `msgctxt` — é o identificador interno, mexer nele quebra a injeção;
- `msgid` — é o texto-fonte em inglês;
- os comentários `#.` e `#:`;
- o cabeçalho do arquivo.

## Prioridades absolutas

1. O glossário é PRIORIDADE MÁXIMA.
2. Acentuação correta e encoding limpo, logo abaixo do glossário.
3. Códigos de controle são sagrados.
4. Classes de Servo (`Saber`, `Archer`, `Lancer`, `Rider`, `Caster`, `Assassin`, `Berserker`, `Savior`, `Gunner`, `Alter Ego`, `Moon Cancer`, `Ruler`, `Avenger`, `Foreigner`, `Pretender`, `Shielder`, `Beast`, etc.) e nomes próprios **nunca** são traduzidos.
5. Limites de bytes e de largura de linha (`medida.py`) nunca podem ser estourados.
6. PT-BR natural e com voz fiel é obrigatório — frase "correta, mas com cara de tradução" é erro.
7. A tradução deve ser feita por etapas, informando quantas faltam e pedindo confirmação ao encerrar.

## Convenções de Localização Type-Moon (Padrão Fate Café / FSN / FHA / Mahoyo)

### Termos obrigatórios

| Inglês / JP | PT-BR obrigatório | Observação |
|---|---|---|
| `Servant` / `Servants` | **Servo** / **Servos** | Nunca deixar `Servant` em inglês no texto traduzido. |
| `Master` / `Masters` | **Mestre** / **Mestres** | Feminino `Mestra` quando apropriado. Nunca deixar `Master` em inglês. |
| `Noble Phantasm` / `Noble Phantasms` | **Fantasma Nobre** / **Fantasmas Nobres** | Proibido `Pergaminho Nobre`. |
| `Mystic Code` / `Mystic Codes` | **Artefato Místico** / **Artefatos Místicos** | `Supreme Mystic Code` = `Artefato Místico Supremo`. |
| `Command Seal` / `Command Spell` | **Selo de Comando** / **Selos de Comando** | Proibido `Selo de Mando`. |
| `Holy Grail` / `Holy Grail War` | **Santo Graal** / **Guerra do Santo Graal** | `Moon Holy Grail War` = `Guerra do Santo Graal Lunar`. |
| `True Name` | **Nome Verdadeiro** | |
| `Heroic Spirit` / `Divine Spirit` | **Espírito Heroico** / **Espírito Divino** | |
| `Spirit Origin` / `Saint Graph` | **Origem Espiritual** | `Spirit Core` = `Núcleo Espiritual`. |
| `Authority` | **Autoridade** | |
| `Magecraft` (魔術) | **magia** (minúscula no meio da frase) | Proibido `taumaturgia` ou `feitiçaria`. |
| `True Magic` / `Magic` (魔法) | **Magia Verdadeira** (sempre maiúscula) | Nunca minúscula. |
| `Magical Energy` (魔力) | **energia mágica** (minúscula no meio da frase) | |
| `Magician` (魔法使い) | **Feiticeiro** / **Feiticeira** (maiúscula) | Usuário de Magia Verdadeira. Nunca traduzir como `Mago`. |
| `Magus` / `Mage` (魔術師) | **mago** / **maga** (minúscula no meio da frase) | Praticante comum de magia. |
| `Mystery` (神秘) | **Mistério** (maiúscula quando conceito) | |
| `Bounded Field` | **Campo Limitado** | |
| `Reality Marble` | **Projeção de Realidade** | Proibido `Marble Fantasma`. |
| `Marble Phantasm` | **Projeção de Fantasia** | |
| `Counter Force` | **Força de Contenção** | Proibido `Força Contrária`. |
| `Magic Circuit` / `Magic Crest` | **Circuito Mágico** / **Brasão Mágico** | |
| `Mage's Association` / `Clock Tower` / `Atlas Institute` | **Associação dos Magos** / **Torre do Relógio** / **Instituto Atlas** | |
| `Moon Cell` / `Spiritron` / `Code Cast` | **Moon Cell** / **Spiritron** / **Code Cast** | Mantidos (`Pseudo-Spiritron` = `Pseudo-Spiritron`). |
| `Sentinel` / `Sentinels` | **Sentinela** / **Sentinelas** | Sempre no feminino (`a Sentinela`). |
| `Near Side` / `Far Side` | **Near Side** / **Far Side** | Em descrições por extenso, `Lado Próximo da Lua` / `Lado Distante da Lua`. |
| `Secret Garden` / `SG` / `Info Matrix` | **Secret Garden** / **SG** / **Info Matrix** | Mantidos como nomes de recurso. |
| `Praetor` / `SE.RA.PH` / `SERIAL PHANTASM` | **Praetor** / **SE.RA.PH** / **SERIAL PHANTASM** | Mantidos. |

### Nomes japoneses completos (ordem japonesa, sem mácrons)

Todo nome completo japonês segue a ordem japonesa (**Sobrenome Nome**), sempre **sem mácrons** (`Touko`, `Ryuudou`). Nomes ocidentais ou estrangeiros mantêm a ordem própria (`Leonardo Bistario Harwey`, `Julius B. Harwey`, `Dan Blackmore`, `Twice H. Pieceman`, `Rani VIII`, `Alice`, `Nero Claudius`, `Elizabeth Báthory`, `Hans Christian Andersen`).

Exemplos obrigatórios no CCC:
- `Hakuno Kishinami` → **`Kishinami Hakuno`** (nos scripts, `#FAMILY #GIVEN`)
- `Rin Tohsaka` → **`Tohsaka Rin`**
- `Sakura Matou` → **`Matou Sakura`**
- `Shinji Matou` → **`Matou Shinji`**
- `Issei Ryuudou` → **`Ryuudou Issei`**
- `Taiga Fujimura` → **`Fujimura Taiga`**
- `Aozaki Touko` → **`Aozaki Touko`** (já na ordem certa; nunca `Tōko`)
- `Kirei Kotomine` → **`Kotomine Kirei`** (`Father Kotomine` = `Padre Kotomine`)
- `Kiara Sessyoin` → **`Sessyoin Kiara`**
- `Jinako Carigiri` → **`Carigiri Jinako`**
- `Monji Gatou` → **`Monji Gatou`**

*Nota CCC vs FGO:* No patch EN e nos arquivos/texturas do CCC usa-se **`Meltlilith`** (no FGO NA / Fate Café usa-se `Meltryllis`). Mantenha **`Meltlilith`** no CCC para consistência com os gráficos, interface e dublagem exibidos no PSP.

### Honoríficos e relações escolares

- Mantenha sempre `-san`, `-kun`, `-chan`, `-sensei`, `-senpai`, `Senpai`, `Kouhai`/`kouhai`, `Onii-chan`, `Fuji-nee`.
- `先生` = **`-sensei`** (`Fujimura-sensei`), nunca `"Professor(a) X"` onde houver `-sensei`.
- Não force equivalentes artificiais para `Senpai` ou `Kouhai` (`BB` chama Hakuno de `Senpai`).
- Andares: tradução literal do número (`1F` = `primeiro andar` em diálogo corrido; nos rótulos curtos de mapa, `Andar 1` porque o glifo `º` não existe na fonte).

### Onomatopeias e reações abrasileiradas

- `"Tch"` → **`"Tsc"`**
- `"Eh?!"` → **`"Hã?!"`** / **`"O quê?!"`**
- Suspiro (`"Sigh"`) → **`"Ah..."`** / **`"Ai, ai..."`**
- Resmungo (`"Hmph"`, `"Grumble"`) → **`"Hunf"`**
- Mastigação (`"Munch, munch"`) → **`"Nham, nham"`**
- Proibido deixar SFX em inglês (`Hmph`, `Sigh`, `Gasp`, `Grab`, `Fwump`).

### Adaptação com freio, Lista Negra e Antitradutês

- **Adaptação com freio:** PT-BR natural, fluente e literário. Na narração, mantenha prosa mais formal e limpa; nas falas, respeite a escala de voz (1 a 4), sem gíria escrachada nem regionalismo estadual (`"oxe"`, `"mermão"`, `"uai"`, `"tu"` misturado com `"você"`). Prefira sempre `"você"`.
- **Lista Negra (erros proibidos no texto final):**
  - `Servant`, `Master`, `Noble Phantasm`, `Mystic Code` mantidos em inglês no texto traduzido;
  - `Salvador` para a classe `Savior`;
  - `Pergaminho Nobre`, `Selo de Mando`, `Projétil Mágico`, `Marble Fantasma`, `Força Contrária`, `Ancestral Verdadeiro`, `taumaturgia`, `feitiçaria`;
  - `Mago` traduzindo `Magician` (use `Feiticeiro`/`Feiticeira`);
  - nome completo japonês invertido em ordem ocidental;
  - `Hey.` / `Roger que` / mojibake / `?` no lugar de acento.
- **Idiomatismos e antitradutês obrigatórios (padrão FHA):**
  - `"I see"` (concordando) → `"Entendi"` / `"Compreendo"` (nunca `"Eu vejo"`).
  - `"It can't be helped"` → `"Não tem jeito"` / `"Fazer o quê"`.
  - `"As expected"` → `"Era de se esperar"` / `"Só podia ser"`.
  - `"What a pain"` → `"Que saco"` / `"Que trabalheira"`.
  - `"That's right"` → `"Isso mesmo"` / `"Exatamente"` (nunca `"Isso é certo"`).
  - `"Not bad"` → `"Nada mal"` (nunca `"Não ruim"`).
  - Corte sujeito explícito redundante (`"Ela disse que ela estava bem"` → `"Disse que estava bem"`), evite passiva inglesa desnecessária e conectivos mecânicos repetidos (`"Bem,"` / `"Então,"` no início de toda frase).

## Regra inegociável de encoding

- Proibido deixar `?` no lugar de acento ou caractere válido.
- Proibido escrever sem acento por conveniência (`nao`, `voce`, `coracao`, `efigie`, `harens`).
- Antes de encerrar uma etapa, revisar explicitamente se palavras como `não`, `você`, `coração`, `história`, `próprio`, `opções`, `início`, `efígie`, `haréns` mantiveram acento.

Letras disponíveis na fonte do jogo:

```
á é í ó ú â ê ô ã õ ç à   Á É Í Ó Ú À Ç
```

Não disponíveis: `Â Ã Ê Ô Õ` — são rebaixadas automaticamente para `A E O`.
Por isso: **escreva em Caixa Alta Apenas na Inicial** (`Opções`, nunca `OPÇÕES`).

## Códigos de controle

Copiar exatamente, na mesma posição, **incluindo os espaços internos**.

| Código | O que é |
|---|---|
| `#Cnnnnnnnnn` … `#CDEF` | abre cor / volta ao padrão |
| `#RUBS<base>#RUBE<leitura>#REND` | texto rubi: base grande, leitura pequena em cima |
| `#ROFSnnnn` | desloca o rubi; vem antes do `#RUBS` |
| `#FAMILY` / `#GIVEN` | sobrenome / nome do jogador |
| `#SVT` | nome do Servo do jogador |
| `#TITM0001` | nome do item corrente |
| `#TVALnn` | valor numérico do jogo |
| `#[a][b]#` | variante por gênero: 1ª masculino, 2ª feminino |
| `\n` | quebra de linha literal |

Regras:

- O `#[a][b]#` precisa das **duas** opções traduzidas e deve concordar com a
  frase em português. Exemplo: `Será um prazer recebê-#[lo][la]#`.
- No rubi, traduza base e leitura. Se a leitura for um nome próprio, mantenha.
- Nunca traduza o conteúdo entre `#C...` e o número da cor.

## Diagramação e largura de linha

**O jogo não quebra linha sozinho. O que passar da largura da caixa é cortado na
tela e o jogador simplesmente não lê aquele trecho.** A quebra é
responsabilidade da tradução.

Limites reais, em pixels, do `CccWidthLimit` oficial. Cada caractere comum
(inclusive os acentuados) mede **7px**:

| Onde | Limite | Em caracteres |
|---|---|---|
| Diálogo, linhas normais | 338px | **48** |
| Diálogo, última linha | 319px | **45** |
| Escolha (`choice`) | 350px | 50, em 1 linha só |
| In-dungeon | 396px | 56, em até 2 linhas |
| Info Matrix | 423px | 60 |
| Secret Garden | 415px | 59 |

A última linha é mais estreita por causa da setinha de avançar.

Caracteres de largura cheia medem 15px, não 7: `…` `～` `―` `—` `☆` `♪` `□` `△`
`○` `×` `◆` `→` `「` `」` `※`. Ou seja, `……` sozinho já custa 30px.

Nomes variáveis são medidos no **pior caso**, como no toolkit oficial:
`#FAMILY` e `#GIVEN` contam 11 caracteres cada, `#SVT` conta 9. Um `#[a][b]#`
conta pela variante **mais longa**.

Regras:

- Máximo de **3 linhas** por caixa de diálogo.
- Mantenha a mesma quantidade de `\n` do original quando couber; se o português
  ficar mais longo, redistribua as quebras em vez de criar uma quarta linha.
- Não deixe linha órfã de uma ou duas palavras.

**Verificação obrigatória** antes de fechar qualquer etapa:

```bash
python tools/medida.py              # varre tudo
python tools/medida.py historia/007 # um arquivo
```

O `build.py` também avisa a cada build. Aviso de largura = etapa inválida até
ser corrigida.

## Gênero do protagonista

O jogador escolhe se o protagonista é homem ou mulher. **Em inglês isso não
aparece; em português, todo adjetivo, particípio, pronome ou tratamento que se refere a ele muda.**

Sempre que o texto qualificar o protagonista, use o seletor:

```
#[masculino][feminino]#
```

Primeira opção = masculino, segunda = feminino. Exemplos reais do projeto:

```
Você tem essa cara de #[bobo][boba]#, #C236196003#GIVEN#CDEF,
Você é bem #[direto][direta]#, #C236196003#GIVEN#CDEF.
Será um prazer recebê-#[lo][la]#,
de "você está #[estranho][estranha]# hoje"?
Já deveria estar acostumad#[o][a]# com o trajeto,
```

Dá para aplicar só na terminação quando isso deixa a frase mais limpa:
`es#RUBS        oculto#RUBE#RENDtranh#[o][a]#`.

Vale para adjetivos, particípios (`#[cansado][cansada]#`), pronomes
(`#[lo][la]#`, `#[ele][ela]#`) e tratamentos (`#[Sr.][Srta.]#`, `#[meu Mestre][minha Mestra]#`).

**Verificação:**

```bash
python tools/genero.py              # varre tudo
python tools/genero.py historia/007 # um arquivo
```

Ele levanta suspeitas, não decide: a mesma palavra pode estar falando de outro
personagem (`novo jogo`, `conhecido como`). Revise cada uma e aplique o seletor
só onde o alvo é o protagonista. Ao encontrar um adjetivo novo que se repita,
acrescente-o à lista `GENDERED` em `tools/genero.py`.

## Limites de bytes

Onde o `.po` traz `#. max N bytes`, o limite é real e vale para o texto já
codificado. Cada acento custa **1 byte** (é um byte de controle), igual a uma
letra comum — então basta contar caracteres.

Se não couber: reescreva mais curto. **Nunca truncar no meio de uma palavra.**
Se for impossível encurtar sem perder sentido, deixe `msgstr` vazio (fica em
inglês) e registre o caso.

`ptbr/historia/` não tem limite de tamanho — **exceto `ptbr/historia/main.po`**,
que corresponde a `field_new/main/0000.dat` dentro do `PRELOAD.pak` e não pode
crescer nem 1 byte.

## Perfis de Voz dos Personagens (Calibragem 1 a 4 e Teste Cego)

Escala de registro: **1** (formal/elevado) a **4** (coloquial/gíria de internet, restrito a Taiga e Jinako). No **Teste Cego**, ao tapar o nome do falante, deve ser possível reconhecer quem fala pelo vocabulário e ritmo.

- **Kishinami Hakuno (Protagonista, 1ª pessoa — nível 2):** Narrador(a) sóbrio(a), observador(a), seco(a) e direto(a), com humor interno sutil. Português correto e natural (sem gíria na narração). Todo adjetivo/particípio/pronome referente a ele(a) exige `#[masc][fem]#`.
- **Nero Claudius (Saber — nível 1):** Grandiloquente, imperial, teatral, apaixonada e narcisista de bom coração. Chama Hakuno de `Praetor` ou `#[meu Mestre][minha Mestra]#`. Zero gíria ou contração coloquial (`pra`/`tá`).
- **Tamamo no Mae (Caster — nível 3):** Afetada, melosa, devotada como "esposa dedicada" (`Goshujin-sama` / `meu Mestre`), mas afiada e calculista quando séria.
- **EMIYA / Sem Nome (Archer — nível 2):** Seco, maduro, sardônico, contido e pragmático; ironia cortante com cuidado oculto.
- **Gilgamesh (nível 1):** Régio, absoluto, arrogante e arcaico; todos são mestiços/vermes; vocabulário elevado, jamais coloquial.
- **BB (nível 2–3):** Kouhai diabólica; alterna entre doçura artificial de apresentadora (`BB Channel`, chama Hakuno de `Senpai`) e sadismo frio e ameaçador.
- **Meltlilith (Alter Ego do prazer — nível 1–2):** Altiva, sádica, orgulhosa, elegante como bailarina; despreza os outros, mas tem forte senso de estética e dignidade.
- **Passionlip (Alter Ego do amor e do ódio — nível 2):** Tímida, insegura, carente e defensiva, com explosões de frustração pesada.
- **Sessyoin Kiara (nível 1):** Serena, polida, religiosa e profundamente perturbadora; fala mansa e formal escondendo devassidão absoluta.
- **Tohsaka Rin (nível 2–3):** Afiada, confiante, pragmática, tsundere clássica; direta e impaciente.
- **Rani VIII (nível 1):** Homúnculo do Instituto Atlas; fala analítica, formal, calma e sem contrações.
- **Matou Sakura (nível 1–2):** Gentil, contida, prestativa na enfermaria, com melancolia silenciosa.
- **Matou Shinji (nível 3):** Pedante, arrogante, covarde quando acuado, mas com momentos de camaradagem juvenil.
- **Ryuudou Issei (nível 1):** Presidente do grêmio; extremamente formal, sério e metódico. Zero contrações (`para`, `está`).
- **Fujimura Taiga (`Fujimura-sensei` / `Fuji-nee` — nível 4):** Descontraída, barulhenta, calorosa e exagerada; contrações e expressões coloquiais liberadas.
- **Carigiri Jinako (nível 4):** NEET reclusa, gamer/otaku de fórum; única junto da Taiga com gíria de internet e coloquialismo forte (`"pra"`, `"tá"`, `"normie"`).
- **Karna (Lancer — nível 1):** Solene, brutalmente honesto, econômico nas palavras e desprovido de malícia; zero gíria.
- **Gawain (Saber — nível 1):** Cavaleiro solar cortês, leal ao extremo a Leo, formal e honrado.
- **Hans Christian Andersen (Caster — nível 2):** Escritor cínico, rabugento, mordaz e observador; vocabulário culto com veneno ácido.
- **Elizabeth Báthory (Lancer — nível 3):** Idol autoproclamada, mimada, dramática e infantilmente vaidosa.

### Pontuação e estilo do CCC

- Reticências do original (`……`) são mantidas como estão.
- `―――` (travessão longo) é mantido.
- Aspas: use `"` reto, não aspas curvas — o jogo não tem glifo para elas.
- Não use `—` (travessão em) nem `º`/`ª`: não existem na fonte.

## Protocolo Antideriva e Passe Triplo

Ao trabalhar em lotes ou cenas longas, **nunca** degrade o ritmo para "fechar rápido" nem deixe a voz dos personagens convergir para um português neutro de máquina. Leia sempre ±3 falas em volta antes de traduzir e execute o **Passe Triplo** antes de dar a etapa como pronta:

1. **Passe literário e de largura (`medida.py`):** ritmo, subtexto, pontuação, máximo de 3 linhas e zero aviso de largura em pixels.
2. **Passe de voz (Teste Cego) e gênero (`genero.py`):** confirmar que cada personagem soa único e que todo adjetivo/particípio/pronome referente a Hakuno usa `#[masc][fem]#`.
3. **Passe antitradutês e Lista Negra:** eliminar decalques do inglês e garantir zero termo da Lista Negra.

## Fluxo de uma etapa

1. Ler o arquivo e contar quantas entradas faltam.
2. Traduzir em contexto, aplicando os glossários (`CCC` + `TYPEMOON`).
3. Se surgirem termos repetidos novos (locais, avisos de sistema, termos de lore), adicioná-los a `tools/glossario.py` e ao glossário operacional em vez de repetir à mão em cada arquivo.
4. Rodar `python tools/glossario.py` para padronizar.
5. Executar o Passe Triplo (`python tools/medida.py` e `python tools/genero.py`).
6. Rodar `python tools/build.py --only <grupo>/<arquivo>`.
7. Conferir os avisos do build. Aviso de limite estourado = etapa inválida até ser resolvido.
8. Registrar em `standards/DIARIO_DE_MUDANCAS.md` se algo estrutural mudou.
9. Informar quantas etapas faltam e pedir confirmação para seguir.

## Checklist antes de fechar uma etapa

- [ ] Nenhum `msgctxt` ou `msgid` foi alterado
- [ ] Todos os códigos de controle preservados e na mesma posição
- [ ] `python tools/medida.py` sem nenhum aviso de largura
- [ ] `python tools/genero.py` revisado, seletor aplicado onde o alvo é o protagonista
- [ ] `#[a][b]#` com as duas variantes concordando em português
- [ ] Acentuação correta, sem `?` e sem palavra sem acento
- [ ] Nenhuma caixa alta acentuada (`OPÇÕES`)
- [ ] Limites de bytes respeitados (build sem aviso de tamanho)
- [ ] Glossários (`CCC` + `TYPEMOON`) e ordem japonesa de nomes aplicados, sem itens da Lista Negra
- [ ] Passe Triplo (literário, voz/Teste Cego, antitradutês) concluído
- [ ] Build rodou e a ISO foi gerada
