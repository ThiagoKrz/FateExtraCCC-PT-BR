# Guia Operacional — Fate/Extra CCC PT-BR

Padrão oficial deste repositório para traduzir, injetar e gerar a ISO PT-BR de
**Fate/Extra CCC (PSP)**.

Este guia herda o padrão Type-Moon unificado do Fate Café
(`standards/GLOSSARIO_TYPEMOON_OPERACIONAL.json`, sincronizado de
`C:/Users/Thiago/Desktop/fate-cafe-react/standards/type-moon/GLOSSARIO_TYPEMOON_OPERACIONAL.json`)
e dos projetos irmãos (**FSN Remastered**, **FHA Remastered**, **Mahoyo VN/Mangá** e
**Tsukihime Remake**), acrescentando o que é específico deste jogo.

## Leitura obrigatória para LLMs

Nesta ordem:

1. `standards/GLOSSARIO_CCC_OPERACIONAL.json`
2. `standards/GLOSSARIO_TYPEMOON_OPERACIONAL.json` *(cópia sincronizada do Fate Café)*
3. `standards/README.md` (este arquivo)
4. `standards/PROMPT_TRADUCAO_CCC.md`
5. `standards/DIARIO_DE_MUDANCAS.md` ← **leia sempre, é o estado atual do projeto**

Regra de conflito:

- Glossário vence o prompt.
- Para termos gerais da Type-Moon (`Servo`, `Mestre`, `Fantasma Nobre`,
  `Artefato Místico`, `Selo de Comando`, `Magia Verdadeira` vs `magia`,
  `Feiticeiro(a)` vs `mago(a)`, ordem japonesa de nomes completos sem mácrons,
  honoríficos, classes nunca traduzidas — inclusive `Savior`), o glossário
  central do **Fate Café** (`GLOSSARIO_TYPEMOON_OPERACIONAL.json`) vence.
- Para termos, nomes de UI/sistema e limites técnicos exclusivos do CCC,
  `GLOSSARIO_CCC_OPERACIONAL.json` vence.
- Instrução da tarefa atual pode complementar o padrão, nunca derrubar o glossário.

## Regra de registro (inegociável)

**Ao terminar qualquer mudança maior, decisão de arquitetura ou descoberta sobre
o formato do jogo, registre em `standards/DIARIO_DE_MUDANCAS.md` antes de
encerrar.**

O diário é o que permite a próxima sessão continuar sem redescobrir nada. Uma
mudança não registrada é considerada trabalho incompleto.

O que sempre entra no diário:

- mudança em qualquer script de `tools/`;
- descoberta sobre formato de arquivo, endereço, limite ou codificação;
- decisão de padronização que afete a tradução inteira;
- qualquer bug encontrado no jogo gerado e sua causa raiz.

---

## O que é este projeto

A base é a ISO **já traduzida para inglês** (`EnglishBase/ccc-patched.iso`), feita
pela equipe do [ccc-tl](https://github.com/ccc-tl/translation-tools).

Nós traduzimos por cima dela. O que não estiver traduzido para PT-BR **continua
aparecendo em inglês**, nunca em japonês. O resultado é sempre uma `.iso` pronta
em `output/ccc-ptbr.iso` — não é um patch.

### Por que não usamos as ferramentas da equipe para gerar

As ferramentas deles vão de **ISO japonesa → ISO traduzida**. Isso não serve aqui:

- exigem a ISO japonesa, que não temos;
- o que não fosse traduzido sairia em japonês;
- o `CccRepackager` reescreve o EBOOT com patches de ASM em endereços fixos, e o
  nosso EBOOT **já está patcheado** — aplicar de novo corrompe.

Então os formatos foram portados para Python em `tools/`, operando direto sobre
a ISO inglesa. O código Kotlin deles continua sendo a **especificação**: quando
houver dúvida sobre um formato, a resposta está lá.

---

## Arquitetura

A ISO guarda quase tudo em um arquivo só:

```
ccc-patched.iso
├── PSP_GAME/SYSDIR/EBOOT.BIN     executável (ELF, já descriptografado)
└── PSP_GAME/INSDIR/GAME.DNS      arquivo CPK, 14.851 itens
    └── pack/*.pak                1.641 containers
        ├── field_new/NNN/0000.dat   história e diálogos
        ├── interface/**/*.bin       menus, SG, Info Matrix
        └── font.txb + kanzi.bin     a fonte
```

Fluxo:

```
ptbr/*.po  →  .dat / .bin  →  .pak  →  GAME.DNS  →  output/ccc-ptbr.iso
```

### Ciclo de trabalho

```bash
# 1. traduzir: editar os .po em ptbr/
# 2. padronizar termos repetidos
python tools/glossario.py
# 3. validar largura de linha e gênero do protagonista
python tools/medida.py
python tools/genero.py
# 4. gerar a ISO
python tools/build.py
# 5. conferir o que entrou de verdade
python tools/verify.py output/ccc-ptbr.iso interface/shop/msg.bin
python tools/integrity.py output/ccc-ptbr.iso
# 6. testar
"C:\Program Files\PPSSPP\PPSSPPWindows64.exe" --log=work/pp.log output/ccc-ptbr.iso
```

Build parcial, para iterar rápido:

```bash
python tools/build.py --only historia/007
python tools/build.py --only menus/interface__shop__msg,sg/interface__sg__sg_ner_text1
```

---

## Organização da tradução

| Pasta | Conteúdo | Limite de tamanho |
|---|---|---|
| `ptbr/historia/` | 187 arquivos, um por cena | livre (exceto `main`) |
| `ptbr/menus/` | 22 arquivos de interface | varia por arquivo |
| `ptbr/sg/` | 62 arquivos, Secret Gardens | **campo fixo** |
| `ptbr/lore/` | 16 arquivos, Info Matrix | **campo fixo** |
| `ptbr/sistema/` | textos dentro do EBOOT | **campo fixo** |

`ptbr/_INDICE.md` lista todos os arquivos com contagem e amostra. Regerar com
`python tools/dump.py` (preserva o que já foi traduzido).

Formato `.po` padrão (Poedit / Weblate). `msgstr` vazio = mantém o inglês.

---

## As ferramentas

| Arquivo | Função |
|---|---|
| `tools/dump.py` | Lê o jogo e (re)gera os `.po` em `ptbr/` |
| `tools/build.py` | Lê os `.po` e gera `output/ccc-ptbr.iso` |
| `tools/glossario.py` | Aplica o glossário em todos os arquivos de uma vez |
| `tools/medida.py` | Mede a largura de cada linha e acusa o que seria cortado na tela |
| `tools/genero.py` | Acha concordância de gênero que precisa do seletor `#[masc][fem]#` |
| `tools/accents.py` | Monta os glifos acentuados na fonte |
| `tools/verify.py` | Lê uma ISO gerada e mostra o que está lá dentro |
| `tools/integrity.py` | Prova que só os arquivos pretendidos mudaram |
| `tools/validate.py` | Confere a extração contra os ponteiros oficiais da equipe |
| `tools/unusedglyphs.py` | Acha glifos da fonte que nenhum texto usa |
| `tools/freeslots.py` | Acha bytes de controle ainda livres |
| `tools/isobuild.py` | Reconstrói a ISO do zero quando não cabe mais injetar |
| `tools/cpk.py` `pak.py` `binfile.py` `fixedbin.py` `fatetext.py` `eboot.py` `tex.py` `kanzi.py` | Leitores/gravadores dos formatos |

`tools/data/` guarda os índices oficiais da equipe (`dat-pointers.json`,
`eboot-pointers.json`), usados para validação.

`work/` é 100% regenerável a partir da ISO base e pode ser apagado.

---

## Armadilhas conhecidas

Detalhes completos e o histórico estão em `DIARIO_DE_MUDANCAS.md`. Resumo do que
mais morde:

1. **`PRELOAD.pak` não pode mudar de tamanho.** Um único byte a mais desloca o
   código nativo do patch inglês e o jogo dá tela preta. Há travas automáticas.
2. **Acentos não são UTF-8.** São bytes de controle ligados a glifos na fonte.
   19 letras funcionam; `Â Ã Ê Ô Õ` rebaixam para a letra sem acento.
3. **Campos de largura fixa** em SG, Info Matrix e EBOOT. O `.po` traz o limite.
4. **`ptbr/historia/` não tem limite** de tamanho, porque o texto é acessado por
   ponteiro e pode ser realocado para o fim do arquivo.
5. **A ISO é reconstruída** automaticamente quando o CPK não cabe mais no espaço
   original. Isso muda o tamanho do arquivo final, e é esperado.

## Como depurar tela preta ou travamento

```bash
"C:\Program Files\PPSSPP\PPSSPPWindows64.exe" --log=work/pp.log output/ccc-ptbr.iso
```

- `Bad memory access` com endereço pequeno (ex.: `00000012`) = ponteiro nulo,
  quase sempre recurso que falhou ao carregar → suspeite de `PRELOAD.pak`.
- Sinal de que está renderizando: o log sai de `0 vertex, 0 fragment shaders`
  para valores não nulos.
- `python tools/integrity.py <iso>` prova se algum arquivo foi corrompido sem querer.
- Para isolar o culpado, faça build parcial com `--only` e vá somando.
