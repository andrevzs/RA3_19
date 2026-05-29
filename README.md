# RA3_19 — Analisador Sintático LL(1)

**Instituição:** Pontifícia Universidade Católica do Paraná (PUCPR)  
**Disciplina:** Linguagens Formais e Compiladores (LFC) — 2026/1  
**Professor:** Prof. Frank Alcântara  
**Grupo Canvas:** RA3_19

## Integrantes (ordem alfabética)

- André Vinícius Zicka Schmidt — andrevzs
- Gabriel Fischer Domakoski — fochu3013

---

## Descrição

Este projeto implementa um compilador para uma linguagem de programação simplificada em **Notação Polonesa Reversa (RPN)**, desenvolvido em duas fases:

- **Fase 1** (`lexer.py`): analisador léxico com autômato finito determinístico (AFD).
- **Fase 2** (`AnalisadorSintatico.py`): analisador sintático LL(1), geração de árvore sintática e geração de código Assembly ARMv7 para Cpulator-ARMv7 DEC1-SOC(v16.1).

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
| `^` | Potenciação (exp. inteiro ≥ 0) | `(2.0 8.0 ^)` |

### Operadores Relacionais

`>`, `<`, `==`, `!=`, `>=`, `<=` — produzem `1.0` (verdadeiro) ou `0.0` (falso).

### Comandos Especiais

| Comando | Significado |
|---------|-------------|
| `(N RES)` | Resultado da expressão N linhas atrás |
| `(V MEM)` | Armazena o valor `V` na memória `MEM` |
| `(MEM)` | Carrega o valor armazenado em `MEM` (retorna 0.0 se não inicializado) |

### Estruturas de Controle

#### Decisão (IF)

```
(IF cond true_stmt)
(IF cond true_stmt false_stmt)
```

Exemplos:
```
(IF (X 0.0 >) (1.0 RESULTADO) (0.0 RESULTADO))
(IF (CONTADOR 5.0 >=) (CONTADOR MAXIMO))
```

#### Laço de Repetição (WHILE)

```
(WHILE cond body_stmt)
```

Exemplos:
```
(WHILE (I 10.0 <) ((I 1.0 +) I))
(WHILE (TOTAL LIMITE !=) ((TOTAL PASSO +) TOTAL))
```

- `cond` é qualquer expressão RPN; se avaliada como não-zero, o laço continua.
- Aninhamento ilimitado.

---

## Compilação e Execução

### Pré-requisitos

- Python 3.10 ou superior (sem dependências externas)

### Executar o compilador (Fase 2)

```bash
python AnalisadorSintatico.py <arquivo.txt>
```

Exemplo:
```bash
python AnalisadorSintatico.py teste1.txt
```

**Saídas geradas:**

| Arquivo | Conteúdo |
|---------|----------|
| `arvore.json` | Árvore sintática em formato JSON |
| `programa.asm` | Código Assembly ARMv7 pronto para Cpulator |

### Executar o analisador léxico (Fase 1)

```bash
python lexer.py teste1.txt
```

### Executar os testes unitários

```bash
# Testes da gramática LL(1) (FIRST, FOLLOW, tabela)
python AnalisadorSintatico.py --test-gramatica

# Testes do parser LL(1)
python AnalisadorSintatico.py --test-parsear

# Testes do analisador léxico
python AnalisadorSintatico.py --test-lerTokens
```

---

## Arquivos de Teste

| Arquivo | Descrição |
|---------|-----------|
| `teste1.txt` | Todas as operações aritméticas, IF, WHILE, MEM, RES |
| `teste2.txt` | Operações com variáveis, operadores relacionais, IF com `>=` |
| `teste3.txt` | Expressões aninhadas, IF com `!=`, WHILE com incremento por 10 |
| `teste_erros.txt` | Erro léxico intencional (`@`) para validar recuperação de erros |
| `teste_erro_sintatico.txt` | Erro sintático intencional (operando extra após operador) |

Para testar tratamento de erros:
```bash
# Erro léxico: caractere inválido '@'
python AnalisadorSintatico.py teste_erros.txt

# Erro sintático: token inesperado após operador
python AnalisadorSintatico.py teste_erro_sintatico.txt
```

---

## Documentação Técnica

- [`GRAMATICA.md`](GRAMATICA.md) — Gramática LL(1) completa: produções, conjuntos FIRST e FOLLOW, tabela de análise, e árvore sintática de exemplo.
- [`arvore.json`](arvore.json) — Árvore sintática da última execução.
- [`programa.asm`](programa.asm) — Assembly gerado pela última execução.

---

## Arquitetura do Código (`AnalisadorSintatico.py`)

| Função / Classe | Responsável | Descrição |
|---|---|---|
| `lerTokens(arquivo)` | Aluno 3 | Analisador léxico (AFD), retorna vetor de tokens |
| `construirGramatica()` | Aluno 1 | Calcula FIRST/FOLLOW e constrói tabela LL(1) |
| `calcularFirst()` | Aluno 1 | Conjuntos FIRST iterativos |
| `calcularFollow()` | Aluno 1 | Conjuntos FOLLOW iterativos |
| `construirTabelaLL1()` | Aluno 1 | Tabela de análise LL(1) sem conflitos |
| `parsear(tokens, gramatica)` | Aluno 2 | Parser LL(1) descendente recursivo |
| `gerarArvore(derivacao)` | Aluno 4 | Converte derivação em árvore sintática |
| `gerarAssembly(arvore)` | Aluno 4 | Gera Assembly ARMv7 VFP a partir da árvore |
| `main()` | Aluno 4 | Interface de linha de comando e integração |

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
python AnalisadorSintatico.py teste1.txt
```

O programa imprime no terminal:
1. A árvore sintática em formato visual
2. O código Assembly gerado

Mensagens de erro incluem o número de linha e descrição:
- **Erro léxico** (`ValueError`): caractere inválido, número malformado, operador incompleto
- **Erro sintático** (`SyntaxError`): token inesperado com lista de tokens esperados
