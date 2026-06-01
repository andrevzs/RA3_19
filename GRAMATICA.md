# Gramática Atribuída LL(1) — Fase 3

## 1. Convenções

- Não-terminais em **letras minúsculas**; Terminais em **MAIÚSCULAS**.
- `ε` = épsilon (palavra vazia); `$` = EOF.
- Atributos semânticos:
  - `.tipo` — tipo inferido do nó (`int`, `real`, `bool`, `unknown`, ou `None` para comandos sem valor de retorno).
  - `.codigo` — fragmento de código Assembly ARMv7 gerado para o nó.
  - `Γ` — contexto de tipos (tabela de símbolos, mapeamento `nome → {tipo, linha_def, linhas_uso}`).
- Ações semânticas aparecem entre chaves `{ }` imediatamente após o símbolo ao qual se aplicam.

---

## 2. Regras de Produção com Ações Semânticas

### 2.1 `programa`

```
programa → stmt_list $
    { programa.tipo   := None
      programa.codigo := stmt_list.codigo }
```

---

### 2.2 `stmt_list`

```
stmt_list → stmt stmt_list
    { stmt_list.tipo   := None
      stmt_list.codigo := stmt.codigo ++ stmt_list₁.codigo }

stmt_list → ε
    { stmt_list.tipo   := None
      stmt_list.codigo := "" }
```

---

### 2.3 `stmt`

```
stmt → LP stmt_inner RP
    { stmt.tipo   := stmt_inner.tipo
      stmt.codigo := stmt_inner.codigo }
```

---

### 2.4 `stmt_inner`

```
stmt_inner → START
    { stmt_inner.tipo   := None
      stmt_inner.codigo := "@ START\n" }

stmt_inner → END
    { stmt_inner.tipo   := None
      stmt_inner.codigo := "@ END\n" }

stmt_inner → IF stmt_cond stmt_true opt_else
    { verificar: stmt_cond.tipo = bool
                 se stmt_cond.tipo ≠ bool → ERRO semântico "condição do IF deve ser bool"
      stmt_inner.tipo   := None
      stmt_inner.codigo := stmt_cond.codigo
                        ++ gerar_branch_condicional(label_else, label_fim)
                        ++ stmt_true.codigo
                        ++ gerar_branch(label_fim)
                        ++ label_else ++ ":"
                        ++ opt_else.codigo
                        ++ label_fim ++ ":" }

stmt_inner → WHILE stmt_cond stmt_body
    { verificar: stmt_cond.tipo = bool
                 se stmt_cond.tipo ≠ bool → ERRO semântico "condição do WHILE deve ser bool"
      stmt_inner.tipo   := None
      stmt_inner.codigo := label_loop ++ ":"
                        ++ stmt_cond.codigo
                        ++ gerar_branch_saida(label_fim)
                        ++ stmt_body.codigo
                        ++ "B " ++ label_loop
                        ++ label_fim ++ ":" }

stmt_inner → NUM_INT num_int_cont
    { stmt_inner.tipo   := num_int_cont.tipo_result(base=int)
      stmt_inner.codigo := num_int_cont.codigo(base_val=NUM_INT.valor) }

stmt_inner → NUM_REAL num_real_cont
    { stmt_inner.tipo   := num_real_cont.tipo_result(base=real)
      stmt_inner.codigo := num_real_cont.codigo(base_val=NUM_REAL.valor) }

stmt_inner → ID id_cont
    { t1 := Γ(ID.valor).tipo    @ busca na tabela de símbolos
      stmt_inner.tipo   := id_cont.tipo_result(t1)
      stmt_inner.codigo := id_cont.codigo(ID.valor, t1) }

stmt_inner → LP stmt_inner_aninhado RP nested_cont
    { t1 := stmt_inner_aninhado.tipo
      stmt_inner.tipo   := nested_cont.tipo_result(t1)
      stmt_inner.codigo := stmt_inner_aninhado.codigo
                        ++ nested_cont.codigo(t1) }
```

---

### 2.5 `opt_else`

```
opt_else → stmt
    { opt_else.tipo   := stmt.tipo
      opt_else.codigo := stmt.codigo }

opt_else → ε
    { opt_else.tipo   := None
      opt_else.codigo := "" }
```

---

### 2.6 `num_int_cont`

```
num_int_cont → RES
    { num_int_cont.tipo_result(base) := unknown
      num_int_cont.codigo(v)         := gerar_load_res(n=v) }

num_int_cont → ID after_id_first_arg
    { se after_id_first_arg.tem_operador:
          t2 := Γ(ID.valor).tipo
          verificar_uso(ID.valor, Γ)
          num_int_cont.tipo_result(base) := tipo_op(base, t2, after_id_first_arg.op)
      senão:                              @ padrão STORE: (V MEM)
          verificar: ID.valor ∉ {TRUE, FALSE}
          registrar_definicao(ID.valor, tipo=base, Γ)
          num_int_cont.tipo_result(base) := None
      num_int_cont.codigo(v) := gerar_store_ou_op(v, ID.valor, after_id_first_arg) }

num_int_cont → NUM_INT any_op
    { t2 := int
      num_int_cont.tipo_result(base) := tipo_op(base, t2, any_op.op)
      num_int_cont.codigo(v)         := gerar_op(v, NUM_INT.valor, any_op.op) }

num_int_cont → NUM_REAL any_op
    { t2 := real
      num_int_cont.tipo_result(base) := tipo_op(base, t2, any_op.op)
      num_int_cont.codigo(v)         := gerar_op(v, NUM_REAL.valor, any_op.op) }

num_int_cont → LP stmt_inner RP any_op
    { t2 := stmt_inner.tipo
      num_int_cont.tipo_result(base) := tipo_op(base, t2, any_op.op)
      num_int_cont.codigo(v)         := stmt_inner.codigo
                                     ++ gerar_op_com_resultado(v, any_op.op) }
```

---

### 2.7 `after_id_first_arg`

```
after_id_first_arg → ε
    { after_id_first_arg.tem_operador := false
      after_id_first_arg.op          := None
      after_id_first_arg.codigo      := "" }

after_id_first_arg → any_op
    { after_id_first_arg.tem_operador := true
      after_id_first_arg.op          := any_op.op
      after_id_first_arg.codigo      := any_op.codigo }
```

---

### 2.8 `num_real_cont`

```
num_real_cont → ID after_id_first_arg
    { (mesma lógica de num_int_cont → ID after_id_first_arg, base=real) }

num_real_cont → NUM_INT any_op
    { t2 := int
      num_real_cont.tipo_result(base) := tipo_op(base, t2, any_op.op) }

num_real_cont → NUM_REAL any_op
    { t2 := real
      num_real_cont.tipo_result(base) := tipo_op(base, t2, any_op.op) }

num_real_cont → LP stmt_inner RP any_op
    { t2 := stmt_inner.tipo
      num_real_cont.tipo_result(base) := tipo_op(base, t2, any_op.op) }
```

---

### 2.9 `id_cont`

```
id_cont → ε
    { @ padrão LOAD: (MEM)
      id_cont.tipo_result(t1) := t1
      id_cont.codigo(nome, t1) := gerar_load(nome) }

id_cont → NUM_INT any_op
    { t2 := int
      id_cont.tipo_result(t1) := tipo_op(t1, t2, any_op.op)
      id_cont.codigo(nome, t1) := gerar_op(nome, NUM_INT.valor, any_op.op) }

id_cont → NUM_REAL any_op
    { t2 := real
      id_cont.tipo_result(t1) := tipo_op(t1, t2, any_op.op)
      id_cont.codigo(nome, t1) := gerar_op(nome, NUM_REAL.valor, any_op.op) }

id_cont → ID any_op
    { t2 := Γ(ID.valor).tipo
      verificar_uso(ID.valor, Γ)
      id_cont.tipo_result(t1) := tipo_op(t1, t2, any_op.op)
      id_cont.codigo(nome, t1) := gerar_op(nome, ID.valor, any_op.op) }

id_cont → LP stmt_inner RP any_op
    { t2 := stmt_inner.tipo
      id_cont.tipo_result(t1) := tipo_op(t1, t2, any_op.op)
      id_cont.codigo(nome, t1) := gerar_load(nome)
                               ++ stmt_inner.codigo
                               ++ gerar_op_resultado(any_op.op) }
```

---

### 2.10 `nested_cont`

```
nested_cont → ε
    { nested_cont.tipo_result(t1) := t1
      nested_cont.codigo(t1)      := "" }

nested_cont → NUM_INT any_op
    { t2 := int
      nested_cont.tipo_result(t1) := tipo_op(t1, t2, any_op.op)
      nested_cont.codigo(t1)      := gerar_op_resultado_imediato(NUM_INT.valor, any_op.op) }

nested_cont → NUM_REAL any_op
    { t2 := real
      nested_cont.tipo_result(t1) := tipo_op(t1, t2, any_op.op)
      nested_cont.codigo(t1)      := gerar_op_resultado_imediato(NUM_REAL.valor, any_op.op) }

nested_cont → ID after_id_nested
    { se after_id_nested.tem_operador:
          t2 := Γ(ID.valor).tipo
          verificar_uso(ID.valor, Γ)
          nested_cont.tipo_result(t1) := tipo_op(t1, t2, after_id_nested.op)
      senão:                            @ padrão STORE: ((expr) MEM)
          verificar: ID.valor ∉ {TRUE, FALSE}
          registrar_definicao(ID.valor, tipo=unknown, Γ)
          nested_cont.tipo_result(t1) := None
      nested_cont.codigo(t1) := gerar_store_ou_op_resultado(ID.valor, after_id_nested) }

nested_cont → LP stmt_inner RP any_op
    { t2 := stmt_inner.tipo
      nested_cont.tipo_result(t1) := tipo_op(t1, t2, any_op.op)
      nested_cont.codigo(t1)      := stmt_inner.codigo
                                  ++ gerar_op_resultado(any_op.op) }
```

---

### 2.11 `after_id_nested`

```
after_id_nested → ε
    { after_id_nested.tem_operador := false
      after_id_nested.op          := None }

after_id_nested → any_op
    { after_id_nested.tem_operador := true
      after_id_nested.op          := any_op.op }
```

---

### 2.12 `any_op`, `arith_op`, `rel_op`

```
any_op → arith_op
    { any_op.op := arith_op.op }

any_op → rel_op
    { any_op.op := rel_op.op }

arith_op → OP_ADD  { arith_op.op := '+' }
arith_op → OP_SUB  { arith_op.op := '-' }
arith_op → OP_MUL  { arith_op.op := '*' }
arith_op → OP_RDIV { arith_op.op := '|' }
arith_op → OP_IDIV { arith_op.op := '/' }
arith_op → OP_MOD  { arith_op.op := '%' }
arith_op → OP_POW  { arith_op.op := '^' }

rel_op → OP_GT   { rel_op.op := '>'  }
rel_op → OP_LT   { rel_op.op := '<'  }
rel_op → OP_EQ   { rel_op.op := '==' }
rel_op → OP_NEQ  { rel_op.op := '!=' }
rel_op → OP_GTE  { rel_op.op := '>=' }
rel_op → OP_LTE  { rel_op.op := '<=' }
```

---

### 2.13 Função auxiliar `tipo_op`

Usada pelas ações semânticas acima para calcular o tipo resultante de `(e₁ op e₂)`:

```
tipo_op(t1, t2, op):
  se op ∈ {>, <, ==, !=, >=, <=}:
      se t1 = bool ou t2 = bool → ERRO "operador relacional não pode operar com bool"
      retorna bool
  se op = '/':
      se t1 ∉ {int, unknown} ou t2 ∉ {int, unknown} → ERRO "divisão inteira requer int"
      retorna int
  se op = '%':
      se t1 ∉ {int, unknown} ou t2 ∉ {int, unknown} → ERRO "resto requer int"
      retorna int
  se op = '|':
      se t1 = bool ou t2 = bool → ERRO "operação '|' não suportada com bool"
      retorna real
  se op ∈ {+, -, *, ^}:
      se t1 = bool ou t2 = bool → ERRO "operação não suportada com bool"
      se t1 = real ou t2 = real → retorna real
      se t1 = unknown ou t2 = unknown → retorna unknown
      retorna int
```

---

## 3. Conjuntos FIRST

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
| `after_id_first_arg` | { OP_ADD, OP_SUB, OP_MUL, OP_RDIV, OP_IDIV, OP_MOD, OP_POW, OP_GT, OP_LT, OP_EQ, OP_NEQ, OP_GTE, OP_LTE, ε } |
| `after_id_nested` | { OP_ADD, OP_SUB, OP_MUL, OP_RDIV, OP_IDIV, OP_MOD, OP_POW, OP_GT, OP_LT, OP_EQ, OP_NEQ, OP_GTE, OP_LTE, ε } |
| `any_op` | { OP_ADD, OP_SUB, OP_MUL, OP_RDIV, OP_IDIV, OP_MOD, OP_POW, OP_GT, OP_LT, OP_EQ, OP_NEQ, OP_GTE, OP_LTE } |
| `arith_op` | { OP_ADD, OP_SUB, OP_MUL, OP_RDIV, OP_IDIV, OP_MOD, OP_POW } |
| `rel_op` | { OP_GT, OP_LT, OP_EQ, OP_NEQ, OP_GTE, OP_LTE } |

---

## 4. Conjuntos FOLLOW

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

## 5. Tabela de Análise LL(1)

A tabela é construída automaticamente pela função `construirGramatica()` em `AnalisadorSintatico.py`.  
Cada par `(não-terminal, terminal)` mapeia para no máximo uma produção — ausência de conflitos verificada em tempo de execução.

| Não-terminal | Terminal | Produção |
|---|---|---|
| `programa` | LP | `stmt_list $` |
| `programa` | EOF | `stmt_list $` |
| `stmt_list` | LP | `stmt stmt_list` |
| `stmt_list` | EOF | `ε` |
| `stmt_list` | RP | `ε` |
| `stmt` | LP | `LP stmt_inner RP` |
| `stmt_inner` | KW_START | `START` |
| `stmt_inner` | KW_END | `END` |
| `stmt_inner` | KW_IF | `IF stmt stmt opt_else` |
| `stmt_inner` | KW_WHILE | `WHILE stmt stmt` |
| `stmt_inner` | NUM_INT | `NUM_INT num_int_cont` |
| `stmt_inner` | NUM_REAL | `NUM_REAL num_real_cont` |
| `stmt_inner` | ID | `ID id_cont` |
| `stmt_inner` | LP | `LP stmt_inner RP nested_cont` |
| `opt_else` | LP | `stmt` |
| `opt_else` | RP | `ε` |
| `num_int_cont` | KW_RES | `RES` |
| `num_int_cont` | ID | `ID after_id_first_arg` |
| `num_int_cont` | NUM_INT | `NUM_INT any_op` |
| `num_int_cont` | NUM_REAL | `NUM_REAL any_op` |
| `num_int_cont` | LP | `LP stmt_inner RP any_op` |
| `after_id_first_arg` | RP | `ε` |
| `after_id_first_arg` | OP_ADD..OP_POW | `any_op` |
| `after_id_first_arg` | OP_GT..OP_LTE | `any_op` |
| `num_real_cont` | ID | `ID after_id_first_arg` |
| `num_real_cont` | NUM_INT | `NUM_INT any_op` |
| `num_real_cont` | NUM_REAL | `NUM_REAL any_op` |
| `num_real_cont` | LP | `LP stmt_inner RP any_op` |
| `id_cont` | RP | `ε` |
| `id_cont` | NUM_INT | `NUM_INT any_op` |
| `id_cont` | NUM_REAL | `NUM_REAL any_op` |
| `id_cont` | ID | `ID any_op` |
| `id_cont` | LP | `LP stmt_inner RP any_op` |
| `nested_cont` | RP | `ε` |
| `nested_cont` | NUM_INT | `NUM_INT any_op` |
| `nested_cont` | NUM_REAL | `NUM_REAL any_op` |
| `nested_cont` | ID | `ID after_id_nested` |
| `nested_cont` | LP | `LP stmt_inner RP any_op` |
| `after_id_nested` | RP | `ε` |
| `after_id_nested` | OP_ADD..OP_LTE | `any_op` |
| `any_op` | OP_ADD..OP_POW | `arith_op` |
| `any_op` | OP_GT..OP_LTE | `rel_op` |
| `arith_op` | OP_ADD | `OP_ADD` |
| `arith_op` | OP_SUB | `OP_SUB` |
| `arith_op` | OP_MUL | `OP_MUL` |
| `arith_op` | OP_RDIV | `OP_RDIV` |
| `arith_op` | OP_IDIV | `OP_IDIV` |
| `arith_op` | OP_MOD | `OP_MOD` |
| `arith_op` | OP_POW | `OP_POW` |
| `rel_op` | OP_GT | `OP_GT` |
| `rel_op` | OP_LT | `OP_LT` |
| `rel_op` | OP_EQ | `OP_EQ` |
| `rel_op` | OP_NEQ | `OP_NEQ` |
| `rel_op` | OP_GTE | `OP_GTE` |
| `rel_op` | OP_LTE | `OP_LTE` |

> **Verificação**: a tabela não possui conflitos. Cada par `(NT, terminal)` mapeia para no máximo uma produção. Verificado automaticamente por `construirGramatica()`, que levanta `ValueError` em caso de conflito.

---

## 6. Árvore Sintática — `teste1.txt`

Gerada pela última execução (`python AnalisadorSemantico.py teste1.txt`).  
A versão completa com anotações semânticas está em `arvore_atribuida.json`.

Trecho representativo (primeiros statements):

```
programa                                           [tipo: None]
└── stmt_list
    ├── stmt                  → (START)             [tipo: None]
    │   └── stmt_inner
    │       └── KW_START: 'START'
    └── stmt_list
        ├── stmt              → (3.14 2.0 +)        [tipo: real]
        │   └── stmt_inner
        │       ├── NUM_REAL: '3.14'
        │       └── num_real_cont
        │           ├── NUM_REAL: '2.0'
        │           └── arith_op
        │               └── OP_ADD: '+'
        └── stmt_list
            ├── stmt          → ((3.0 4.0 *) (2.0 1.0 +) +)   [tipo: real]
            │   └── stmt_inner
            │       ├── LP: '('
            │       ├── stmt_inner                  [tipo: real]
            │       │   ├── NUM_REAL: '3.0'
            │       │   └── num_real_cont
            │       │       ├── NUM_REAL: '4.0'
            │       │       └── arith_op → OP_MUL: '*'
            │       ├── RP: ')'
            │       └── nested_cont
            │           ├── LP: '('
            │           ├── stmt_inner              [tipo: real]
            │           │   ├── NUM_REAL: '2.0'
            │           │   └── num_real_cont
            │           │       ├── NUM_REAL: '1.0'
            │           │       └── arith_op → OP_ADD: '+'
            │           ├── RP: ')'
            │           └── any_op → arith_op → OP_ADD: '+'
            └── ...
```

A árvore completa da última execução (com anotações de tipo semântico e categoria) está em `arvore_atribuida.json`.
