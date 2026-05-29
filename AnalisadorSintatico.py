# Integrantes do grupo (ordem alfabética):
# André Vinícius Zicka Schmidt - andrevzs
# Gabriel Fischer Domakoski - fochu3013
#
# Nome do grupo no Canvas: RA3_19

import sys

# ─────────────────────────────────────────────────────────────
# Constantes para símbolos especiais da gramática
# ─────────────────────────────────────────────────────────────

EPSILON = 'EPSILON'
EOF = 'EOF'

# Mapeamento de valor literal → tipo de token (usado pela função lerTokens do Aluno 3)
MAPA_TOKENS: dict[str, str] = {
    '(':  'LP',
    ')':  'RP',
    '+':  'OP_ADD',
    '-':  'OP_SUB',
    '*':  'OP_MUL',
    '|':  'OP_RDIV',   # Fase 2: divisão real
    '/':  'OP_IDIV',   # Fase 2: divisão inteira (era // na Fase 1)
    '%':  'OP_MOD',
    '^':  'OP_POW',
    '>':  'OP_GT',
    '<':  'OP_LT',
    '==': 'OP_EQ',
    '!=': 'OP_NEQ',
    '>=': 'OP_GTE',
    '<=': 'OP_LTE',
    'RES':   'KW_RES',
    'START': 'KW_START',
    'END':   'KW_END',
    'IF':    'KW_IF',
    'WHILE': 'KW_WHILE',
}


# ─────────────────────────────────────────────────────────────
# Gramática LL(1) — Fase 2
#
# Convenções:
#   Não-terminais: letras minúsculas (ex.: stmt_inner)
#   Terminais:     letras maiúsculas (ex.: LP, NUM_INT, KW_IF)
#   EPSILON:       produção vazia (ε)
#   EOF:           fim de entrada ($)
#
# Estruturas de controle usam keyword em posição prefixada (após '(')
# para garantir determinismo LL(1). Exemplo:
#   IF:    (IF cond_stmt true_stmt [false_stmt])
#   WHILE: (WHILE cond_stmt body_stmt)
# ─────────────────────────────────────────────────────────────

def _producoes_fixas() -> dict[str, list[list[str]]]:
    """Retorna o dicionário completo de produções da gramática."""
    return {
        # Programa completo
        'programa': [
            ['stmt_list', EOF],
        ],

        # Lista de comandos (pode ser vazia)
        'stmt_list': [
            ['stmt', 'stmt_list'],
            [EPSILON],
        ],

        # Um comando: sempre envolto em parênteses
        'stmt': [
            ['LP', 'stmt_inner', 'RP'],
        ],

        # Conteúdo interno de um comando — 8 alternativas, cada uma com
        # primeiro símbolo distinto: determinismo LL(1) garantido.
        'stmt_inner': [
            ['KW_START'],                               # (START)
            ['KW_END'],                                 # (END)
            ['KW_IF', 'stmt', 'stmt', 'opt_else'],      # (IF cond true [false])
            ['KW_WHILE', 'stmt', 'stmt'],               # (WHILE cond body)
            ['NUM_INT', 'num_int_cont'],
            ['NUM_REAL', 'num_real_cont'],
            ['ID', 'id_cont'],
            ['LP', 'stmt_inner', 'RP', 'nested_cont'],  # subexpr como 1.º operando
        ],

        # Ramo else opcional do IF
        'opt_else': [
            ['stmt'],      # com else  — começa com LP ∈ FIRST(stmt)
            [EPSILON],     # sem else  — detectado por RP ∈ FOLLOW(opt_else)
        ],

        # Continuação após NUM_INT
        'num_int_cont': [
            ['KW_RES'],                              # (N RES)
            ['ID', 'after_id_first_arg'],            # (N ID) ou (N ID op)
            ['NUM_INT', 'arith_op'],                 # (N N op)
            ['NUM_REAL', 'arith_op'],                # (N V.x op)
            ['LP', 'stmt_inner', 'RP', 'arith_op'],  # (N (expr) op)
        ],

        # Após ID visto como segundo símbolo em (NUM_INT/NUM_REAL ID ...)
        # ε → STORE (N ID);   arith_op → aritmética (N ID op)
        'after_id_first_arg': [
            [EPSILON],
            ['arith_op'],
        ],

        # Continuação após NUM_REAL
        'num_real_cont': [
            ['ID', 'after_id_first_arg'],            # (V ID) ou (V ID op)
            ['NUM_INT', 'arith_op'],
            ['NUM_REAL', 'arith_op'],
            ['LP', 'stmt_inner', 'RP', 'arith_op'],
        ],

        # Continuação após ID como primeiro símbolo
        # ε → LOAD (ID);   demais → operação binária (ID operand op)
        'id_cont': [
            [EPSILON],
            ['NUM_INT', 'any_op'],
            ['NUM_REAL', 'any_op'],
            ['ID', 'any_op'],
            ['LP', 'stmt_inner', 'RP', 'any_op'],
        ],

        # Continuação após subexpressão como primeiro operando: ((expr) ...)
        # ε → wrapper simples ((expr));   ID → STORE ou aritmética; demais → aritmética
        'nested_cont': [
            [EPSILON],
            ['NUM_INT', 'any_op'],
            ['NUM_REAL', 'any_op'],
            ['ID', 'after_id_nested'],               # pode ser STORE ou aritmética
            ['LP', 'stmt_inner', 'RP', 'any_op'],
        ],

        # Após ID visto como segundo símbolo em ((expr) ID ...)
        # ε → STORE ((expr) ID);   any_op → aritmética ((expr) ID op)
        'after_id_nested': [
            [EPSILON],
            ['any_op'],
        ],

        # Operador genérico (aritmético ou relacional)
        'any_op': [
            ['arith_op'],
            ['rel_op'],
        ],

        # Operadores aritméticos
        'arith_op': [
            ['OP_ADD'],
            ['OP_SUB'],
            ['OP_MUL'],
            ['OP_RDIV'],
            ['OP_IDIV'],
            ['OP_MOD'],
            ['OP_POW'],
        ],

        # Operadores relacionais
        'rel_op': [
            ['OP_GT'],
            ['OP_LT'],
            ['OP_EQ'],
            ['OP_NEQ'],
            ['OP_GTE'],
            ['OP_LTE'],
        ],
    }


def _extrair_nao_terminais_e_terminais(
    producoes: dict[str, list[list[str]]],
) -> tuple[set[str], set[str]]:
    """Infere os conjuntos de não-terminais e terminais a partir das produções."""
    nao_terminais = set(producoes.keys())
    terminais: set[str] = set()
    for prods in producoes.values():
        for prod in prods:
            for simbolo in prod:
                if simbolo not in nao_terminais and simbolo != EPSILON:
                    terminais.add(simbolo)
    return nao_terminais, terminais


def _first_de_seq(
    seq: list[str],
    first: dict[str, set[str]],
) -> set[str]:
    """Calcula FIRST de uma sequência de símbolos usando os conjuntos já calculados."""
    resultado: set[str] = set()
    for simbolo in seq:
        simbolo_first = first.get(simbolo, {simbolo})
        resultado |= simbolo_first - {EPSILON}
        if EPSILON not in simbolo_first:
            return resultado
    resultado.add(EPSILON)
    return resultado


# ─────────────────────────────────────────────────────────────
# Funções principais — Aluno 1
# ─────────────────────────────────────────────────────────────

def calcularFirst(
    producoes: dict[str, list[list[str]]],
    nao_terminais: set[str],
) -> dict[str, set[str]]:
    """
    Calcula os conjuntos FIRST para todos os símbolos da gramática.

    Para terminais: FIRST(t) = {t}.
    Para não-terminais: algoritmo iterativo até ponto fixo.
    EPSILON é tratado como símbolo virtual (string 'EPSILON').

    Entrada:
        producoes     — dicionário de produções
        nao_terminais — conjunto de nomes de não-terminais

    Saída:
        dict mapeando cada símbolo ao seu conjunto FIRST
    """
    first: dict[str, set[str]] = {}

    # Inicializa terminais com FIRST(t) = {t}
    for prods in producoes.values():
        for prod in prods:
            for simbolo in prod:
                if simbolo not in nao_terminais and simbolo != EPSILON:
                    first[simbolo] = {simbolo}

    # Inicializa não-terminais com conjunto vazio
    for nt in nao_terminais:
        first[nt] = set()

    # Itera até ponto fixo
    alterado = True
    while alterado:
        alterado = False
        for nt, prods in producoes.items():
            for prod in prods:
                antes = len(first[nt])
                if prod == [EPSILON]:
                    first[nt].add(EPSILON)
                else:
                    first[nt] |= _first_de_seq(prod, first)
                if len(first[nt]) != antes:
                    alterado = True

    return first


def calcularFollow(
    producoes: dict[str, list[list[str]]],
    nao_terminais: set[str],
    first: dict[str, set[str]],
    simbolo_inicial: str,
) -> dict[str, set[str]]:
    """
    Calcula os conjuntos FOLLOW para todos os não-terminais.

    FOLLOW(simbolo_inicial) recebe EOF.
    Itera até ponto fixo aplicando as regras padrão de Follow.

    Entrada:
        producoes        — dicionário de produções
        nao_terminais    — conjunto de nomes de não-terminais
        first            — conjuntos FIRST já calculados
        simbolo_inicial  — não-terminal raiz da gramática

    Saída:
        dict mapeando cada não-terminal ao seu conjunto FOLLOW
    """
    follow: dict[str, set[str]] = {nt: set() for nt in nao_terminais}
    follow[simbolo_inicial].add(EOF)

    alterado = True
    while alterado:
        alterado = False
        for nt, prods in producoes.items():
            for prod in prods:
                if prod == [EPSILON]:
                    continue
                for i, simbolo in enumerate(prod):
                    if simbolo not in nao_terminais:
                        continue
                    sufixo = prod[i + 1:]
                    first_sufixo = _first_de_seq(sufixo, first) if sufixo else {EPSILON}
                    antes = len(follow[simbolo])
                    follow[simbolo] |= first_sufixo - {EPSILON}
                    if EPSILON in first_sufixo:
                        follow[simbolo] |= follow[nt]
                    if len(follow[simbolo]) != antes:
                        alterado = True

    return follow


def construirTabelaLL1(
    producoes: dict[str, list[list[str]]],
    nao_terminais: set[str],
    terminais: set[str],
    first: dict[str, set[str]],
    follow: dict[str, set[str]],
) -> dict[tuple[str, str], list[str]]:
    """
    Constrói a tabela de análise LL(1).

    Para cada produção A → α:
      - Para cada terminal a ∈ FIRST(α) − {ε}: tabela[A, a] = α
      - Se ε ∈ FIRST(α): para cada b ∈ FOLLOW(A): tabela[A, b] = α

    Levanta ValueError se detectar conflito (gramática não é LL(1)).

    Entrada:
        producoes     — dicionário de produções
        nao_terminais — conjunto de não-terminais
        terminais     — conjunto de terminais
        first         — conjuntos FIRST calculados
        follow        — conjuntos FOLLOW calculados

    Saída:
        dict com chave (não-terminal, terminal) → produção
    """
    tabela: dict[tuple[str, str], list[str]] = {}

    for nt, prods in producoes.items():
        for prod in prods:
            first_prod = {EPSILON} if prod == [EPSILON] else _first_de_seq(prod, first)

            for terminal in first_prod - {EPSILON}:
                chave = (nt, terminal)
                if chave in tabela:
                    raise ValueError(
                        f"Conflito LL(1) em [{nt}, {terminal}]: "
                        f"{tabela[chave]} vs {prod}"
                    )
                tabela[chave] = prod

            if EPSILON in first_prod:
                for terminal in follow.get(nt, set()):
                    chave = (nt, terminal)
                    if chave in tabela:
                        raise ValueError(
                            f"Conflito LL(1) em [{nt}, {terminal}]: "
                            f"{tabela[chave]} vs {prod}"
                        )
                    tabela[chave] = prod

    return tabela


def construirGramatica() -> dict:
    """
    Define a gramática LL(1) da linguagem RPN estendida (Fase 2),
    calcula FIRST e FOLLOW, e constrói a tabela de análise.

    Entrada: nenhuma (gramática é fixa).

    Saída — dicionário com as chaves:
        'producoes'       : dict[str, list[list[str]]]
        'nao_terminais'   : set[str]
        'terminais'       : set[str]
        'simbolo_inicial' : str  ('programa')
        'first'           : dict[str, set[str]]
        'follow'          : dict[str, set[str]]
        'tabela'          : dict[tuple[str, str], list[str]]
    """
    producoes = _producoes_fixas()
    nao_terminais, terminais = _extrair_nao_terminais_e_terminais(producoes)
    simbolo_inicial = 'programa'

    first = calcularFirst(producoes, nao_terminais)
    follow = calcularFollow(producoes, nao_terminais, first, simbolo_inicial)
    tabela = construirTabelaLL1(producoes, nao_terminais, terminais, first, follow)

    return {
        'producoes': producoes,
        'nao_terminais': nao_terminais,
        'terminais': terminais,
        'simbolo_inicial': simbolo_inicial,
        'first': first,
        'follow': follow,
        'tabela': tabela,
    }


# ─────────────────────────────────────────────────────────────
# Stubs — a serem implementados pelos outros alunos
# ─────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────
# Analisador léxico (AFD) — Aluno 3
#
# Cada estado é uma função que recebe (conteudo, i, linha_ref, tokens)
# e retorna a nova posição i.  linha_ref é list[int] mutável para que
# os estados possam incrementar o contador ao encontrar '\n'.
# ─────────────────────────────────────────────────────────────

# Operadores de um único caractere que não precisam de lookahead
_OPS_SIMPLES: dict[str, str] = {
    '(': 'LP', ')': 'RP',
    '+': 'OP_ADD', '-': 'OP_SUB', '*': 'OP_MUL',
    '|': 'OP_RDIV', '/': 'OP_IDIV', '%': 'OP_MOD', '^': 'OP_POW',
}


def _emit(tokens: list[dict], tipo: str, valor: str, linha: int) -> None:
    tokens.append({'tipo': tipo, 'valor': valor, 'linha': linha})


def _estado_numero(cont: str, i: int, linha_ref: list[int], tokens: list[dict]) -> int:
    """
    Estado: acumulando dígitos (inteiro ou real).
    Emite NUM_INT se não houver ponto decimal, NUM_REAL se houver exatamente um.
    """
    start = i
    tem_ponto = False
    while i < len(cont) and (cont[i].isdigit() or cont[i] == '.'):
        if cont[i] == '.':
            if tem_ponto:
                raise ValueError(
                    f"Linha {linha_ref[0]}: número inválido '{cont[start:i+1]}'"
                )
            tem_ponto = True
        i += 1
    valor = cont[start:i]
    if valor.endswith('.'):
        raise ValueError(f"Linha {linha_ref[0]}: número inválido '{valor}'")
    tipo = 'NUM_REAL' if tem_ponto else 'NUM_INT'
    _emit(tokens, tipo, valor, linha_ref[0])
    return i


def _estado_identificador(cont: str, i: int, linha_ref: list[int], tokens: list[dict]) -> int:
    """
    Estado: acumulando letras e dígitos.
    Palavras-chave (presentes em MAPA_TOKENS) recebem o tipo mapeado; o restante é ID.
    """
    start = i
    while i < len(cont) and (cont[i].isalpha() or cont[i].isdigit()):
        i += 1
    valor = cont[start:i]
    tipo = MAPA_TOKENS.get(valor, 'ID')
    _emit(tokens, tipo, valor, linha_ref[0])
    return i


def _estado_op_maior(cont: str, i: int, linha_ref: list[int], tokens: list[dict]) -> int:
    """Estado: leu '>'. Verifica se o próximo char forma '>='."""
    if i < len(cont) and cont[i] == '=':
        _emit(tokens, 'OP_GTE', '>=', linha_ref[0])
        return i + 1
    _emit(tokens, 'OP_GT', '>', linha_ref[0])
    return i


def _estado_op_menor(cont: str, i: int, linha_ref: list[int], tokens: list[dict]) -> int:
    """Estado: leu '<'. Verifica se o próximo char forma '<='."""
    if i < len(cont) and cont[i] == '=':
        _emit(tokens, 'OP_LTE', '<=', linha_ref[0])
        return i + 1
    _emit(tokens, 'OP_LT', '<', linha_ref[0])
    return i


def _estado_op_igual(cont: str, i: int, linha_ref: list[int], tokens: list[dict]) -> int:
    """Estado: leu '='. Somente '==' é válido; '=' isolado é erro léxico."""
    if i < len(cont) and cont[i] == '=':
        _emit(tokens, 'OP_EQ', '==', linha_ref[0])
        return i + 1
    raise ValueError(
        f"Linha {linha_ref[0]}: '=' isolado é inválido; use '=='"
    )


def _estado_op_excl(cont: str, i: int, linha_ref: list[int], tokens: list[dict]) -> int:
    """Estado: leu '!'. Somente '!=' é válido; '!' isolado é erro léxico."""
    if i < len(cont) and cont[i] == '=':
        _emit(tokens, 'OP_NEQ', '!=', linha_ref[0])
        return i + 1
    raise ValueError(
        f"Linha {linha_ref[0]}: '!' isolado é inválido; use '!='"
    )


def _estado_inicial(cont: str, i: int, linha_ref: list[int], tokens: list[dict]) -> int:
    """
    Estado inicial do AFD. Despacha para o estado correto de acordo com cont[i].
    Retorna a nova posição após processar o token (ou apenas avançar sobre espaço).
    """
    c = cont[i]

    if c == '\n':
        linha_ref[0] += 1
        return i + 1

    if c in (' ', '\t', '\r'):
        return i + 1

    if c in _OPS_SIMPLES:
        _emit(tokens, _OPS_SIMPLES[c], c, linha_ref[0])
        return i + 1

    if c.isdigit():
        return _estado_numero(cont, i, linha_ref, tokens)

    if c.isalpha():
        return _estado_identificador(cont, i, linha_ref, tokens)

    if c == '>':
        return _estado_op_maior(cont, i + 1, linha_ref, tokens)

    if c == '<':
        return _estado_op_menor(cont, i + 1, linha_ref, tokens)

    if c == '=':
        return _estado_op_igual(cont, i + 1, linha_ref, tokens)

    if c == '!':
        return _estado_op_excl(cont, i + 1, linha_ref, tokens)

    raise ValueError(f"Linha {linha_ref[0]}: caractere inválido '{c}'")


def lerTokens(arquivo: str, erros_out: list[str] | None = None) -> list[dict]:
    """
    Lê o arquivo de código-fonte e devolve vetor de tokens tipados.

    Implementa o analisador léxico da Fase 2 usando um Autômato Finito
    Determinístico com cada estado representado por uma função.
    Processa o conteúdo completo caractere a caractere, rastreando o
    número de linha para mensagens de erro.

    Cada token é representado como:
        {'tipo': str, 'valor': str, 'linha': int}

    Tipos de token possíveis: LP, RP, NUM_INT, NUM_REAL, ID,
    OP_ADD, OP_SUB, OP_MUL, OP_RDIV, OP_IDIV, OP_MOD, OP_POW,
    OP_GT, OP_LT, OP_EQ, OP_NEQ, OP_GTE, OP_LTE,
    KW_RES, KW_START, KW_END, KW_IF, KW_WHILE, EOF.

    Parâmetros:
        arquivo    — caminho do arquivo de entrada.
        erros_out  — lista opcional para recuperação de erros. Quando fornecida,
                     erros léxicos são registrados aqui e o analisador continua
                     (o caractere inválido é descartado). Quando None (padrão),
                     um ValueError é levantado no primeiro erro.

    Levanta:
        FileNotFoundError — se o arquivo não existir.
        ValueError        — se houver erro léxico e erros_out for None.
    """
    try:
        with open(arquivo, encoding='utf-8') as f:
            conteudo = f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"Arquivo '{arquivo}' não encontrado.")

    tokens: list[dict] = []
    linha_ref = [1]
    i = 0
    while i < len(conteudo):
        try:
            i = _estado_inicial(conteudo, i, linha_ref, tokens)
        except ValueError as e:
            if erros_out is not None:
                erros_out.append(str(e))
                i += 1  # descarta o caractere inválido e continua
            else:
                raise

    tokens.append({'tipo': EOF, 'valor': '', 'linha': linha_ref[0]})
    return tokens


# ─────────────────────────────────────────────────────────────
# Parser LL(1) descendente recursivo — Aluno 2
# ─────────────────────────────────────────────────────────────

class _Buffer:
    """
    Buffer de entrada para o parser.
    Encapsula o vetor de tokens e a posição de leitura atual.
    """

    def __init__(self, tokens: list[dict]) -> None:
        self._tokens = tokens
        self._pos = 0

    def lookahead(self) -> dict:
        """Retorna o token atual sem consumi-lo. Retorna token EOF ao fim da entrada."""
        if self._pos < len(self._tokens):
            return self._tokens[self._pos]
        ultima_linha = self._tokens[-1]['linha'] if self._tokens else 1
        return {'tipo': EOF, 'valor': '', 'linha': ultima_linha}

    def consumir(self, tipo_esperado: str) -> dict:
        """
        Consome e retorna o token atual se o tipo bater com tipo_esperado.
        Levanta SyntaxError com mensagem descritiva caso contrário.
        """
        token = self.lookahead()
        if token['tipo'] != tipo_esperado:
            raise SyntaxError(
                f"Linha {token['linha']}: "
                f"esperado {tipo_esperado}, "
                f"encontrado {token['tipo']} ('{token['valor']}')"
            )
        self._pos += 1
        return token

    def avancar(self) -> None:
        """Avança a posição sem verificar o tipo do token (usado na recuperação de erros)."""
        if self._pos < len(self._tokens):
            self._pos += 1

    def linha_atual(self) -> int:
        return self.lookahead()['linha']


def _terminais_esperados_para(nt: str, tabela: dict) -> set[str]:
    """Retorna os terminais que têm entrada definida na tabela para o não-terminal nt."""
    return {terminal for (n, terminal) in tabela if n == nt}


def _pular_ate_proximo_stmt(buf: '_Buffer') -> None:
    """
    Recuperação de pânico: avança o buffer até o LP que inicia o próximo
    stmt no nível 0 de parênteses (ou até EOF), descartando tokens problemáticos.
    """
    profundidade = 0
    while True:
        tok = buf.lookahead()
        if tok['tipo'] == EOF:
            break
        if tok['tipo'] == 'LP':
            if profundidade == 0:
                break  # início do próximo stmt no nível raiz
            profundidade += 1
            buf.avancar()
        elif tok['tipo'] == 'RP':
            if profundidade > 0:
                profundidade -= 1
            buf.avancar()
        else:
            buf.avancar()


def _construir_stmt_list(stmts: list[dict]) -> dict:
    """Constrói nó NT(stmt_list) encadeado a partir de lista de stmts."""
    if not stmts:
        return {'tipo': 'NT', 'simbolo': 'stmt_list', 'filhos': [], 'linha': 1}
    head = stmts[0]
    tail = _construir_stmt_list(stmts[1:])
    return {
        'tipo': 'NT',
        'simbolo': 'stmt_list',
        'filhos': [head, tail],
        'linha': head.get('linha', 1),
    }


def _parse_nt(
    nt: str,
    buf: _Buffer,
    tabela: dict,
    nao_terminais: set[str],
) -> dict:
    """
    Passo central do parser descendente recursivo LL(1).

    Consulta tabela[(nt, lookahead)] para decidir qual produção aplicar,
    processa cada símbolo da produção recursivamente e constrói o nó da
    árvore de derivação.

    Nó não-terminal: {'tipo': 'NT',    'simbolo': str, 'filhos': list, 'linha': int}
    Nó terminal:     {'tipo': 'TOKEN', 'tipo_token': str, 'valor': str, 'linha': int}
    Produção ε:      nó NT com filhos vazios []
    """
    token = buf.lookahead()
    tipo_atual = token['tipo']
    linha = token['linha']

    chave = (nt, tipo_atual)
    if chave not in tabela:
        esperados = sorted(_terminais_esperados_para(nt, tabela))
        raise SyntaxError(
            f"Linha {linha}: token inesperado '{token['valor']}' ({tipo_atual}) "
            f"ao analisar '{nt}'. "
            f"Esperados: {esperados}"
        )

    producao = tabela[chave]
    filhos: list[dict] = []

    for simbolo in producao:
        if simbolo == EPSILON:
            break
        if simbolo in nao_terminais:
            filho = _parse_nt(simbolo, buf, tabela, nao_terminais)
        else:
            tok = buf.consumir(simbolo)
            filho = {
                'tipo': 'TOKEN',
                'tipo_token': simbolo,
                'valor': tok['valor'],
                'linha': tok['linha'],
            }
        filhos.append(filho)

    return {'tipo': 'NT', 'simbolo': nt, 'filhos': filhos, 'linha': linha}


def parsear(tokens: list[dict], gramatica: dict,
            erros_out: list[str] | None = None) -> dict:
    """
    Analisa sintaticamente o vetor de tokens usando a tabela LL(1).

    Implementa um parser descendente recursivo guiado pela tabela LL(1)
    fornecida por construirGramatica(). Cada não-terminal é expandido via
    _parse_nt(), que consulta a tabela para escolher a produção correta.

    Entrada:
        tokens     — vetor de tokens tipados (saída de lerTokens),
                     cada elemento: {'tipo': str, 'valor': str, 'linha': int}
        gramatica  — estrutura retornada por construirGramatica()
        erros_out  — lista opcional para recuperação de erros. Quando fornecida,
                     erros sintáticos são registrados aqui e o parser continua
                     a partir do próximo stmt (recuperação de pânico). Quando
                     None (padrão), SyntaxError é levantado no primeiro erro.

    Saída:
        Nó raiz da árvore de derivação (parse tree), formato:
            {'tipo': 'NT', 'simbolo': 'programa', 'filhos': [...], 'linha': int}

    Levanta:
        SyntaxError — com número de linha, token inesperado e tokens esperados
                      (apenas quando erros_out é None).
    """
    tabela = gramatica['tabela']
    nao_terminais = gramatica['nao_terminais']
    simbolo_inicial = gramatica['simbolo_inicial']

    buf = _Buffer(tokens)

    if erros_out is None:
        # Comportamento original: levanta SyntaxError no primeiro erro
        raiz = _parse_nt(simbolo_inicial, buf, tabela, nao_terminais)
        sobra = buf.lookahead()
        if sobra['tipo'] != EOF:
            raise SyntaxError(
                f"Linha {sobra['linha']}: tokens inesperados após fim do programa "
                f"('{sobra['valor']}' — {sobra['tipo']})"
            )
        return raiz

    # Modo de recuperação: analisa stmt a stmt, coletando todos os erros
    stmts_validos: list[dict] = []
    while buf.lookahead()['tipo'] != EOF:
        tok = buf.lookahead()
        if tok['tipo'] != 'LP':
            erros_out.append(
                f"Linha {tok['linha']}: token inesperado '{tok['valor']}' "
                f"({tok['tipo']}) — esperado início de stmt '('"
            )
            buf.avancar()
            continue
        try:
            stmt = _parse_nt('stmt', buf, tabela, nao_terminais)
            stmts_validos.append(stmt)
        except SyntaxError as e:
            erros_out.append(str(e))
            _pular_ate_proximo_stmt(buf)

    # Constrói árvore de programa com os stmts analisados com sucesso
    stmt_list = _construir_stmt_list(stmts_validos)
    linha_inicio = stmts_validos[0]['linha'] if stmts_validos else 1
    return {
        'tipo': 'NT',
        'simbolo': 'programa',
        'filhos': [
            stmt_list,
            {'tipo': 'TOKEN', 'tipo_token': 'EOF', 'valor': '',
             'linha': buf.lookahead()['linha']},
        ],
        'linha': linha_inicio,
    }


# ─────────────────────────────────────────────────────────────
# Geração de Árvore Sintática — Aluno 4
# ─────────────────────────────────────────────────────────────

def gerarArvore(derivacao: dict) -> dict:
    """
    (Aluno 4) Constrói a árvore sintática a partir da estrutura de derivação.
    
    A derivação retornada por parsear() já é essencialmente uma árvore sintática.
    Esta função valida, limpa e formata a árvore para uso posterior (geração de
    código, visualização, etc.).

    Entrada:
        derivacao — nó raiz da árvore de derivação produzida por parsear()
                    (tipo: dict com 'tipo', 'simbolo', 'filhos', 'linha')

    Saída:
        dict com mesma estrutura, validado e potencialmente reformatado:
            {
                'tipo': 'NT' | 'TOKEN',
                'simbolo': str (para 'NT') ou 'tipo_token': str (para 'TOKEN'),
                'valor': str (opcional, para 'TOKEN'),
                'filhos': list[dict] (opcional, para 'NT'),
                'linha': int
            }
    """
    def _validar_e_limpar(no: dict) -> dict:
        """Recursivamente valida e limpa a árvore."""
        if no['tipo'] == 'NT':
            filhos_limpos = [_validar_e_limpar(f) for f in no.get('filhos', [])]
            return {
                'tipo': 'NT',
                'simbolo': no['simbolo'],
                'filhos': filhos_limpos,
                'linha': no['linha'],
            }
        elif no['tipo'] == 'TOKEN':
            return {
                'tipo': 'TOKEN',
                'tipo_token': no['tipo_token'],
                'valor': no['valor'],
                'linha': no['linha'],
            }
        else:
            raise ValueError(f"Tipo de nó desconhecido: {no['tipo']}")
    
    return _validar_e_limpar(derivacao)


# ─────────────────────────────────────────────────────────────
# Visualização de Árvore
# ─────────────────────────────────────────────────────────────

def _visualizar_arvore(no: dict, prefixo: str = "", eh_ultimo: bool = True) -> str:
    """
    Converte uma árvore sintática em representação de texto visual (tree format).
    
    Exemplo:
        programa
        └── stmt_list
            ├── stmt
            │   └── stmt_inner: (3.14 2.0 +)
            └── stmt_list
                └── EPSILON
    """
    linhas: list[str] = []
    
    if no['tipo'] == 'NT':
        simbolo = no['simbolo']
        connector = "└── " if eh_ultimo else "├── "
        linhas.append(prefixo + connector + simbolo)
        
        filhos = no.get('filhos', [])
        for i, filho in enumerate(filhos):
            eh_ultimo_filho = (i == len(filhos) - 1)
            extensao = "    " if eh_ultimo else "│   "
            novo_prefixo = prefixo + extensao
            linhas.append(_visualizar_arvore(filho, novo_prefixo, eh_ultimo_filho))
    
    elif no['tipo'] == 'TOKEN':
        tipo_token = no['tipo_token']
        valor = no['valor']
        connector = "└── " if eh_ultimo else "├── "
        linhas.append(prefixo + connector + f"{tipo_token}: '{valor}'")
    
    return "\n".join(filter(None, linhas))


def _arvore_para_json(no: dict, indentar: int = 2, nivel: int = 0) -> str:
    """
    Converte uma árvore sintática em formato JSON legível.
    """
    indent = " " * (nivel * indentar)
    next_indent = " " * ((nivel + 1) * indentar)
    
    if no['tipo'] == 'NT':
        filhos = no.get('filhos', [])
        filhos_json = ",\n".join(
            _arvore_para_json(f, indentar, nivel + 1) for f in filhos
        )
        return (
            f'{{\n'
            f'{next_indent}"tipo": "NT",\n'
            f'{next_indent}"simbolo": "{no["simbolo"]}",\n'
            f'{next_indent}"filhos": [\n'
            f'{next_indent}  {filhos_json}\n'
            f'{next_indent}],\n'
            f'{next_indent}"linha": {no["linha"]}\n'
            f'{indent}}}'
        )
    elif no['tipo'] == 'TOKEN':
        return (
            f'{{\n'
            f'{next_indent}"tipo": "TOKEN",\n'
            f'{next_indent}"tipo_token": "{no["tipo_token"]}",\n'
            f'{next_indent}"valor": "{no["valor"]}",\n'
            f'{next_indent}"linha": {no["linha"]}\n'
            f'{indent}}}'
        )


# ─────────────────────────────────────────────────────────────
# Geração de Código Assembly ARMv7 — Aluno 4
# ─────────────────────────────────────────────────────────────

class _GeradorAssembly:
    """
    Gerador de código Assembly ARMv7 VFP para DEC1-SOC(v16.1).

    Estratégia:
    - Todos os valores são IEEE 754 double-precision (registradores D0-D7)
    - Constantes e variáveis vivem na seção .data como .double
    - Acesso via LDR R0, =label; VLDR Dd, [R0]
    - dreg (0-7): índice do D-registrador destino da sub-expressão atual
    - Ops binárias: D{dreg} op D{dreg+1} → D{dreg}
    - IF/WHILE: VCMP.F64 + VMRS APSR_nzcv + branches condicionais
    - RES: cada stmt topo salva D0 em label .data; (N RES) carrega de volta
    """

    _REL_OPS: frozenset = frozenset(
        {'OP_GT', 'OP_LT', 'OP_EQ', 'OP_NEQ', 'OP_GTE', 'OP_LTE'}
    )
    _BRANCH_MAP: dict = {
        'OP_GT': 'BGT', 'OP_LT': 'BLT', 'OP_EQ': 'BEQ',
        'OP_NEQ': 'BNE', 'OP_GTE': 'BGE', 'OP_LTE': 'BLE',
    }

    def __init__(self):
        self._dados: list[str] = []
        self._texto: list[str] = []
        self._label_c = 0
        self._constantes: dict[str, str] = {}
        self._variaveis: dict[str, str] = {}
        self._resultados: list[str] = []

    # ── emissores ──────────────────────────────────────────────

    def _novo_label(self, pref: str = "L") -> str:
        self._label_c += 1
        return f"{pref}{self._label_c}"

    def e(self, linha: str) -> None:
        self._texto.append(f"  {linha}")

    def elabel(self, lbl: str) -> None:
        self._texto.append(f"{lbl}:")

    def ec(self, txt: str) -> None:
        self._texto.append(f"  @ {txt}")

    # ── seção .data ─────────────────────────────────────────────

    def _label_const(self, valor_str: str) -> str:
        """Garante entrada .double na seção .data e retorna o label."""
        if valor_str not in self._constantes:
            lbl = self._novo_label("c")
            self._constantes[valor_str] = lbl
            try:
                fval = float(valor_str)
            except ValueError:
                fval = 0.0
            self._dados.append(f".align 8")
            self._dados.append(f"{lbl}: .double {fval}")
        return self._constantes[valor_str]

    def _label_var(self, nome: str) -> str:
        """Garante variável .double na seção .data e retorna o label."""
        if nome not in self._variaveis:
            lbl = f"v_{nome}"
            self._variaveis[nome] = lbl
            self._dados.append(f".align 8")
            self._dados.append(f"{lbl}: .double 0.0")
        return self._variaveis[nome]

    # ── load/store ──────────────────────────────────────────────

    def _load_const(self, valor_str: str, dreg: int) -> None:
        lbl = self._label_const(valor_str)
        self.e(f"LDR R0, ={lbl}")
        self.e(f"VLDR D{dreg}, [R0]")

    def _load_var(self, nome: str, dreg: int) -> None:
        lbl = self._label_var(nome)
        self.e(f"LDR R0, ={lbl}")
        self.e(f"VLDR D{dreg}, [R0]")

    def _store_var(self, nome: str, dreg: int) -> None:
        lbl = self._label_var(nome)
        self.e(f"LDR R0, ={lbl}")
        self.e(f"VSTR D{dreg}, [R0]")

    # ── operações ───────────────────────────────────────────────

    def _emit_op(self, op_tipo: str, dreg: int) -> None:
        """D{dreg} = D{dreg} <op> D{dreg+1}."""
        d0, d1 = f"D{dreg}", f"D{dreg + 1}"
        if op_tipo == 'OP_ADD':
            self.e(f"VADD.F64 {d0}, {d0}, {d1}")
        elif op_tipo == 'OP_SUB':
            self.e(f"VSUB.F64 {d0}, {d0}, {d1}")
        elif op_tipo == 'OP_MUL':
            self.e(f"VMUL.F64 {d0}, {d0}, {d1}")
        elif op_tipo == 'OP_RDIV':
            self.e(f"VDIV.F64 {d0}, {d0}, {d1}")
        elif op_tipo == 'OP_IDIV':
            self._emit_idiv(dreg)
        elif op_tipo == 'OP_MOD':
            self._emit_mod(dreg)
        elif op_tipo == 'OP_POW':
            self._emit_pow(dreg)

    def _emit_idiv(self, dreg: int) -> None:
        """Divisão inteira: trunca para int, divide com SDIV, converte de volta."""
        self.ec("divisao inteira")
        self.e(f"VCVT.S32.F64 S0, D{dreg}")
        self.e(f"VCVT.S32.F64 S2, D{dreg + 1}")
        self.e(f"VMOV R0, S0")
        self.e(f"VMOV R1, S2")
        self.e(f"SDIV R0, R0, R1")
        self.e(f"VMOV S0, R0")
        self.e(f"VCVT.F64.S32 D{dreg}, S0")

    def _emit_mod(self, dreg: int) -> None:
        """Resto da divisão inteira: r = a - (a/b)*b."""
        self.ec("modulo inteiro")
        self.e(f"VCVT.S32.F64 S0, D{dreg}")
        self.e(f"VCVT.S32.F64 S2, D{dreg + 1}")
        self.e(f"VMOV R0, S0")
        self.e(f"VMOV R1, S2")
        self.e(f"SDIV R2, R0, R1")
        self.e(f"MUL R2, R2, R1")
        self.e(f"SUB R0, R0, R2")
        self.e(f"VMOV S0, R0")
        self.e(f"VCVT.F64.S32 D{dreg}, S0")

    def _emit_pow(self, dreg: int) -> None:
        """Potenciação com loop (expoente inteiro >= 0). Usa D{dreg+2} como base temp."""
        lbl_loop = self._novo_label("pow_loop")
        lbl_end  = self._novo_label("pow_end")
        lbl_um   = self._label_const("1.0")
        base_d   = dreg + 2
        self.ec(f"potenciacao D{dreg} ^ D{dreg + 1}")
        self.e(f"VMOV.F64 D{base_d}, D{dreg}")          # salva base
        self.e(f"VCVT.S32.F64 S0, D{dreg + 1}")         # expoente → inteiro
        self.e(f"VMOV R1, S0")
        self.e(f"LDR R0, ={lbl_um}")                     # resultado = 1.0
        self.e(f"VLDR D{dreg}, [R0]")
        self.elabel(lbl_loop)
        self.e(f"CMP R1, #0")
        self.e(f"BEQ {lbl_end}")
        self.e(f"VMUL.F64 D{dreg}, D{dreg}, D{base_d}")
        self.e(f"SUB R1, R1, #1")
        self.e(f"B {lbl_loop}")
        self.elabel(lbl_end)

    def _emit_cmp(self, op_tipo: str, dreg: int) -> None:
        """Comparação: D{dreg} = 1.0 se verdadeiro, 0.0 se falso."""
        lbl_true  = self._novo_label("cmp_t")
        lbl_after = self._novo_label("cmp_a")
        lbl_um    = self._label_const("1.0")
        lbl_zero  = self._label_const("0.0")
        self.e(f"VCMP.F64 D{dreg}, D{dreg + 1}")
        self.e(f"VMRS APSR_nzcv, FPSCR")
        bcc = self._BRANCH_MAP.get(op_tipo, 'BEQ')
        self.e(f"{bcc} {lbl_true}")
        self.e(f"LDR R0, ={lbl_zero}")
        self.e(f"VLDR D{dreg}, [R0]")
        self.e(f"B {lbl_after}")
        self.elabel(lbl_true)
        self.e(f"LDR R0, ={lbl_um}")
        self.e(f"VLDR D{dreg}, [R0]")
        self.elabel(lbl_after)

    # ── navegação na árvore ─────────────────────────────────────

    def _get_op_tipo(self, no: dict) -> str:
        """Extrai tipo do operador de arith_op, rel_op ou any_op."""
        if no['tipo'] == 'TOKEN':
            return no['tipo_token']
        for f in no.get('filhos', []):
            t = self._get_op_tipo(f)
            if t:
                return t
        return ''

    def _apply_op(self, op_tipo: str, dreg: int) -> None:
        if op_tipo in self._REL_OPS:
            self._emit_cmp(op_tipo, dreg)
        else:
            self._emit_op(op_tipo, dreg)

    # ── avaliação de expressões ─────────────────────────────────

    def _eval_stmt(self, no: dict, dreg: int) -> None:
        """Avalia stmt = (LP stmt_inner RP) → resultado em D{dreg}."""
        for filho in no.get('filhos', []):
            if filho['tipo'] == 'NT' and filho['simbolo'] == 'stmt_inner':
                self._eval_stmt_inner(filho, dreg)
                return

    def _eval_stmt_inner(self, no: dict, dreg: int) -> None:
        """Avalia stmt_inner → resultado em D{dreg}."""
        filhos = no.get('filhos', [])
        if not filhos:
            return
        primeiro = filhos[0]
        if primeiro['tipo'] != 'TOKEN':
            return
        tipo = primeiro['tipo_token']

        if tipo in ('KW_START', 'KW_END'):
            self.ec(f"--- {tipo[3:]} ---")

        elif tipo == 'KW_IF':
            # [KW_IF, stmt_cond, stmt_true, opt_else]
            self._gerar_if(
                filhos[1], filhos[2],
                filhos[3] if len(filhos) > 3 else None,
                dreg,
            )

        elif tipo == 'KW_WHILE':
            # [KW_WHILE, stmt_cond, stmt_body]
            self._gerar_while(filhos[1], filhos[2], dreg)

        elif tipo in ('NUM_INT', 'NUM_REAL'):
            cont = filhos[1] if len(filhos) > 1 else None
            self._eval_num_cont(primeiro['valor'], cont, dreg)

        elif tipo == 'ID':
            cont = filhos[1] if len(filhos) > 1 else None
            self._eval_id_cont(primeiro['valor'], cont, dreg)

        elif tipo == 'LP':
            # [LP, NT(stmt_inner), RP, NT(nested_cont)]
            inner = filhos[1] if len(filhos) > 1 else None
            cont  = filhos[3] if len(filhos) > 3 else None
            if inner:
                self._eval_stmt_inner(inner, dreg)
            if cont and cont['tipo'] == 'NT' and cont['simbolo'] == 'nested_cont':
                self._eval_nested_cont(cont, dreg)

    def _eval_num_cont(self, valor: str, cont: dict | None, dreg: int) -> None:
        """Carrega literal e processa sua continuação."""
        self._load_const(valor, dreg)
        if not cont or cont['tipo'] != 'NT':
            return
        filhos = cont.get('filhos', [])
        if not filhos:
            return
        primeiro = filhos[0]
        if primeiro['tipo'] != 'TOKEN':
            return
        t = primeiro['tipo_token']

        if t == 'KW_RES':
            # (N RES) — substitui D{dreg} pelo resultado N stmts atrás
            try:
                n = int(valor)
            except ValueError:
                n = 0
            self._eval_res(n, dreg)

        elif t == 'ID':
            # (valor ID ...) → STORE ou aritmética
            after = filhos[1] if len(filhos) > 1 else None
            self._eval_after_id(primeiro['valor'], after, dreg)

        elif t in ('NUM_INT', 'NUM_REAL'):
            # (valor N2 op)
            self._load_const(primeiro['valor'], dreg + 1)
            op_no = filhos[1] if len(filhos) > 1 else None
            if op_no:
                self._apply_op(self._get_op_tipo(op_no), dreg)

        elif t == 'LP':
            # (valor (expr) op)
            inner = filhos[1] if len(filhos) > 1 else None
            op_no = filhos[3] if len(filhos) > 3 else None
            if inner:
                self._eval_stmt_inner(inner, dreg + 1)
            if op_no:
                self._apply_op(self._get_op_tipo(op_no), dreg)

    def _eval_id_cont(self, nome: str, cont: dict | None, dreg: int) -> None:
        """Avalia expressão que começa com ID."""
        filhos = cont.get('filhos', []) if cont and cont['tipo'] == 'NT' else []

        if not filhos:
            # (ID) → LOAD
            self.ec(f"LOAD {nome}")
            self._load_var(nome, dreg)
            return

        # Primeiro operando é o ID
        self._load_var(nome, dreg)
        self._eval_segundo_operando(filhos, dreg)

    def _eval_nested_cont(self, cont: dict, dreg: int) -> None:
        """Processa continuação após subexpressão: ((expr) ...)."""
        filhos = cont.get('filhos', [])
        if not filhos:
            return  # ((expr)) — apenas a subexpressão
        primeiro = filhos[0]
        if primeiro['tipo'] != 'TOKEN':
            return
        t = primeiro['tipo_token']

        if t == 'ID':
            # ((expr) ID ...) → STORE ou aritmética
            after = filhos[1] if len(filhos) > 1 else None
            self._eval_after_id(primeiro['valor'], after, dreg)
        else:
            self._eval_segundo_operando(filhos, dreg)

    def _eval_segundo_operando(self, filhos: list, dreg: int) -> None:
        """
        D{dreg} já tem o primeiro operando.
        filhos é a lista de filhos da continuação (num_int_cont excl. primeiro filho,
        id_cont, nested_cont, etc.). Carrega segundo operando em D{dreg+1} e aplica op.
        """
        if not filhos:
            return
        primeiro = filhos[0]
        if primeiro['tipo'] != 'TOKEN':
            return
        t = primeiro['tipo_token']

        if t in ('NUM_INT', 'NUM_REAL'):
            self._load_const(primeiro['valor'], dreg + 1)
            op_no = filhos[1] if len(filhos) > 1 else None
            if op_no:
                self._apply_op(self._get_op_tipo(op_no), dreg)

        elif t == 'ID':
            self._load_var(primeiro['valor'], dreg + 1)
            op_no = filhos[1] if len(filhos) > 1 else None
            if op_no:
                self._apply_op(self._get_op_tipo(op_no), dreg)

        elif t == 'LP':
            inner = filhos[1] if len(filhos) > 1 else None
            op_no = filhos[3] if len(filhos) > 3 else None
            if inner:
                self._eval_stmt_inner(inner, dreg + 1)
            if op_no:
                self._apply_op(self._get_op_tipo(op_no), dreg)

    def _eval_after_id(self, nome: str, after_no: dict | None, dreg: int) -> None:
        """
        Processa (A nome ...) onde A já está em D{dreg}:
          after_id = EPSILON → STORE D{dreg} em nome
          after_id = [op]    → aritmética: carrega nome em D{dreg+1}, aplica op
        """
        after_filhos = (
            after_no.get('filhos', []) if after_no and after_no['tipo'] == 'NT' else []
        )
        if not after_filhos:
            self.ec(f"STORE {nome}")
            self._store_var(nome, dreg)
        else:
            self._load_var(nome, dreg + 1)
            op_no = after_filhos[0]
            self._apply_op(self._get_op_tipo(op_no), dreg)

    def _eval_res(self, n: int, dreg: int) -> None:
        """Carrega resultado n stmts atrás em D{dreg}."""
        idx = len(self._resultados) - n
        if 0 <= idx < len(self._resultados):
            lbl = self._resultados[idx]
            self.ec(f"RES({n}) <- {lbl}")
            self.e(f"LDR R0, ={lbl}")
            self.e(f"VLDR D{dreg}, [R0]")
        else:
            self.ec(f"RES({n}) fora do alcance -> 0.0")
            self._load_const("0.0", dreg)

    # ── estruturas de controle ───────────────────────────────────

    def _gerar_if(self, stmt_cond: dict, stmt_true: dict,
                  opt_else_no: dict | None, dreg: int) -> None:
        lbl_else = self._novo_label("else")
        lbl_end  = self._novo_label("endif")
        lbl_zero = self._label_const("0.0")

        self.ec("--- IF: avalia condicao ---")
        self._eval_stmt(stmt_cond, dreg)
        self.e(f"LDR R0, ={lbl_zero}")
        self.e(f"VLDR D{dreg + 1}, [R0]")
        self.e(f"VCMP.F64 D{dreg}, D{dreg + 1}")
        self.e(f"VMRS APSR_nzcv, FPSCR")
        self.e(f"BEQ {lbl_else}")

        self.ec("ramo verdadeiro")
        self._eval_stmt(stmt_true, dreg)
        self.e(f"B {lbl_end}")

        self.elabel(lbl_else)
        if opt_else_no and opt_else_no['tipo'] == 'NT':
            else_filhos = opt_else_no.get('filhos', [])
            if else_filhos:
                self.ec("ramo falso (else)")
                self._eval_stmt(else_filhos[0], dreg)

        self.elabel(lbl_end)

    def _gerar_while(self, stmt_cond: dict, stmt_body: dict, dreg: int) -> None:
        lbl_loop = self._novo_label("while_loop")
        lbl_end  = self._novo_label("while_end")
        lbl_zero = self._label_const("0.0")

        self.ec("--- WHILE ---")
        self.elabel(lbl_loop)
        self._eval_stmt(stmt_cond, dreg)
        self.e(f"LDR R0, ={lbl_zero}")
        self.e(f"VLDR D{dreg + 1}, [R0]")
        self.e(f"VCMP.F64 D{dreg}, D{dreg + 1}")
        self.e(f"VMRS APSR_nzcv, FPSCR")
        self.e(f"BEQ {lbl_end}")

        self.ec("corpo do loop")
        self._eval_stmt(stmt_body, dreg)
        self.e(f"B {lbl_loop}")
        self.elabel(lbl_end)

    # ── processamento de nível de programa ─────────────────────

    def processar_arvore(self, arvore: dict) -> None:
        if arvore['tipo'] == 'NT' and arvore['simbolo'] == 'programa':
            for filho in arvore.get('filhos', []):
                self._processar_stmt_list(filho)

    def _processar_stmt_list(self, no: dict) -> None:
        if no['tipo'] != 'NT' or no['simbolo'] != 'stmt_list':
            return
        for filho in no.get('filhos', []):
            if filho['tipo'] == 'NT' and filho['simbolo'] == 'stmt':
                self._processar_stmt_topo(filho)
            elif filho['tipo'] == 'NT' and filho['simbolo'] == 'stmt_list':
                self._processar_stmt_list(filho)

    def _processar_stmt_topo(self, no_stmt: dict) -> None:
        """Processa stmt de nível superior; salva D0 para uso por (N RES)."""
        lbl_res = self._novo_label("res")
        self._dados.append(".align 8")
        self._dados.append(f"{lbl_res}: .double 0.0")

        self.ec(f"==== stmt #{len(self._resultados) + 1} -> {lbl_res} ====")
        self._eval_stmt(no_stmt, 0)

        # Guarda resultado em memória para (N RES)
        self.e(f"LDR R0, ={lbl_res}")
        self.e(f"VSTR D0, [R0]")
        self._resultados.append(lbl_res)

    def finalizar(self) -> str:
        """Monta e retorna o código Assembly completo."""
        linhas = [
            "@ ============================================",
            "@ Codigo Assembly gerado - ARMv7 DEC1-SOC",
            "@ ============================================",
            "",
            ".section .data",
        ]
        linhas.extend(self._dados)
        linhas.extend([
            "",
            ".section .text",
            ".global _start",
            "_start:",
        ])
        linhas.extend(self._texto)
        linhas.extend([
            "",
            "  @ fim do programa",
            "  MOV R0, #0",
            "  BX LR",
        ])
        return "\n".join(linhas)


def gerarAssembly(arvore: dict) -> str:
    """
    (Aluno 4) Gera código Assembly ARMv7 DEC1-SOC(v16.1) a partir da árvore sintática.

    Implementa um gerador de código para a máquina Cpulator-ARMv7 DEC1-SOC(v16.1).
    
    Estratégia:
    - Usa registradores R0-R3 para valores temporários
    - Usa stack para variáveis (memória)
    - Gera rótulos para estruturas de controle (IF, WHILE)
    - Processa árvore recursivamente, gerando instruções conforme encontra
      operações aritméticas, comandos especiais e estruturas de controle

    Entrada:
        arvore — raiz da árvore sintática gerada por gerarArvore() ou parsear()

    Saída:
        string contendo código Assembly completo e pronto para montagem/execução
    """
    gerador = _GeradorAssembly()
    gerador.processar_arvore(arvore)
    return gerador.finalizar()


# ─────────────────────────────────────────────────────────────
# Interface Principal — Aluno 4
# ─────────────────────────────────────────────────────────────

def main() -> None:
    """
    (Aluno 4) Ponto de entrada do programa.
    
    Lê arquivo de código-fonte fornecido como argumento de linha de comando,
    executa análise léxica, sintática, gera árvore sintática e código Assembly,
    e exibe resultados.
    
    Uso:
        python AnalisadorSintatico.py <arquivo.txt>
    
    Saídas:
        - Exibe árvore sintática em formato visual
        - Exibe código Assembly gerado
        - Salva árvore em "arvore.json"
        - Salva Assembly em "programa.asm"
    """
    # Garante UTF-8 no stdout (necessário no Windows para caracteres da árvore)
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass

    if len(sys.argv) != 2:
        print("Uso: python AnalisadorSintatico.py <arquivo.txt>")
        sys.exit(1)

    arquivo = sys.argv[1]

    erros_lex:  list[str] = []
    erros_sint: list[str] = []

    try:
        # ── Fase 1: Análise léxica com recuperação de erros ──────────────
        print(f"Analisando arquivo: {arquivo}")
        tokens = lerTokens(arquivo, erros_out=erros_lex)

        if erros_lex:
            print(f"\n[ERROS LÉXICOS] {len(erros_lex)} erro(s) encontrado(s):",
                  file=sys.stderr)
            for e in erros_lex:
                print(f"  {e}", file=sys.stderr)
        else:
            print(f"[OK] {len(tokens) - 1} tokens gerados")

        # ── Fase 2: Gramática LL(1) ───────────────────────────────────────
        gramatica = construirGramatica()
        print(f"[OK] Gramática LL(1) construída")

        # ── Fase 3: Análise sintática com recuperação de erros ───────────
        derivacao = parsear(tokens, gramatica, erros_out=erros_sint)

        if erros_sint:
            print(f"\n[ERROS SINTÁTICOS] {len(erros_sint)} erro(s) encontrado(s):",
                  file=sys.stderr)
            for e in erros_sint:
                print(f"  {e}", file=sys.stderr)
        else:
            print(f"[OK] Análise sintática concluída")

        # ── Interrompe se há erros (léxicos e/ou sintáticos) ─────────────
        total_erros = len(erros_lex) + len(erros_sint)
        if total_erros > 0:
            print(
                f"\n[ERRO] Compilação interrompida: "
                f"{total_erros} erro(s) encontrado(s).",
                file=sys.stderr,
            )
            sys.exit(1)

        # ── Fase 4: Geração de árvore sintática ──────────────────────────
        arvore = gerarArvore(derivacao)
        print(f"[OK] Árvore sintática gerada")

        # Exibe árvore
        print("\n" + "="*70)
        print("ÁRVORE SINTÁTICA")
        print("="*70)
        print(_visualizar_arvore(arvore))

        # Salva árvore em JSON
        with open("arvore.json", "w", encoding="utf-8") as f:
            f.write(_arvore_para_json(arvore))
        print(f"\n[OK] Árvore salva em 'arvore.json'")

        # ── Fase 5: Geração de código Assembly ───────────────────────────
        assembly = gerarAssembly(arvore)
        print("\n" + "="*70)
        print("CÓDIGO ASSEMBLY GERADO")
        print("="*70)
        print(assembly)

        # Salva Assembly
        with open("programa.asm", "w", encoding="utf-8") as f:
            f.write(assembly)
        print(f"\n[OK] Assembly salvo em 'programa.asm'")

        print("\n" + "="*70)
        print("[OK] Compilação concluída com sucesso!")
        print("="*70)

    except FileNotFoundError as e:
        print(f"[ERRO] Arquivo não encontrado: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[ERRO] Erro inesperado: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


# ─────────────────────────────────────────────────────────────
# Funções de teste — construirGramatica (Aluno 1)
# ─────────────────────────────────────────────────────────────

def test_gramatica_retorna_estrutura_completa() -> None:
    g = construirGramatica()
    chaves_esperadas = {
        'producoes', 'nao_terminais', 'terminais',
        'simbolo_inicial', 'first', 'follow', 'tabela',
    }
    assert set(g.keys()) == chaves_esperadas, f"Chaves inesperadas: {set(g.keys())}"
    assert g['simbolo_inicial'] == 'programa'
    assert isinstance(g['producoes'], dict)
    assert isinstance(g['tabela'], dict)
    assert len(g['nao_terminais']) > 0
    assert len(g['terminais']) > 0


def test_first_terminais_sao_si_mesmos() -> None:
    g = construirGramatica()
    first = g['first']
    for t in g['terminais']:
        assert first.get(t) == {t}, (
            f"FIRST({t}) deveria ser {{{t}}}, obteve {first.get(t)}"
        )


def test_first_arith_op() -> None:
    g = construirGramatica()
    esperado = {'OP_ADD', 'OP_SUB', 'OP_MUL', 'OP_RDIV', 'OP_IDIV', 'OP_MOD', 'OP_POW'}
    assert g['first']['arith_op'] == esperado, (
        f"FIRST(arith_op) errado: {g['first']['arith_op']}"
    )


def test_first_rel_op() -> None:
    g = construirGramatica()
    esperado = {'OP_GT', 'OP_LT', 'OP_EQ', 'OP_NEQ', 'OP_GTE', 'OP_LTE'}
    assert g['first']['rel_op'] == esperado, (
        f"FIRST(rel_op) errado: {g['first']['rel_op']}"
    )


def test_first_stmt_inner() -> None:
    g = construirGramatica()
    first_si = g['first']['stmt_inner']
    tokens_esperados = (
        'KW_START', 'KW_END', 'KW_IF', 'KW_WHILE',
        'NUM_INT', 'NUM_REAL', 'ID', 'LP',
    )
    for token in tokens_esperados:
        assert token in first_si, f"{token} deveria estar em FIRST(stmt_inner)"
    assert EPSILON not in first_si, "stmt_inner não pode derivar ε"


def test_first_stmt_e_stmt_list() -> None:
    g = construirGramatica()
    assert g['first']['stmt'] == {'LP'}, (
        f"FIRST(stmt) deveria ser {{'LP'}}, obteve {g['first']['stmt']}"
    )
    assert 'LP' in g['first']['stmt_list'], "LP deveria estar em FIRST(stmt_list)"
    assert EPSILON in g['first']['stmt_list'], "ε deveria estar em FIRST(stmt_list)"


def test_follow_stmt_inner() -> None:
    g = construirGramatica()
    assert g['follow']['stmt_inner'] == {'RP'}, (
        f"FOLLOW(stmt_inner) errado: {g['follow']['stmt_inner']}"
    )


def test_follow_stmt_list() -> None:
    g = construirGramatica()
    assert EOF in g['follow']['stmt_list'], (
        f"EOF deveria estar em FOLLOW(stmt_list), obteve {g['follow']['stmt_list']}"
    )


def test_follow_opt_else() -> None:
    g = construirGramatica()
    assert 'RP' in g['follow']['opt_else'], (
        f"RP deveria estar em FOLLOW(opt_else), obteve {g['follow']['opt_else']}"
    )


def test_tabela_sem_conflitos() -> None:
    # construirGramatica levanta ValueError em caso de conflito
    try:
        construirGramatica()
    except ValueError as e:
        assert False, f"Conflito detectado na tabela LL(1): {e}"


def test_tabela_entrada_valida_start() -> None:
    g = construirGramatica()
    assert ('stmt_inner', 'KW_START') in g['tabela'], (
        "Entrada [stmt_inner, KW_START] ausente na tabela"
    )
    assert g['tabela'][('stmt_inner', 'KW_START')] == ['KW_START']


def test_tabela_entrada_valida_end() -> None:
    g = construirGramatica()
    assert ('stmt_inner', 'KW_END') in g['tabela'], (
        "Entrada [stmt_inner, KW_END] ausente na tabela"
    )


def test_tabela_entrada_valida_if() -> None:
    g = construirGramatica()
    assert ('stmt_inner', 'KW_IF') in g['tabela'], (
        "Entrada [stmt_inner, KW_IF] ausente na tabela"
    )
    prod = g['tabela'][('stmt_inner', 'KW_IF')]
    assert prod == ['KW_IF', 'stmt', 'stmt', 'opt_else'], (
        f"Produção para [stmt_inner, KW_IF] errada: {prod}"
    )


def test_tabela_entrada_while() -> None:
    g = construirGramatica()
    assert ('stmt_inner', 'KW_WHILE') in g['tabela'], (
        "Entrada [stmt_inner, KW_WHILE] ausente na tabela"
    )
    prod = g['tabela'][('stmt_inner', 'KW_WHILE')]
    assert prod == ['KW_WHILE', 'stmt', 'stmt'], (
        f"Produção para [stmt_inner, KW_WHILE] errada: {prod}"
    )


def test_tabela_id_cont_epsilon() -> None:
    g = construirGramatica()
    # Quando token é RP após ID, id_cont → ε
    assert ('id_cont', 'RP') in g['tabela'], (
        "Entrada [id_cont, RP] ausente na tabela"
    )
    assert g['tabela'][('id_cont', 'RP')] == [EPSILON], (
        "id_cont com RP deveria produzir ε"
    )


def test_tabela_opt_else_epsilon() -> None:
    g = construirGramatica()
    assert ('opt_else', 'RP') in g['tabela'], (
        "Entrada [opt_else, RP] ausente na tabela"
    )
    assert g['tabela'][('opt_else', 'RP')] == [EPSILON], (
        "opt_else com RP deveria produzir ε (sem ramo else)"
    )


def test_tabela_num_int_cont_res() -> None:
    g = construirGramatica()
    assert ('num_int_cont', 'KW_RES') in g['tabela'], (
        "Entrada [num_int_cont, KW_RES] ausente na tabela"
    )
    assert g['tabela'][('num_int_cont', 'KW_RES')] == ['KW_RES']


def test_tabela_stmt_list_eof() -> None:
    g = construirGramatica()
    assert ('stmt_list', EOF) in g['tabela'], (
        "Entrada [stmt_list, EOF] ausente na tabela"
    )
    assert g['tabela'][('stmt_list', EOF)] == [EPSILON]


def rodar_testes_gramatica() -> None:
    test_gramatica_retorna_estrutura_completa()
    test_first_terminais_sao_si_mesmos()
    test_first_arith_op()
    test_first_rel_op()
    test_first_stmt_inner()
    test_first_stmt_e_stmt_list()
    test_follow_stmt_inner()
    test_follow_stmt_list()
    test_follow_opt_else()
    test_tabela_sem_conflitos()
    test_tabela_entrada_valida_start()
    test_tabela_entrada_valida_end()
    test_tabela_entrada_valida_if()
    test_tabela_entrada_while()
    test_tabela_id_cont_epsilon()
    test_tabela_opt_else_epsilon()
    test_tabela_num_int_cont_res()
    test_tabela_stmt_list_eof()
    print("Todos os testes de construirGramatica passaram.")


# ─────────────────────────────────────────────────────────────
# Funções de teste — parsear (Aluno 2)
# ─────────────────────────────────────────────────────────────

def _tok(tipo: str, valor: str, linha: int = 1) -> dict:
    """Helper: cria um dict de token para testes."""
    return {'tipo': tipo, 'valor': valor, 'linha': linha}


def _prog(*grupos: list[dict]) -> list[dict]:
    """
    Helper: monta um programa completo com (START) ... (END) EOF.
    Cada argumento é uma lista de tokens representando um comando.
    """
    toks: list[dict] = [_tok('LP', '('), _tok('KW_START', 'START'), _tok('RP', ')')]
    for grupo in grupos:
        toks.extend(grupo)
    toks += [_tok('LP', '('), _tok('KW_END', 'END'), _tok('RP', ')'), _tok('EOF', '')]
    return toks


def _buscar_nt(no: dict, simbolo: str) -> dict | None:
    """Helper: busca em profundidade o primeiro nó NT com o símbolo dado."""
    if no.get('tipo') == 'NT' and no.get('simbolo') == simbolo:
        return no
    for filho in no.get('filhos', []):
        resultado = _buscar_nt(filho, simbolo)
        if resultado is not None:
            return resultado
    return None


def test_parsear_expressao_simples() -> None:
    g = construirGramatica()
    tokens = _prog([
        _tok('LP', '('), _tok('NUM_REAL', '3.14'), _tok('NUM_REAL', '2.0'),
        _tok('OP_ADD', '+'), _tok('RP', ')'),
    ])
    arvore = parsear(tokens, g)
    assert arvore['tipo'] == 'NT'
    assert arvore['simbolo'] == 'programa'
    # num_real_cont deve ter sido resolvido
    assert _buscar_nt(arvore, 'num_real_cont') is not None


def test_parsear_expressao_aninhada() -> None:
    g = construirGramatica()
    # ((3.0 4.0 *) 2.0 +)
    tokens = _prog([
        _tok('LP', '('),
        _tok('LP', '('), _tok('NUM_REAL', '3.0'), _tok('NUM_REAL', '4.0'),
        _tok('OP_MUL', '*'), _tok('RP', ')'),
        _tok('NUM_REAL', '2.0'), _tok('OP_ADD', '+'),
        _tok('RP', ')'),
    ])
    arvore = parsear(tokens, g)
    assert arvore['tipo'] == 'NT'
    # nested_cont não deve ser vazio (tem 2.0 e +)
    nc = _buscar_nt(arvore, 'nested_cont')
    assert nc is not None
    assert len(nc['filhos']) > 0


def test_parsear_store() -> None:
    g = construirGramatica()
    # (10.5 TEMP) — armazena 10.5 em TEMP
    tokens = _prog([
        _tok('LP', '('), _tok('NUM_REAL', '10.5'), _tok('ID', 'TEMP'), _tok('RP', ')'),
    ])
    arvore = parsear(tokens, g)
    # after_id_first_arg deve ter derivado ε (filhos vazios)
    no = _buscar_nt(arvore, 'after_id_first_arg')
    assert no is not None
    assert no['filhos'] == []


def test_parsear_load() -> None:
    g = construirGramatica()
    # (TEMP) — carrega valor de TEMP
    tokens = _prog([
        _tok('LP', '('), _tok('ID', 'TEMP'), _tok('RP', ')'),
    ])
    arvore = parsear(tokens, g)
    # id_cont deve ter derivado ε
    no = _buscar_nt(arvore, 'id_cont')
    assert no is not None
    assert no['filhos'] == []


def test_parsear_res() -> None:
    g = construirGramatica()
    # (3 RES)
    tokens = _prog([
        _tok('LP', '('), _tok('NUM_INT', '3'), _tok('KW_RES', 'RES'), _tok('RP', ')'),
    ])
    arvore = parsear(tokens, g)
    no = _buscar_nt(arvore, 'num_int_cont')
    assert no is not None
    assert len(no['filhos']) == 1
    assert no['filhos'][0]['valor'] == 'RES'


def test_parsear_if_com_else() -> None:
    g = construirGramatica()
    # (IF (X 5 >) (1.0 R) (0.0 R))
    tokens = _prog([
        _tok('LP', '('), _tok('KW_IF', 'IF'),
        _tok('LP', '('), _tok('ID', 'X'), _tok('NUM_INT', '5'),
        _tok('OP_GT', '>'), _tok('RP', ')'),
        _tok('LP', '('), _tok('NUM_REAL', '1.0'), _tok('ID', 'R'), _tok('RP', ')'),
        _tok('LP', '('), _tok('NUM_REAL', '0.0'), _tok('ID', 'R'), _tok('RP', ')'),
        _tok('RP', ')'),
    ])
    arvore = parsear(tokens, g)
    no_else = _buscar_nt(arvore, 'opt_else')
    assert no_else is not None
    assert len(no_else['filhos']) > 0, "opt_else deveria ter o ramo false"


def test_parsear_if_sem_else() -> None:
    g = construirGramatica()
    # (IF (X 5 >) (1.0 R))
    tokens = _prog([
        _tok('LP', '('), _tok('KW_IF', 'IF'),
        _tok('LP', '('), _tok('ID', 'X'), _tok('NUM_INT', '5'),
        _tok('OP_GT', '>'), _tok('RP', ')'),
        _tok('LP', '('), _tok('NUM_REAL', '1.0'), _tok('ID', 'R'), _tok('RP', ')'),
        _tok('RP', ')'),
    ])
    arvore = parsear(tokens, g)
    no_else = _buscar_nt(arvore, 'opt_else')
    assert no_else is not None
    assert no_else['filhos'] == [], "opt_else sem else deve ter filhos vazios (ε)"


def test_parsear_while() -> None:
    g = construirGramatica()
    # (WHILE (I 10 <) (I 1 +))
    tokens = _prog([
        _tok('LP', '('), _tok('KW_WHILE', 'WHILE'),
        _tok('LP', '('), _tok('ID', 'I'), _tok('NUM_INT', '10'),
        _tok('OP_LT', '<'), _tok('RP', ')'),
        _tok('LP', '('), _tok('ID', 'I'), _tok('NUM_INT', '1'),
        _tok('OP_ADD', '+'), _tok('RP', ')'),
        _tok('RP', ')'),
    ])
    arvore = parsear(tokens, g)
    # Verifica que KW_WHILE foi consumido
    def tem_token_while(no: dict) -> bool:
        if no.get('tipo') == 'TOKEN' and no.get('tipo_token') == 'KW_WHILE':
            return True
        return any(tem_token_while(f) for f in no.get('filhos', []))
    assert tem_token_while(arvore), "Token KW_WHILE deveria estar na árvore"


def test_parsear_programa_vazio() -> None:
    g = construirGramatica()
    # (START)(END) — programa sem comandos
    tokens = [
        _tok('LP', '('), _tok('KW_START', 'START'), _tok('RP', ')'),
        _tok('LP', '('), _tok('KW_END', 'END'), _tok('RP', ')'),
        _tok('EOF', ''),
    ]
    arvore = parsear(tokens, g)
    # stmt_list deve ter derivado ε logo no (END)
    no_list = _buscar_nt(arvore, 'stmt_list')
    assert no_list is not None


def test_parsear_todos_operadores() -> None:
    g = construirGramatica()
    # Operadores aritméticos: (NUM_REAL NUM_REAL op) — válido via num_real_cont
    arith_ops = [
        ('OP_ADD', '+'), ('OP_SUB', '-'), ('OP_MUL', '*'),
        ('OP_RDIV', '|'), ('OP_IDIV', '/'), ('OP_MOD', '%'), ('OP_POW', '^'),
    ]
    for tipo_op, val_op in arith_ops:
        tokens = _prog([
            _tok('LP', '('), _tok('NUM_REAL', '1.0'), _tok('NUM_REAL', '2.0'),
            _tok(tipo_op, val_op), _tok('RP', ')'),
        ])
        try:
            parsear(tokens, g)
        except SyntaxError as e:
            assert False, f"Operador aritmético '{val_op}' causou SyntaxError inesperado: {e}"
    # Operadores relacionais: (ID NUM_INT op) — válido via id_cont → NUM_INT any_op → rel_op
    rel_ops = [
        ('OP_GT', '>'), ('OP_LT', '<'), ('OP_EQ', '=='),
        ('OP_NEQ', '!='), ('OP_GTE', '>='), ('OP_LTE', '<='),
    ]
    for tipo_op, val_op in rel_ops:
        tokens = _prog([
            _tok('LP', '('), _tok('ID', 'X'), _tok('NUM_INT', '5'),
            _tok(tipo_op, val_op), _tok('RP', ')'),
        ])
        try:
            parsear(tokens, g)
        except SyntaxError as e:
            assert False, f"Operador relacional '{val_op}' causou SyntaxError inesperado: {e}"


def test_parsear_erro_token_inesperado() -> None:
    g = construirGramatica()
    # (A B + C) — depois do operador há ID 'C' em vez de ')'
    tokens = _prog([
        _tok('LP', '(', 2), _tok('ID', 'A', 2), _tok('ID', 'B', 2),
        _tok('OP_ADD', '+', 2), _tok('ID', 'C', 2), _tok('RP', ')', 2),
    ])
    try:
        parsear(tokens, g)
        assert False, "deveria ter levantado SyntaxError"
    except SyntaxError as e:
        assert '2' in str(e), f"Mensagem de erro deveria conter o número de linha: {e}"


def test_parsear_erro_paren_ausente() -> None:
    g = construirGramatica()
    # (3.14 2.0 +  — sem ')' final
    tokens = [
        _tok('LP', '('), _tok('KW_START', 'START'), _tok('RP', ')'),
        _tok('LP', '(', 2), _tok('NUM_REAL', '3.14', 2), _tok('NUM_REAL', '2.0', 2),
        _tok('OP_ADD', '+', 2),
        # RP ausente — próximo token é EOF
        _tok('EOF', '', 2),
    ]
    try:
        parsear(tokens, g)
        assert False, "deveria ter levantado SyntaxError"
    except SyntaxError as e:
        assert 'RP' in str(e) or 'EOF' in str(e), (
            f"Mensagem deveria mencionar RP ou EOF: {e}"
        )


def test_parsear_erro_operando_sem_operador() -> None:
    g = construirGramatica()
    # (3.14 2.0) — falta operador antes do ')'
    tokens = _prog([
        _tok('LP', '(', 2), _tok('NUM_REAL', '3.14', 2),
        _tok('NUM_REAL', '2.0', 2), _tok('RP', ')', 2),
    ])
    try:
        parsear(tokens, g)
        assert False, "deveria ter levantado SyntaxError"
    except SyntaxError:
        pass


def test_parsear_recuperacao_multiplos_erros() -> None:
    """Verifica que parsear com erros_out reporta múltiplos erros sem parar no primeiro."""
    g = construirGramatica()
    # Dois stmts com erro: falta operador antes de ')' — resulta em RP onde
    # arith_op é esperado
    tokens = _prog([
        _tok('LP', '(', 2), _tok('NUM_REAL', '3.14', 2),
        _tok('NUM_REAL', '2.0', 2), _tok('RP', ')', 2),   # erro: falta operador
        _tok('LP', '(', 3), _tok('NUM_REAL', '5.0', 3),
        _tok('NUM_REAL', '2.0', 3), _tok('RP', ')', 3),   # erro: falta operador
    ])
    erros: list[str] = []
    parsear(tokens, g, erros_out=erros)
    assert len(erros) >= 2, (
        f"Deveria encontrar ao menos 2 erros sintáticos, obteve {len(erros)}: {erros}"
    )
    # Cada mensagem deve conter número de linha
    for e in erros:
        assert any(c.isdigit() for c in e), (
            f"Mensagem de erro deveria conter número de linha: {e}"
        )


def test_parsear_mensagem_erro_contem_esperados() -> None:
    g = construirGramatica()
    # Token completamente inválido dentro de um stmt
    tokens = _prog([
        _tok('LP', '(', 2), _tok('EOF', '', 2),
    ])
    try:
        parsear(tokens, g)
        assert False, "deveria ter levantado SyntaxError"
    except SyntaxError as e:
        # A mensagem deve listar tokens esperados para stmt_inner
        assert 'Esperados' in str(e) or 'esperado' in str(e).lower(), (
            f"Mensagem deveria listar tokens esperados: {e}"
        )


def rodar_testes_parsear() -> None:
    test_parsear_expressao_simples()
    test_parsear_expressao_aninhada()
    test_parsear_store()
    test_parsear_load()
    test_parsear_res()
    test_parsear_if_com_else()
    test_parsear_if_sem_else()
    test_parsear_while()
    test_parsear_programa_vazio()
    test_parsear_todos_operadores()
    test_parsear_erro_token_inesperado()
    test_parsear_erro_paren_ausente()
    test_parsear_erro_operando_sem_operador()
    test_parsear_recuperacao_multiplos_erros()
    test_parsear_mensagem_erro_contem_esperados()
    print("Todos os testes de parsear passaram.")


# ─────────────────────────────────────────────────────────────
# Funções de teste — lerTokens (Aluno 3)
# ─────────────────────────────────────────────────────────────

import os
import tempfile


def _escrever_tmp(conteudo: str) -> str:
    """Escreve conteúdo em arquivo temporário e retorna o caminho."""
    fd, caminho = tempfile.mkstemp(suffix='.txt')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(conteudo)
    except Exception:
        os.close(fd)
        raise
    return caminho


def _apagar_tmp(caminho: str) -> None:
    try:
        os.remove(caminho)
    except OSError:
        pass


def test_lerTokens_lp_rp() -> None:
    cam = _escrever_tmp('( )')
    try:
        toks = lerTokens(cam)
        tipos = [t['tipo'] for t in toks]
        assert tipos[0] == 'LP',  f"Esperado LP, obteve {tipos[0]}"
        assert tipos[1] == 'RP',  f"Esperado RP, obteve {tipos[1]}"
        assert tipos[-1] == EOF,  "Último token deveria ser EOF"
    finally:
        _apagar_tmp(cam)


def test_lerTokens_num_int() -> None:
    cam = _escrever_tmp('42')
    try:
        toks = lerTokens(cam)
        assert toks[0]['tipo'] == 'NUM_INT',  f"Tipo errado: {toks[0]['tipo']}"
        assert toks[0]['valor'] == '42',      f"Valor errado: {toks[0]['valor']}"
    finally:
        _apagar_tmp(cam)


def test_lerTokens_num_real() -> None:
    cam = _escrever_tmp('3.14')
    try:
        toks = lerTokens(cam)
        assert toks[0]['tipo'] == 'NUM_REAL',  f"Tipo errado: {toks[0]['tipo']}"
        assert toks[0]['valor'] == '3.14',     f"Valor errado: {toks[0]['valor']}"
    finally:
        _apagar_tmp(cam)


def test_lerTokens_operadores_aritm() -> None:
    esperados = [('+','OP_ADD'), ('-','OP_SUB'), ('*','OP_MUL'),
                 ('|','OP_RDIV'), ('/','OP_IDIV'), ('%','OP_MOD'), ('^','OP_POW')]
    for valor, tipo in esperados:
        cam = _escrever_tmp(valor)
        try:
            toks = lerTokens(cam)
            assert toks[0]['tipo'] == tipo, (
                f"Operador '{valor}': esperado {tipo}, obteve {toks[0]['tipo']}"
            )
        finally:
            _apagar_tmp(cam)


def test_lerTokens_operadores_rel() -> None:
    esperados = [('>', 'OP_GT'), ('<', 'OP_LT'), ('==', 'OP_EQ'),
                 ('!=', 'OP_NEQ'), ('>=', 'OP_GTE'), ('<=', 'OP_LTE')]
    for valor, tipo in esperados:
        cam = _escrever_tmp(valor)
        try:
            toks = lerTokens(cam)
            assert toks[0]['tipo'] == tipo, (
                f"Operador '{valor}': esperado {tipo}, obteve {toks[0]['tipo']}"
            )
            assert toks[0]['valor'] == valor, (
                f"Valor errado para '{valor}': {toks[0]['valor']}"
            )
        finally:
            _apagar_tmp(cam)


def test_lerTokens_keywords() -> None:
    kws = [('START','KW_START'), ('END','KW_END'), ('IF','KW_IF'),
           ('WHILE','KW_WHILE'), ('RES','KW_RES')]
    for valor, tipo in kws:
        cam = _escrever_tmp(valor)
        try:
            toks = lerTokens(cam)
            assert toks[0]['tipo'] == tipo, (
                f"Keyword '{valor}': esperado {tipo}, obteve {toks[0]['tipo']}"
            )
        finally:
            _apagar_tmp(cam)


def test_lerTokens_identificador() -> None:
    cam = _escrever_tmp('CONTADOR')
    try:
        toks = lerTokens(cam)
        assert toks[0]['tipo'] == 'ID',       f"Tipo errado: {toks[0]['tipo']}"
        assert toks[0]['valor'] == 'CONTADOR', f"Valor errado: {toks[0]['valor']}"
    finally:
        _apagar_tmp(cam)


def test_lerTokens_linha_correta() -> None:
    cam = _escrever_tmp('(\n(\n3.14')
    try:
        toks = lerTokens(cam)
        assert toks[0]['linha'] == 1, f"1.º token deveria ser linha 1, obteve {toks[0]['linha']}"
        assert toks[1]['linha'] == 2, f"2.º token deveria ser linha 2, obteve {toks[1]['linha']}"
        assert toks[2]['linha'] == 3, f"3.º token deveria ser linha 3, obteve {toks[2]['linha']}"
    finally:
        _apagar_tmp(cam)


def test_lerTokens_eof_sempre_presente() -> None:
    for conteudo in ('', '  ', '( )'):
        cam = _escrever_tmp(conteudo)
        try:
            toks = lerTokens(cam)
            assert toks[-1]['tipo'] == EOF, (
                f"EOF ausente para conteúdo '{conteudo}': {toks}"
            )
        finally:
            _apagar_tmp(cam)


def test_lerTokens_programa_completo() -> None:
    prog = '(START)\n(3.14 2.0 +)\n(END)\n'
    cam = _escrever_tmp(prog)
    try:
        toks = lerTokens(cam)
        tipos = [t['tipo'] for t in toks]
        assert tipos[0] == 'LP'
        assert tipos[1] == 'KW_START'
        assert tipos[2] == 'RP'
        assert tipos[3] == 'LP'
        assert tipos[4] == 'NUM_REAL'
        assert tipos[5] == 'NUM_REAL'
        assert tipos[6] == 'OP_ADD'
        assert tipos[7] == 'RP'
        assert tipos[-1] == EOF
    finally:
        _apagar_tmp(cam)


def test_lerTokens_erro_char_invalido() -> None:
    cam = _escrever_tmp('(3.0 @)')
    try:
        lerTokens(cam)
        assert False, "deveria ter levantado ValueError"
    except ValueError as e:
        assert '1' in str(e), f"Mensagem deveria conter número de linha: {e}"
    finally:
        _apagar_tmp(cam)


def test_lerTokens_erro_excl_isolado() -> None:
    cam = _escrever_tmp('(A ! B)')
    try:
        lerTokens(cam)
        assert False, "deveria ter levantado ValueError"
    except ValueError as e:
        assert '!' in str(e), f"Mensagem deveria mencionar '!': {e}"
    finally:
        _apagar_tmp(cam)


def test_lerTokens_erro_numero_invalido() -> None:
    for num in ('3.14.5', '1.'):
        cam = _escrever_tmp(num)
        try:
            lerTokens(cam)
            assert False, f"Deveria falhar para número inválido '{num}'"
        except ValueError:
            pass
        finally:
            _apagar_tmp(cam)


def test_lerTokens_arquivo_inexistente() -> None:
    try:
        lerTokens('arquivo_que_nao_existe_xyz_123.txt')
        assert False, "deveria ter levantado FileNotFoundError"
    except FileNotFoundError:
        pass


def test_lerTokens_recuperacao() -> None:
    """Verifica que lerTokens com erros_out continua após caractere inválido."""
    # Dois caracteres inválidos na mesma entrada
    cam = _escrever_tmp('(3.0 @ 2.0 # +)')
    try:
        erros: list[str] = []
        toks = lerTokens(cam, erros_out=erros)
        assert len(erros) >= 2, (
            f"Deveria ter ao menos 2 erros léxicos, obteve {len(erros)}: {erros}"
        )
        # Mensagens devem conter número de linha e o caractere problemático
        assert any('@' in e or 'inválido' in e.lower() for e in erros), (
            f"Mensagem deveria mencionar '@': {erros}"
        )
        assert any('#' in e or 'inválido' in e.lower() for e in erros), (
            f"Mensagem deveria mencionar '#': {erros}"
        )
        # Tokens válidos ainda presentes: LP, os números e RP
        tipos = [t['tipo'] for t in toks]
        assert 'LP' in tipos, "LP deveria estar presente após recuperação"
        assert 'NUM_REAL' in tipos, "NUM_REAL deveria estar presente"
        assert EOF in tipos, "EOF deveria estar ao final"
    finally:
        _apagar_tmp(cam)


def test_lerTokens_fase2_teste1() -> None:
    toks = lerTokens('teste1.txt')
    tipos = [t['tipo'] for t in toks]
    assert 'KW_START' in tipos,  "teste1.txt deveria ter START"
    assert 'KW_END'   in tipos,  "teste1.txt deveria ter END"
    assert 'KW_IF'    in tipos,  "teste1.txt deveria ter IF"
    assert 'KW_WHILE' in tipos,  "teste1.txt deveria ter WHILE"
    assert 'OP_RDIV'  in tipos,  "teste1.txt deveria ter | (OP_RDIV)"
    assert 'OP_IDIV'  in tipos,  "teste1.txt deveria ter / (OP_IDIV)"
    assert 'OP_GT'    in tipos,  "teste1.txt deveria ter >"
    assert 'OP_LT'    in tipos,  "teste1.txt deveria ter <"
    assert tipos[-1]  == EOF,    "Último token deveria ser EOF"


def rodar_testes_lerTokens() -> None:
    test_lerTokens_lp_rp()
    test_lerTokens_num_int()
    test_lerTokens_num_real()
    test_lerTokens_operadores_aritm()
    test_lerTokens_operadores_rel()
    test_lerTokens_keywords()
    test_lerTokens_identificador()
    test_lerTokens_linha_correta()
    test_lerTokens_eof_sempre_presente()
    test_lerTokens_programa_completo()
    test_lerTokens_erro_char_invalido()
    test_lerTokens_erro_excl_isolado()
    test_lerTokens_erro_numero_invalido()
    test_lerTokens_arquivo_inexistente()
    test_lerTokens_recuperacao()
    test_lerTokens_fase2_teste1()
    print("Todos os testes de lerTokens passaram.")


# ─────────────────────────────────────────────────────────────
# Ponto de entrada
# ─────────────────────────────────────────────────────────────

if __name__ == '__main__':
    if len(sys.argv) == 2 and sys.argv[1] == '--test-gramatica':
        rodar_testes_gramatica()
    elif len(sys.argv) == 2 and sys.argv[1] == '--test-parsear':
        rodar_testes_parsear()
    elif len(sys.argv) == 2 and sys.argv[1] == '--test-lerTokens':
        rodar_testes_lerTokens()
    else:
        main()
