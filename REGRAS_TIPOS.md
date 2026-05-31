# Sistema de Regras de Validação de Tipos — Fase 3

**Grupo:** RA3\_19  
**Aluno responsável:** Aluno 3

---

## 1. Notação

Usamos julgamentos de tipagem na forma:

```
Γ ⊢ e : τ
```

onde:

- **Γ** (gama) é o contexto de tipos — a tabela de símbolos que mapeia cada variável ao seu tipo declarado: `Γ = { x₁ : τ₁, x₂ : τ₂, … }`
- **e** é uma expressão ou comando da linguagem RPN
- **τ** é o tipo inferido, um elemento de `{ int, real, bool, unknown }`

Uma linha horizontal separa premissas (acima) de conclusão (abaixo). O nome da regra aparece à direita.

---

## 2. Tipos da Linguagem

| Tipo      | Descrição                                    | Exemplo de literal |
|-----------|----------------------------------------------|--------------------|
| `int`     | Inteiro de precisão arbitrária               | `42`, `0`, `7`     |
| `real`    | Ponto flutuante duplo IEEE 754               | `3.14`, `0.0`      |
| `bool`    | Valor lógico — produzido por operadores relacionais ou pelos literais `TRUE`/`FALSE` | `TRUE`, `FALSE` |
| `unknown` | Tipo não inferível estaticamente             | resultado de `(N RES)` |

---

## 3. Regras para Literais

```
                                          (T-INT)
────────────────────
Γ ⊢ n : int          (n é um literal NUM_INT)


                                          (T-REAL)
────────────────────
Γ ⊢ v : real         (v é um literal NUM_REAL)


                                          (T-TRUE)
────────────────────
Γ ⊢ TRUE : bool


                                          (T-FALSE)
────────────────────
Γ ⊢ FALSE : bool
```

---

## 4. Regras para Variáveis (LOAD e STORE)

```
Γ(x) = τ                                 (T-LOAD)
──────────────────
Γ ⊢ (x) : τ          (lê variável x da tabela)


Γ ⊢ e : τ    x ∉ {TRUE, FALSE}          (T-STORE)
──────────────────────────────────
Γ, x : τ ⊢ (e x) : τ    (armazena e em x; não produz valor de saída)
```

---

## 5. Regra para RES

O tipo do resultado de `N` comandos atrás não é determinável estaticamente:

```
n ∈ ℕ    n ≤ |stmts anteriores|          (T-RES)
───────────────────────────────
Γ ⊢ (n RES) : unknown
```

Expressões com `unknown` propagam o tipo sem gerar erros adicionais.

---

## 6. Regras para Operadores Aritméticos

### 6.1 Adição, Subtração, Multiplicação, Potenciação (`+`, `-`, `*`, `^`)

Promoção numérica: `int` com `real` resulta em `real`. Operandos `bool` são inválidos.

```
Γ ⊢ e₁ : int    Γ ⊢ e₂ : int            (T-ARITH-INT)
──────────────────────────────
Γ ⊢ (e₁ e₂ ⊕) : int          ⊕ ∈ { +, -, *, ^ }


Γ ⊢ e₁ : τ₁    Γ ⊢ e₂ : τ₂             (T-ARITH-REAL)
τ₁ ∈ {int, real}    τ₂ ∈ {int, real}
(τ₁ = real) ∨ (τ₂ = real)
──────────────────────────────
Γ ⊢ (e₁ e₂ ⊕) : real         ⊕ ∈ { +, -, *, ^ }
```

**Erro** se `τ₁ = bool` ou `τ₂ = bool`:

```
Γ ⊢ e₁ : τ₁    Γ ⊢ e₂ : τ₂             (T-ARITH-ERRO)
(τ₁ = bool) ∨ (τ₂ = bool)
──────────────────────────────
ERRO: "operação '⊕' não suportada com tipo bool"
```

### 6.2 Divisão Real (`|`)

```
Γ ⊢ e₁ : τ₁    Γ ⊢ e₂ : τ₂             (T-RDIV)
τ₁ ∈ {int, real, unknown}
τ₂ ∈ {int, real, unknown}
──────────────────────────────
Γ ⊢ (e₁ e₂ |) : real
```

**Erro** se `τ₁ = bool` ou `τ₂ = bool`:

```
Γ ⊢ e₁ : τ₁    Γ ⊢ e₂ : τ₂             (T-RDIV-ERRO)
(τ₁ = bool) ∨ (τ₂ = bool)
──────────────────────────────
ERRO: "operação '|' não suportada com tipo bool"
```

### 6.3 Divisão Inteira (`/`)

Ambos os operandos devem ser `int` (ou `unknown`, tolerado por propagação):

```
Γ ⊢ e₁ : int    Γ ⊢ e₂ : int            (T-IDIV)
──────────────────────────────
Γ ⊢ (e₁ e₂ /) : int


Γ ⊢ e₁ : τ₁    Γ ⊢ e₂ : τ₂             (T-IDIV-ERRO)
(τ₁ ∉ {int, unknown}) ∨ (τ₂ ∉ {int, unknown})
──────────────────────────────
ERRO: "divisão inteira '/' requer tipo int"
```

### 6.4 Resto (`%`)

Mesma restrição que divisão inteira:

```
Γ ⊢ e₁ : int    Γ ⊢ e₂ : int            (T-MOD)
──────────────────────────────
Γ ⊢ (e₁ e₂ %) : int


Γ ⊢ e₁ : τ₁    Γ ⊢ e₂ : τ₂             (T-MOD-ERRO)
(τ₁ ∉ {int, unknown}) ∨ (τ₂ ∉ {int, unknown})
──────────────────────────────
ERRO: "resto '%' requer tipo int"
```

---

## 7. Regras para Operadores Relacionais

Operadores relacionais (`>`, `<`, `==`, `!=`, `>=`, `<=`) aceitam operandos numéricos e produzem `bool`. Operandos do tipo `bool` são inválidos.

```
Γ ⊢ e₁ : τ₁    Γ ⊢ e₂ : τ₂             (T-REL)
τ₁ ∈ {int, real, unknown}
τ₂ ∈ {int, real, unknown}
──────────────────────────────
Γ ⊢ (e₁ e₂ ⊙) : bool        ⊙ ∈ { >, <, ==, !=, >=, <= }


Γ ⊢ e₁ : τ₁    Γ ⊢ e₂ : τ₂             (T-REL-ERRO)
(τ₁ = bool) ∨ (τ₂ = bool)
──────────────────────────────
ERRO: "operador relacional '⊙' não pode operar com tipo bool"
```

---

## 8. Regras para Literais Lógicos e Tipo `bool`

Os únicos literais do tipo `bool` são `TRUE` e `FALSE` (regras T-TRUE e T-FALSE).  
O tipo `bool` também é produzido por qualquer operador relacional (regra T-REL).  
Não existem operadores lógicos binários (AND, OR) ou unário (NOT) na linguagem — a composição lógica é feita pelo aninhamento de estruturas de controle.

---

## 9. Regras para Estruturas de Controle

### 9.1 Decisão — IF sem else

```
Γ ⊢ c : bool                             (T-IF)
Γ ⊢ s_true : τ_true
──────────────────────────────
Γ ⊢ (IF c s_true) : ∅        (comando, sem tipo de resultado)


Γ ⊢ c : τ_c    τ_c ≠ bool               (T-IF-ERRO)
──────────────────────────────
ERRO: "condição do IF deve ser bool (obteve 'τ_c')"
```

### 9.2 Decisão — IF com else

```
Γ ⊢ c : bool                             (T-IF-ELSE)
Γ ⊢ s_true : τ_true
Γ ⊢ s_false : τ_false
──────────────────────────────
Γ ⊢ (IF c s_true s_false) : ∅
```

### 9.3 Repetição — WHILE

```
Γ ⊢ c : bool                             (T-WHILE)
Γ ⊢ s_body : τ_body
──────────────────────────────
Γ ⊢ (WHILE c s_body) : ∅


Γ ⊢ c : τ_c    τ_c ≠ bool               (T-WHILE-ERRO)
──────────────────────────────
ERRO: "condição do WHILE deve ser bool (obteve 'τ_c')"
```

---

## 10. Regra de Propagação de `unknown`

Quando um dos operandos tem tipo `unknown` e não viola as restrições da operação (ex.: não é `bool` onde bool é proibido), o resultado é inferido pelo tipo do outro operando ou `unknown`:

```
Γ ⊢ e₁ : unknown    Γ ⊢ e₂ : τ₂        (T-UNKNOWN-PROP)
τ₂ ≠ bool
──────────────────────────────
Γ ⊢ (e₁ e₂ ⊕) : τ₂    se τ₂ ∈ {int, real}
Γ ⊢ (e₁ e₂ ⊕) : unknown    se τ₂ = unknown
```

Nenhum erro adicional é gerado para `unknown` — o erro de declaração já foi reportado pelo Aluno 2.

---

## 11. Tabela de Compatibilidade Resumida

| Operação | τ₁ | τ₂ | τ resultado | Válido? |
|---|---|---|---|---|
| `+` `-` `*` `^` | int | int | int | ✅ |
| `+` `-` `*` `^` | int ou real | real | real | ✅ |
| `+` `-` `*` `^` | bool | qualquer | — | ❌ |
| `\|` | int ou real | int ou real | real | ✅ |
| `\|` | bool | qualquer | — | ❌ |
| `/` | int | int | int | ✅ |
| `/` | real ou bool | qualquer | — | ❌ |
| `%` | int | int | int | ✅ |
| `%` | real ou bool | qualquer | — | ❌ |
| `>` `<` `==` `!=` `>=` `<=` | int ou real | int ou real | bool | ✅ |
| `>` `<` `==` `!=` `>=` `<=` | bool | qualquer | — | ❌ |
| `(IF c …)` | — | — | — | ✅ se c : bool |
| `(WHILE c …)` | — | — | — | ✅ se c : bool |
