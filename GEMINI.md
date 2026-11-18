# Fate/Extra CCC PT-BR — Regras do Projeto

Antes de traduzir, mexer em qualquer script de `tools/` ou gerar a ISO, leia e
obedeça obrigatoriamente nesta ordem:

1. `standards/GLOSSARIO_CCC_OPERACIONAL.json`
2. `standards/GLOSSARIO_TYPEMOON_OPERACIONAL.json` *(cópia sincronizada do Fate Café)*
3. `standards/README.md`
4. `standards/PROMPT_TRADUCAO_CCC.md`
5. `standards/DIARIO_DE_MUDANCAS.md` ← **estado atual do projeto, leia sempre**

Padrão Type-Moon consolidado nos projetos irmãos (fonte de verdade geral):
- `C:/Users/Thiago/Desktop/fate-cafe-react/standards/type-moon/GLOSSARIO_TYPEMOON_OPERACIONAL.json`
- FSN Remastered (`PROMPT_REVISAO_FSN_REMASTERED_SCRIPTS.md`)
- FHA Remastered (`PROMPT_AGENTE_FHA_UNIFICADO.md`)
- Mahoyo VN & Mangá (`PADRAO_NOMES.md`, `REGRAS_TRADUCAO_MANGA.md`)
- Tsukihime Remake (`HANDOFF.md`)

## Regras inegociáveis

- O glossário é PRIORIDADE MÁXIMA.
- Termos gerais Type-Moon seguem o padrão unificado do Fate Café:
  - `Servant` → **Servo** / **Servos**; `Master` → **Mestre** / **Mestra**;
  - `Noble Phantasm` → **Fantasma Nobre**; `Mystic Code` → **Artefato Místico**;
  - `Command Seal` / `Command Spell` → **Selo de Comando**;
  - `True Magic` (`魔法`) → **Magia Verdadeira** (maiúscula) vs `Magecraft` (`魔術`) → **magia** (minúscula no meio da frase; proibido `taumaturgia`/`feitiçaria`);
  - `Magician` (`魔法使い`) → **Feiticeiro(a)** (maiúscula) vs `Magus` (`魔術師`) → **mago(a)** (minúscula no meio da frase);
  - Classes de Servo (`Saber`, `Archer`, `Lancer`, `Rider`, `Caster`, `Assassin`, `Berserker`, `Savior`, `Gunner`, `Alter Ego`, `Moon Cancer`, `Ruler`, etc.) **nunca** são traduzidas.
- **Nomes completos japoneses seguem a ordem japonesa (Sobrenome Nome), sem mácrons**: `Kishinami Hakuno`, `Tohsaka Rin`, `Matou Sakura`, `Matou Shinji`, `Ryuudou Issei`, `Fujimura Taiga`, `Aozaki Touko`, `Kotomine Kirei`, `Sessyoin Kiara`, `Carigiri Jinako`, `Monji Gatou`. Honoríficos (`-san`, `-kun`, `-chan`, `-sensei`, `Senpai`, `Kouhai`) são mantidos.
- **Ao terminar qualquer mudança maior, decisão de arquitetura ou descoberta sobre o formato do jogo, registre em `standards/DIARIO_DE_MUDANCAS.md` antes de encerrar.** Mudança não registrada é trabalho incompleto.
- Códigos de controle do jogo (`#CDEF`, `#RUBS`, `#[a][b]#`, …) são sagrados: copiar exatamente, na mesma posição. Todo adjetivo/particípio/pronome referente ao protagonista usa `#[masc][fem]#`.
- Nunca alterar `msgctxt` nem `msgid` nos arquivos `.po`. Só `msgstr`.
- PT-BR natural, com acentuação correta sempre. Proibido escrever sem acento ou usar `?` no lugar de acento.
- Nunca usar caixa alta acentuada (`OPÇÕES`): `Â Ã Ê Ô Õ` não existem na fonte.
- **Nenhum arquivo dentro de `pack/PRELOAD.pak` pode mudar de tamanho.** Um byte a mais trava o jogo no boot (atenção especial a `historia/main.po` → `field_new/main/0000.dat`).
- Antes de fechar qualquer etapa, rodar obrigatoriamente `python tools/medida.py` e `python tools/genero.py` para garantir zero corte de linha e gênero correto.
- A tradução é feita por etapas. Ao fim de cada etapa, informe quantas faltam.
- Nunca fazer troca cega de termo se isso quebrar concordância ou naturalidade; reescreva a frase inteira quando necessário.

## Comandos

```bash
python tools/dump.py        # (re)gera os .po a partir do jogo
python tools/glossario.py   # padroniza termos repetidos em todos os arquivos
python tools/medida.py      # verifica se alguma linha estoura a caixa na tela
python tools/genero.py      # verifica concordância #[masc][fem]# do protagonista
python tools/build.py       # gera output/ccc-ptbr.iso
python tools/integrity.py output/ccc-ptbr.iso   # prova que só mudou o pretendido
```
