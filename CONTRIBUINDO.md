# Como contribuir na tradução e revisão — Fate/Extra CCC PT-BR

Este projeto segue o mesmo fluxo de trabalho em equipe dos projetos irmão (FHA Remastered, FSN Remastered, Mahoyo e Tsukihime Remake), adaptado às travas técnicas do Fate/Extra CCC (PSP).

---

## 0. Git pelo GitHub Desktop

A `main` é a versão oficial. **Ninguém traduz direto na `main`:** cada pessoa trabalha numa branch própria e envia por pull request, tudo pelo [GitHub Desktop](https://desktop.github.com/).

**Uma vez só**
1. Instale o [GitHub Desktop](https://desktop.github.com/) (entre com a sua conta do GitHub) e o [Python 3.10+](https://www.python.org/downloads/), marcando **Add python.exe to PATH**.
2. Peça acesso ao repositório no Discord.
3. No GitHub Desktop: **File › Clone repository › URL**, cole `https://github.com/ThiagoKrz/FateExtraCCC-PT-BR` e clique em **Clone**.

**Começar uma tarefa** (reserve a cena na planilha antes, como explicado na seção 1)
1. **Current branch › `main`** e **Pull origin**. Se o botão estiver como **Fetch origin**, clique nele antes.
2. **Current branch › New branch**, nome `seunome/capitulo-cena` › **Create branch**.

**Todo dia, antes de traduzir**
1. **Current branch › `main`** e **Pull origin**.
2. Volte para a sua branch e clique em **Branch › Update from main**. Apareceu conflito? Chame alguém no Discord.

**Enviar** (depois das checagens da seção 3)
1. Na aba **Changes**, confira o que mudou (`trabalho/`, `ptbr/` e a planilha, se você sincronizou), escreva um resumo como `Traduz <capitulo/cena>` e clique em **Commit**.
2. **Publish branch**. Das próximas vezes, o botão vira **Push origin**. Faça isso no fim de cada dia, para o trabalho ficar guardado.
3. Tarefa pronta: **Preview Pull Request › Create pull request** e confirme no navegador. A revisão confere e junta na `main`.

Precisa corrigir? Novo commit e **Push origin** na mesma branch. Aceito? A próxima tarefa começa do zero.

> Se, ao trocar de branch, o Desktop perguntar o que fazer com as suas alterações, cancele e faça o commit antes.

Prefere o terminal? `git switch main && git pull && git switch -c seunome/capitulo-cena` para começar, `git pull --no-edit origin main` todo dia na sua branch e `git push -u origin seunome/capitulo-cena` para enviar.

---

## 1. Estrutura de organização e divisão de tarefas

- **Planilha online (Google Sheets):** [FATE EXTRA CCC PROGRESSO](https://docs.google.com/spreadsheets/d/1sML42bCigiHD25WuX4kTvQTPa5vRphshMTX5kRlXDsQ/edit)
- **Espelhos locais:** **`Fate_Extra_CCC_Progresso_Geral.xlsx`** e `FATE EXTRA CCC PROGRESSO - Geral.csv`.
  Organizam os **292 arquivos** em **15 capítulos / categorias** (`Prólogo`, `Capítulo 1` a `Capítulo 6`, `Cap. 7 e Finais`, `Escola (Hub)`, `Meu Quarto e BB`, `Secret Gardens`, `Info Matrix`, `Menus e Interface`, `Sistema e Comuns` e `Mapas Base (Auto)`).
  - Reserve sua cena colocando seu nome na coluna **REVISORES** e trocando **Estado** para `Em tradução` / `Em revisão` / `Revisado`.
  - **Não é necessário traduzir à mão** os **81 arquivos de `14_mapas_base_auto`**: eles contêm apenas o cabeçalho comum do motor (`0` falas exclusivas) e são sincronizados automaticamente.
  - Em `09_meu_quarto_bb`, traduza **`071`** (arquivo mestre do Meu Quarto): os arquivos **`032`** e **`033`** são espelhos e recebem as traduções automaticamente ao salvar `071` ou clicar em **Sincronizar repetidas**.

- **`trabalho/`**:
  Espelho organizado em pastas por capítulo com nomes legíveis (`<ordem>_<titulo>__<codigo>.json`), sincronizado em mão dupla com os arquivos originais `.po` em `ptbr/`.

- **`ptbr/`**:
  Pasta canônica dos `.po` consumida pelos scripts CLI (`build.py`, `medida.py`, `genero.py`, `glossario.py`). Quem preferir editar via Poedit ou editor de texto pode continuar editando em `ptbr/`.

---

## 2. Usando o Painel Gráfico (`Abrir painel.cmd`)

1. Dê duplo clique em **`Abrir painel.cmd`** na raiz do repositório (ou execute `python -X utf8 tools/painel_ccc.py`).
2. Na árvore à esquerda, selecione o capítulo e a cena (você pode filtrar por nome, código como `024`, `150`, `sg_ner` etc.).
   - A opção **Ocultar mapas base sem falas próprias (81)** vem marcada para manter o foco nos **211** arquivos com conteúdo real.
3. Edite o campo **Português brasileiro**:
   - A **régua em tempo real** logo abaixo do editor calcula automaticamente a largura em pixels (`dialog` = 338px / 319px na última linha, `choice` = 350px, `inDungeon` = 396px), o limite de bytes fixos (`sg/`, `lore/`, `eboot`, `main`) e suspeitas de gênero `#[masc][fem]#`.
   - Botões rápidos ajudam a inserir `#[masc][fem]#` e copiar códigos de cor (`#C...#CDEF`, `#RUBS`, `#FAMILY`, `#GIVEN`, `#SVT`).
   - O painel salva automaticamente (após 1,5s de pausa ou com `Ctrl+S`), atualizando tanto `trabalho/*.json` quanto `ptbr/*.po`.
   - Com **Propagar repetidas ao salvar** ativado, frases comuns já traduzidas são reaplicadas com segurança nas cópias vazias e nos espelhos `032`/`033`.
4. Use a barra superior sempre que quiser:
   - **`Validar projeto (F5)`**: roda todas as travas em todos os 292 arquivos.
   - **`Busca global (Ctrl+Shift+F)`**: encontra qualquer trecho em inglês, português ou `msgctxt` no projeto inteiro.
   - **`Conferir glossário`**: verifica desvios na cena contra `standards/GLOSSARIO_CCC_OPERACIONAL.json` e `standards/GLOSSARIO_TYPEMOON_OPERACIONAL.json`.
   - **`Sincronizar repetidas`**: propaga falas comuns e atualiza `Fate_Extra_CCC_Progresso_Geral.xlsx` preservando os nomes já preenchidos na planilha.
   - **`Testar cena (--only)` / `Gerar ISO completa (Ctrl+Enter)`**: compila `output/ccc-ptbr.iso` via `tools/build.py` para testar no PPSSPP.

---

## 3. Regras de ouro (obrigatórias antes de qualquer commit)

1. Leia na ordem:
   `standards/GLOSSARIO_CCC_OPERACIONAL.json` → `standards/GLOSSARIO_TYPEMOON_OPERACIONAL.json` → `standards/README.md` → `standards/PROMPT_TRADUCAO_CCC.md` → `standards/DIARIO_DE_MUDANCAS.md`.
2. **Códigos de controle são sagrados**: nunca altere `#C...`, `#CDEF`, `#RUBS`, `#RUBE`, `#REND`, `#FAMILY`, `#GIVEN`, `#SVT`, `#TITM...`, etc.
3. **Gênero do protagonista**: use sempre `#[masculino][feminino]#` quando o texto se dirigir ou qualificar o(a) protagonista.
4. **Proibido caixa alta acentuada (`Â`, `Ã`, `Ê`, `Ô`, `Õ`)** — não existem na fonte do PSP (`OPÇÕES` falha; use minúsculas com acento correto no meio da frase ou sem acento em rótulos tudo-maiúsculo quando inevitável).
5. **Nunca mude o tamanho de nada dentro de `pack/PRELOAD.pak`** (atenção especial a `historia/main.po` e `menus/interface__cmn__install.po`).
6. Antes de enviar:
   ```bash
   python -X utf8 tools/medida.py
   python -X utf8 tools/genero.py
   python -X utf8 tools/scripts_ccc.py --validate
   git status
   ```
