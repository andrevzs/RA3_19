# Gramática LL(1) — Fase 2

## 1. Regras de Produção

Convenções: não-terminais em minúsculo, terminais em MAIÚSCULO, `ε` = epsilon, `$` = EOF.

```
programa         → stmt_list $

stmt_list        → stmt stmt_list
stmt_list        → ε

stmt             → ( stmt_inner )

stmt_inner       → START
stmt_inner       → END
stmt_inner       → IF stmt stmt opt_else
stmt_inner       → WHILE stmt stmt
stmt_inner       → NUM_INT num_int_cont
stmt_inner       → NUM_REAL num_real_cont
stmt_inner       → ID id_cont
stmt_inner       → ( stmt_inner ) nested_cont

opt_else         → stmt
opt_else         → ε

num_int_cont     → RES
num_int_cont     → ID after_id_first_arg
num_int_cont     → NUM_INT arith_op
num_int_cont     → NUM_REAL arith_op
num_int_cont     → ( stmt_inner ) arith_op

after_id_first_arg  → ε
after_id_first_arg  → arith_op

num_real_cont    → ID after_id_first_arg
num_real_cont    → NUM_INT arith_op
num_real_cont    → NUM_REAL arith_op
num_real_cont    → ( stmt_inner ) arith_op

id_cont          → ε
id_cont          → NUM_INT any_op
id_cont          → NUM_REAL any_op
id_cont          → ID any_op
id_cont          → ( stmt_inner ) any_op

nested_cont      → ε
nested_cont      → NUM_INT any_op
nested_cont      → NUM_REAL any_op
nested_cont      → ID after_id_nested
nested_cont      → ( stmt_inner ) any_op

after_id_nested  → ε
after_id_nested  → any_op

any_op           → arith_op
any_op           → rel_op

arith_op         → +  |  -  |  *  |  |  |  /  |  %  |  ^

rel_op           → >  |  <  |  ==  |  !=  |  >=  |  <=
```

### Sintaxe das Estruturas de Controle

A sintaxe usa **keyword prefixada** dentro dos parênteses:

| Estrutura | Sintaxe | Exemplo |
|-----------|---------|---------|
| Decisão (sem else) | `(IF cond true_stmt)` | `(IF (X 0 >) (X X))` |
| Decisão (com else)  | `(IF cond true_stmt false_stmt)` | `(IF (X 0 >) (1.0 R) (0.0 R))` |
| Laço               | `(WHILE cond body_stmt)` | `(WHILE (I 10 <) ((I 1 +) I))` |

- `cond` é um stmt RPN cuja avaliação produz 1.0 (verdadeiro) ou 0.0 (falso).
- Os operadores relacionais (`>`, `<`, `==`, `!=`, `>=`, `<=`) produzem booleano duplo.
- `true_stmt` e `false_stmt` são stmts RPN normais (expressões ou STORE).
- Aninhamento ilimitado de estruturas de controle.

---

## 2. Conjuntos FIRST

| Não-terminal | FIRST |
|---|---|
| `programa` | { LP, EOF } |
| `stmt_list` | { LP, ε } |
| `stmt` | { LP } |
| `stmt_inner` | { KW_START, KW_END, KW_IF, KW_WHILE, NUM_INT, NUM_REAL, ID, LP } |
| `opt_else` | { LP, ε } |
| `num_int_cont` | { KW_RES, ID, NUM_INT, NUM_REAL, LP } |
| `num_real_cont` | { ID, NUM_INT, NUM_REAL, LP } |
| `id_cont` | { NUM_INT, NUM_REAL, ID, LP, ε } |
| `nested_cont` | { NUM_INT, NUM_REAL, ID, LP, ε } |
| `after_id_first_arg` | { OP_ADD, OP_SUB, OP_MUL, OP_RDIV, OP_IDIV, OP_MOD, OP_POW, ε } |
| `after_id_nested` | { OP_ADD, OP_SUB, OP_MUL, OP_RDIV, OP_IDIV, OP_MOD, OP_POW, OP_GT, OP_LT, OP_EQ, OP_NEQ, OP_GTE, OP_LTE, ε } |
| `any_op` | { OP_ADD, OP_SUB, OP_MUL, OP_RDIV, OP_IDIV, OP_MOD, OP_POW, OP_GT, OP_LT, OP_EQ, OP_NEQ, OP_GTE, OP_LTE } |
| `arith_op` | { OP_ADD, OP_SUB, OP_MUL, OP_RDIV, OP_IDIV, OP_MOD, OP_POW } |
| `rel_op` | { OP_GT, OP_LT, OP_EQ, OP_NEQ, OP_GTE, OP_LTE } |

---

## 3. Conjuntos FOLLOW

| Não-terminal | FOLLOW |
|---|---|
| `programa` | { EOF } |
| `stmt_list` | { EOF } |
| `stmt` | { LP, RP, EOF } |
| `stmt_inner` | { RP } |
| `opt_else` | { RP } |
| `num_int_cont` | { RP } |
| `num_real_cont` | { RP } |
| `id_cont` | { RP } |
| `nested_cont` | { RP } |
| `after_id_first_arg` | { RP } |
| `after_id_nested` | { RP } |
| `any_op` | { RP } |
| `arith_op` | { RP } |
| `rel_op` | { RP } |

---

## 4. Tabela de Análise LL(1)

A tabela é construída automaticamente pelo programa (função `construirGramatica()`).
Cada linha da tabela é da forma `[não-terminal, terminal] → produção`.

Entradas relevantes:

| Não-terminal | Terminal | Produção |
|---|---|---|
| `programa` | LP | `stmt_list $` |
| `programa` | EOF | `stmt_list $` |
| `stmt_list` | LP | `stmt stmt_list` |
| `stmt_list` | EOF | `ε` |
| `stmt` | LP | `( stmt_inner )` |
| `stmt_inner` | KW_START | `START` |
| `stmt_inner` | KW_END | `END` |
| `stmt_inner` | KW_IF | `IF stmt stmt opt_else` |
| `stmt_inner` | KW_WHILE | `WHILE stmt stmt` |
| `stmt_inner` | NUM_INT | `NUM_INT num_int_cont` |
| `stmt_inner` | NUM_REAL | `NUM_REAL num_real_cont` |
| `stmt_inner` | ID | `ID id_cont` |
| `stmt_inner` | LP | `( stmt_inner ) nested_cont` |
| `opt_else` | LP | `stmt` |
| `opt_else` | RP | `ε` |
| `num_int_cont` | KW_RES | `RES` |
| `num_int_cont` | ID | `ID after_id_first_arg` |
| `num_int_cont` | NUM_INT | `NUM_INT arith_op` |
| `num_int_cont` | NUM_REAL | `NUM_REAL arith_op` |
| `num_int_cont` | LP | `( stmt_inner ) arith_op` |
| `after_id_first_arg` | RP | `ε` |
| `after_id_first_arg` | OP_ADD..OP_POW | `arith_op` |
| `id_cont` | RP | `ε` |
| `id_cont` | NUM_INT | `NUM_INT any_op` |
| `id_cont` | NUM_REAL | `NUM_REAL any_op` |
| `id_cont` | ID | `ID any_op` |
| `id_cont` | LP | `( stmt_inner ) any_op` |
| `nested_cont` | RP | `ε` |
| `nested_cont` | NUM_INT | `NUM_INT any_op` |
| `nested_cont` | NUM_REAL | `NUM_REAL any_op` |
| `nested_cont` | ID | `ID after_id_nested` |
| `nested_cont` | LP | `( stmt_inner ) any_op` |
| `after_id_nested` | RP | `ε` |
| `after_id_nested` | OP_ADD..OP_LTE | `any_op` |
| `any_op` | OP_ADD..OP_POW | `arith_op` |
| `any_op` | OP_GT..OP_LTE | `rel_op` |
| `arith_op` | OP_ADD | `+` |
| `arith_op` | OP_SUB | `-` |
| `arith_op` | OP_MUL | `*` |
| `arith_op` | OP_RDIV | `\|` |
| `arith_op` | OP_IDIV | `/` |
| `arith_op` | OP_MOD | `%` |
| `arith_op` | OP_POW | `^` |
| `rel_op` | OP_GT | `>` |
| `rel_op` | OP_LT | `<` |
| `rel_op` | OP_EQ | `==` |
| `rel_op` | OP_NEQ | `!=` |
| `rel_op` | OP_GTE | `>=` |
| `rel_op` | OP_LTE | `<=` |

> **Verificação:** a tabela não possui conflitos (cada par (NT, terminal) mapeia para no máximo uma produção). Verificado automaticamente pela função `construirGramatica()` que levanta `ValueError` em caso de conflito.

---

## 5. Árvore Sintática — `teste1.txt`

Gerada pela última execução do programa (`python AnalisadorSintatico.py teste1.txt`).
A versão completa em JSON está no arquivo `arvore.json`.

Trecho representativo (primeiros três statements):

```
programa
└── stmt_list
    ├── stmt                              → (START)
    │   ├── LP: '('
    │   ├── stmt_inner
    │   │   └── KW_START: 'START'
    │   └── RP: ')'
    └── stmt_list
        ├── stmt                          → (3.14 2.0 +)
        │   ├── LP: '('
        │   ├── stmt_inner
        │   │   ├── NUM_REAL: '3.14'
        │   │   └── num_real_cont
        │   │       ├── NUM_REAL: '2.0'
        │   │       └── arith_op
        │   │           └── OP_ADD: '+'
        │   └── RP: ')'
        └── stmt_list
            ├── stmt                      → ((3.0 4.0 *) 2.0 +)
            │   ├── LP: '('
            │   ├── stmt_inner
            │   │   ├── LP: '('
            │   │   ├── stmt_inner
            │   │   │   ├── NUM_REAL: '3.0'
            │   │   │   └── num_real_cont
            │   │   │       ├── NUM_REAL: '4.0'
            │   │   │       └── arith_op
            │   │   │           └── OP_MUL: '*'
            │   │   ├── RP: ')'
            │   │   └── nested_cont
            │   │       ├── NUM_REAL: '2.0'
            │   │       └── any_op
            │   │           └── arith_op
            │   │               └── OP_ADD: '+'
            │   └── RP: ')'
            └── stmt_list
                └── ...
```

A árvore completa da última execução está em `arvore.json`.
