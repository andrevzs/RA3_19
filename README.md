# RA3_19 — Compilador RPN (Fases 1–3)

**Instituição:** Pontifícia Universidade Católica do Paraná (PUCPR)  
**Disciplina:** Linguagens Formais e Compiladores (LFC) — 2026/1  
**Professor:** Prof. Frank Alcântara  
**Grupo Canvas:** RA3_19

## Integrantes (ordem alfabética)

- André Vinícius Zicka Schmidt — andrevzs
- Gabriel Fischer Domakoski — fochu3013

---

## Descrição

Este projeto implementa um compilador para uma linguagem de programação simplificada em **Notação Polonesa Reversa (RPN)**, desenvolvido em três fases:

- **Fase 1** (`lexer.py`): analisador léxico com autômato finito determinístico (AFD).
- **Fase 2** (`AnalisadorSintatico.py`): analisador sintático LL(1), geração de árvore sintática e geração de código Assembly ARMv7 para Cpulator-ARMv7 DEC1-SOC(v16.1).
- **Fase 3** (`AnalisadorSemantico.py`): analisador semântico — comentários `*{…}*`, tabela de símbolos, verificação de tipos e geração de Assembly a partir da árvore atribuída.

---

## Sintaxe da Linguagem

Programas são escritos em RPN, no formato `(A B op)`, envoltos em `(START)` e `(END)`.

### Operadores Aritméticos

| Operador | Significado | Exemplo |
|----------|-------------|---------|
| `+` | Adição | `(3.0 2.0 +)` |
| `-` | Subtração | `(5.0 1.0 -)` |
| `*` | Multiplicação | `(4.0 3.0 *)` |
| `\|` | Divisão real (double) | `(10.0 3.0 \|)` |
| `/` | Divisão inteira | `(10 3 /)` |
| `%` | Resto da divisão | `(10 3 %)` |
| `^` | Potenciação (exp. inteiro ≥ 0) | `(2 8 ^)` |

### Operadores Relacionais

`>`, `<`, `==`, `!=`, `>=`, `<=` — produzem o tipo `bool` (resultado de comparação).

### Comandos Especiais

| Comando | Significado |
|---------|-------------|
| `(N RES)` | Resultado da expressão N linhas atrás |
| `(V MEM)` | Armazena o valor `V` na memória `MEM` |
| `(MEM)` | Carrega o valor armazenado em `MEM` (retorna 0.0 se não inicializado) |

### Comentários

Comentários são delimitados por `*{` e `}*` e podem aparecer em qualquer posição:

```
*{ comentário em linha própria }*
(3.0 2.0 +)   *{ comentário no final da linha }*
(10 *{ comentário entre tokens }* 5 +)
*{ comentário
   multilinha }*
```

### Estruturas de Controle

#### Decisão (IF)

```
(IF cond true_stmt)
(IF cond true_stmt false_stmt)
```

Exemplos:
```
(IF (X 0.0 >) (1.0 RESULTADO) (0.0 RESULTADO))
(IF (CONTADOR 5 >=) ((CONTADOR 1 +) CONTADOR))
```

#### Laço de Repetição (WHILE)

```
(WHILE cond body_stmt)
```

Exemplos:
```
(WHILE (I 10 <) ((I 1 +) I))
(WHILE (TOTAL LIMITE !=) ((TOTAL PASSO +) TOTAL))
```

- `cond` deve avaliar para o tipo `bool` (resultado de operador relacional ou literal `TRUE`/`FALSE`).
- Aninhamento ilimitado.

---

## Tipos Suportados

A linguagem possui sistema de tipos **estático e forte**: o tipo de cada variável é determinado no momento da primeira definição e não pode ser alterado.

| Tipo | Descrição | Literais |
|------|-----------|---------|
| `int` | Inteiro de precisão simples | `0`, `42`, `100` |
| `real` | Ponto flutuante duplo IEEE 754 | `0.0`, `3.14`, `2.5` |
| `bool` | Valor lógico produzido por operadores relacionais ou pelos literais `TRUE`/`FALSE` | `TRUE`, `FALSE` |
| `unknown` | Tipo não determinável estaticamente (propagado sem erro) | resultado de `(N RES)` |

### Regras de Compatibilidade de Tipos

| Operação | Tipos válidos | Tipo resultante |
|----------|---------------|-----------------|
| `+` `-` `*` `^` | int × int | int |
| `+` `-` `*` `^` | int × real ou real × real | real |
| `\|` | int ou real × int ou real | real |
| `/` | int × int | int |
| `%` | int × int | int |
| `>` `<` `==` `!=` `>=` `<=` | int ou real × int ou real | bool |
| IF/WHILE condição | — | deve ser `bool` |

Operações com `bool` como operando aritmético ou relacional geram **erro semântico**.

---

## Regras para Definição e Uso de Variáveis

1. **Definição**: usa o padrão `(V MEM)`, onde `V` é um literal numérico ou expressão e `MEM` é um identificador em letras maiúsculas. Exemplo: `(42 CONTADOR)`, `(3.14 PI)`.
2. **Uso**: usa o padrão `(MEM)` para carregar o valor da variável, ou usa `MEM` como operando em uma expressão: `(CONTADOR 1 +)`.
3. **Declaração obrigatória antes do uso**: qualquer variável usada sem ter sido previamente definida com `(V MEM)` gera um **erro semântico**.
4. **Tipo imutável**: uma variável definida como `int` não pode ser redefinida como `real` (e vice-versa). Redefinição com tipo incompatível gera **erro semântico**.
5. **Identificadores reservados**: `TRUE` e `FALSE` são literais booleanos e não podem ser usados como nomes de variáveis.
6. **Escopo**: cada arquivo de código-fonte é um escopo independente.

---

## Compilação e Execução

### Pré-requisitos

- Python 3.10 ou superior (sem dependências externas)

### Executar o compilador completo (Fase 3)

```bash
python AnalisadorSemantico.py <arquivo.txt>
```

Exemplo:
```bash
python AnalisadorSemantico.py teste1.txt
```

### Executar o compilador Fase 2 (léxico + sintático + Assembly)

```bash
python AnalisadorSintatico.py <arquivo.txt>
```

**Saídas geradas pelo compilador (Fase 3):**

| Arquivo | Conteúdo |
|---------|----------|
| `arvore_atribuida.json` | Árvore sintática atribuída com anotações de tipo e categoria |
| `programa.asm` | Código Assembly ARMv7 (gerado apenas para programas sem erros) |
| `tabela_simbolos.md` | Tabela de símbolos com tipos, linhas de definição e uso |
| `erros_tipos.md` | Relatório de erros semânticos de tipo |

### Executar os testes unitários

```bash
# Fase 3 — Aluno 1: léxico com comentários e prepararEntradaSemantica
python AnalisadorSemantico.py --test-preparar

# Fase 3 — Aluno 2: construirTabelaSimbolos
python AnalisadorSemantico.py --test-construir

# Fase 3 — Aluno 3: verificarTipos
python AnalisadorSemantico.py --test-verificar

# Fase 3 — Aluno 4: gerarArvoreAtribuida e gerarAssembly
python AnalisadorSemantico.py --test-aluno4

# Fase 2 — gramática LL(1) (FIRST, FOLLOW, tabela)
python AnalisadorSintatico.py --test-gramatica

# Fase 2 — parser LL(1)
python AnalisadorSintatico.py --test-parsear

# Fase 2 — analisador léxico
python AnalisadorSintatico.py --test-lerTokens
```

---

## Arquivos de Teste

| Arquivo | Descrição |
|---------|-----------|
| `teste1.txt` | Programa válido: todos os ops, IF, WHILE, vars, TRUE/FALSE, comentários |
| `teste2.txt` | Erros semânticos intencionais (6 casos documentados nos comentários) |
| `teste3.txt` | Programa complexo: aninhamento de 3 níveis, todos os tipos, todos os ops |
| `teste_erros.txt` | Erro léxico intencional (`@` na linha 13) |
| `teste_erro_sintatico.txt` | Erro sintático intencional (token extra após operador) |

Para testar tratamento de erros:
```bash
# Erro léxico: caractere inválido '@'
python AnalisadorSemantico.py teste_erros.txt

# Erro sintático: token inesperado após operador
python AnalisadorSemantico.py teste_erro_sintatico.txt

# Erros semânticos: variável não declarada, tipos incompatíveis etc.
python AnalisadorSemantico.py teste2.txt
```

### Exemplos de Programas Semanticamente Válidos

```
(START)
*{ define e usa variáveis de tipos diferentes }*
(42 CONTADOR)           *{ int }*
(3.14 PI)               *{ real }*
(CONTADOR 1 +)          *{ int + int = int }*
(PI 2.0 *)              *{ real * real = real }*
(CONTADOR 10 <)         *{ int < int = bool }*
(IF (CONTADOR 10 <) ((CONTADOR 1 +) CONTADOR))
(WHILE (CONTADOR 5 <) ((CONTADOR 1 +) CONTADOR))
(END)
```

```
(START)
*{ expressões aninhadas }*
((3.0 4.0 *) (2.0 1.0 +) +)   *{ real }*
(((1 2 +) 3 -) 4 *)            *{ int }*
(2 4 ^)                         *{ potenciação: int }*
(10.0 3.0 |)                    *{ divisão real: real }*
(1 RES)                         *{ unknown }*
(END)
```

### Exemplos de Programas Semanticamente Inválidos

```
(START)
(X 1 +)        *{ ERRO: X usada antes de ser definida }*
(42 X)
(END)
```

```
(START)
(42 X)
(3.14 X)       *{ ERRO: X redefinida com tipo incompatível (int → real) }*
(END)
```

```
(START)
(1.0 A)
(IF (A) (2.0 3.0 +))   *{ ERRO: condição do IF deve ser bool, não real }*
(END)
```

```
(START)
(3.5 2 /)      *{ ERRO: divisão inteira '/' requer tipo int (obteve real e int) }*
(END)
```

---

## Explicação da Tabela de Símbolos

A tabela de símbolos é produzida pela função `construirTabelaSimbolos()` durante a análise semântica. Ela é salva em `tabela_simbolos.md` a cada execução.

**Campos registrados para cada variável:**

| Campo | Descrição |
|-------|-----------|
| Variável | Nome do identificador (letras maiúsculas) |
| Tipo | Tipo inferido: `int`, `real` ou `unknown` |
| Escopo | Escopo de visibilidade da variável (sempre `global` — cada arquivo é um escopo independente) |
| Linha de Definição | Linha do arquivo fonte onde a variável foi definida com `(V MEM)` |
| Linhas de Uso | Lista de todas as linhas onde a variável foi usada como operando |

**Funcionamento:**
- Ao encontrar `(V MEM)`, registra `MEM` com o tipo de `V` e a linha corrente.
- Ao encontrar `MEM` como operando, registra a linha corrente na lista de usos.
- Se `MEM` é usado antes de ser definido → **erro semântico** com número de linha.
- Se `MEM` é redefinido com tipo incompatível → **erro semântico** com tipos conflitantes.

**Exemplo de tabela gerada (`tabela_simbolos.md`):**

| Variável | Tipo | Escopo | Linha de Definição | Linhas de Uso |
|---|---|---|---|---|
| CONT | real | global | 15 | 16, 17 |
| SALDO | real | global | 10 | 11, 20, 21, 22 |

---

## Explicação da Árvore Sintática Atribuída

A árvore sintática atribuída é produzida pela função `gerarArvoreAtribuida()` e salva em `arvore_atribuida.json` a cada execução bem-sucedida.

**Diferença em relação à árvore da Fase 2:**

A árvore atribuída estende a árvore sintática original com o campo `anotacoes` em cada nó:

```json
{
  "tipo": "NT",
  "simbolo": "stmt_inner",
  "linha": 6,
  "filhos": [...],
  "anotacoes": {
    "tipo_semantico": "real",
    "categoria": "expressao"
  }
}
```

**Campos de `anotacoes`:**

| Campo | Presente em | Descrição |
|-------|-------------|-----------|
| `tipo_semantico` | Todos os nós | Tipo inferido pelo analisador semântico (`int`, `real`, `bool`, `unknown`, ou `null` para comandos sem valor de retorno como IF/WHILE/STORE) |
| `categoria` | Nós NT | Papel semântico do nó: `inicio`, `fim`, `condicional`, `repeticao`, `expressao`, ou o `simbolo` do NT |

**Categorias dos nós `stmt_inner`:**

| Categoria | Quando ocorre |
|-----------|--------------|
| `inicio` | `(START)` |
| `fim` | `(END)` |
| `condicional` | `(IF ...)` |
| `repeticao` | `(WHILE ...)` |
| `expressao` | qualquer expressão aritmética, relacional, LOAD, STORE ou RES |

---

## Documentação Técnica

- [`GRAMATICA.md`](GRAMATICA.md) — Gramática atribuída LL(1) completa: produções com ações semânticas, conjuntos FIRST e FOLLOW, tabela de análise e árvore sintática de exemplo.
- [`REGRAS_TIPOS.md`](REGRAS_TIPOS.md) — Sistema de regras de validação de tipos em cálculo de sequentes (Aluno 3).
- [`arvore_atribuida.json`](arvore_atribuida.json) — Árvore sintática atribuída da última execução (gerada com `teste1.txt`).
- [`programa.asm`](programa.asm) — Assembly ARMv7 gerado pela última execução (gerado com `teste1.txt`).
- [`tabela_simbolos.md`](tabela_simbolos.md) — Tabela de símbolos da última execução.
- [`erros_tipos.md`](erros_tipos.md) — Relatório de erros de tipo da última execução.

---

## Arquitetura do Código (`AnalisadorSemantico.py`)

| Função | Aluno | Descrição |
|---|---|---|
| `lerTokensFase3(arquivo)` | Aluno 1 | Léxico com suporte a comentários `*{…}*` |
| `prepararEntradaSemantica(arquivo)` | Aluno 1 | Integra léxico + parser da Fase 2; valida START/END |
| `construirTabelaSimbolos(arvore)` | Aluno 2 | Constrói tabela de símbolos; detecta declarações/usos inválidos |
| `salvarTabelaSimbolos(tabela, erros)` | Aluno 2 | Salva tabela em `tabela_simbolos.md` |
| `verificarTipos(arvore, tabela)` | Aluno 3 | Verifica compatibilidade de tipos; infere tipos dos nós |
| `salvarErrosTipos(erros)` | Aluno 3 | Salva relatório de erros em `erros_tipos.md` |
| `gerarArvoreAtribuida(arvore, tabela, tipos)` | Aluno 4 | Produz árvore com anotações semânticas |
| `gerarAssembly(arvoreAtribuida)` | Aluno 4 | Gera código Assembly ARMv7 a partir da árvore atribuída |
| `main()` | Aluno 4 | Interface de linha de comando e coordenação do pipeline completo |

---

## Geração de Assembly

O código Assembly gerado usa instruções **ARMv7 VFP** (ponto flutuante IEEE 754 double):

- `VLDR` / `VSTR` — carrega/armazena double de/para memória
- `VADD.F64`, `VSUB.F64`, `VMUL.F64`, `VDIV.F64` — operações em ponto flutuante
- `VCVT.S32.F64` / `VCVT.F64.S32` — conversão inteiro ↔ double (para `%` e `/`)
- `SDIV` — divisão inteira de inteiros de 32 bits
- `VCMP.F64` + `VMRS APSR_nzcv, FPSCR` — comparação para estruturas de controle
- Rótulos (`label:`) + branches (`BEQ`, `BGT`, `BLT`, etc.) — saltos condicionais

---

## Depuração

Para depurar, execute com um arquivo de teste simples:

```bash
python AnalisadorSemantico.py teste1.txt
```

O programa imprime no terminal:
1. Arquivo analisado
2. Resultado da análise léxica (número de tokens)
3. Resultado da análise sintática
4. Resultado da análise semântica (tabela de símbolos e verificação de tipos)
5. Lista de erros encontrados (se houver)
6. Caminhos dos arquivos de saída gerados

Mensagens de erro incluem o número de linha e descrição:
- **Erro léxico** (`ValueError`): caractere inválido, comentário não fechado
- **Erro sintático**: token inesperado com indicação de linha
- **Erro semântico**: variável não declarada, tipo incompatível, condição inválida, divisão/resto com não-inteiros
