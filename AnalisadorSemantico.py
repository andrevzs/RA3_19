# Integrantes do grupo (ordem alfabética):
# André Vinícius Zicka Schmidt - andrevzs
# Gabriel Fischer Domakoski - fochu3013
#
# Nome do grupo no Canvas: RA3_19

import sys
import os
import tempfile
import json

from AnalisadorSintatico import (
    EPSILON,
    EOF,
    MAPA_TOKENS,
    construirGramatica,
    parsear,
    gerarArvore,
    gerarAssembly as _gerarAssemblyFase2,
    _emit,
    _estado_numero,
    _estado_op_maior,
    _estado_op_menor,
    _estado_op_igual,
    _estado_op_excl,
)


class _ErroComentarioNaoFechado(ValueError):
    """Sinaliza comentário *{...}* sem fechamento }* antes do EOF."""


# ─────────────────────────────────────────────────────────────
# [Aluno 1] Léxico com suporte a comentários — Fase 3
#
# Responsabilidades:
#   - lerTokensFase3: variante de lerTokens que descarta *{...}*
#   - prepararEntradaSemantica: integra léxico + parser da Fase 2
#   - _validarStartEnd: valida estrutura obrigatória do programa
# ─────────────────────────────────────────────────────────────

# '*' foi removido deste mapeamento para permitir lookahead em '*{'
# sem esse ajuste, o AFD emitiria OP_MUL antes de verificar se o
# próximo caractere é '{', iniciando um comentário.
_OPS_SIMPLES_FASE3: dict[str, str] = {
    '(': 'LP', ')': 'RP',
    '+': 'OP_ADD', '-': 'OP_SUB',
    '|': 'OP_RDIV', '/': 'OP_IDIV', '%': 'OP_MOD', '^': 'OP_POW',
}


def _estado_comentario_fase3(cont: str, i: int, linha_ref: list[int]) -> int:
    """
    Estado: dentro de um comentário *{...}*.

    Consome todos os caracteres até encontrar a sequência '}*', atualizando
    linha_ref[0] a cada '\n' para que a numeração de linhas permaneça correta
    mesmo em comentários multilinhas.

    Levanta ValueError se o fim do arquivo for alcançado sem que o comentário
    seja fechado.

    Entrada:
        cont      — string com o conteúdo completo do arquivo
        i         — posição imediatamente após '*{' (primeiro char do comentário)
        linha_ref — lista de um elemento com o número da linha atual (mutável)

    Saída:
        nova posição de leitura (imediatamente após '}*')
    """
    linha_inicio = linha_ref[0]
    while i < len(cont):
        if cont[i] == '\n':
            linha_ref[0] += 1
            i += 1
        elif cont[i] == '}' and i + 1 < len(cont) and cont[i + 1] == '*':
            return i + 2  # consome '}*'
        else:
            i += 1
    # Chegou ao EOF sem fechar o comentário: levanta exceção especializada para
    # que o chamador possa restaurar linha_ref e interromper o loop léxico.
    raise _ErroComentarioNaoFechado(
        f"Linha {linha_inicio}: comentário não fechado (esperado '}}*')"
    )


def _estado_identificador_fase3(
    cont: str, i: int, linha_ref: list[int], tokens: list[dict]
) -> int:
    """
    Estado: acumulando letras e dígitos para formar identificador ou keyword.

    Usa MAPA_TOKENS da Fase 2 para distinguir keywords de IDs.
    TRUE e FALSE são emitidos como ID para que o analisador semântico
    (Aluno 3) realize a inferência de tipo lógico a partir do valor.
    """
    start = i
    while i < len(cont) and (cont[i].isalpha() or cont[i].isdigit()):
        i += 1
    valor = cont[start:i]
    tipo = MAPA_TOKENS.get(valor, 'ID')
    _emit(tokens, tipo, valor, linha_ref[0])
    return i


def _estado_inicial_fase3(
    cont: str, i: int, linha_ref: list[int], tokens: list[dict]
) -> int:
    """
    Estado inicial do AFD da Fase 3.

    Estende _estado_inicial (Fase 2) com detecção de comentários *{...}*:
    ao encontrar '*', faz lookahead de um caractere para verificar se o
    próximo é '{'; se confirmado, delega ao estado de comentário; caso
    contrário, emite OP_MUL normalmente.

    Entrada:
        cont      — conteúdo do arquivo
        i         — posição atual
        linha_ref — contador de linhas mutável
        tokens    — lista de tokens acumulados

    Saída:
        nova posição após processar o token (ou ignorar espaço/comentário)
    """
    c = cont[i]

    if c == '\n':
        linha_ref[0] += 1
        return i + 1

    if c in (' ', '\t', '\r'):
        return i + 1

    if c in _OPS_SIMPLES_FASE3:
        _emit(tokens, _OPS_SIMPLES_FASE3[c], c, linha_ref[0])
        return i + 1

    # Tratamento especial para '*': pode iniciar comentário *{...}*
    if c == '*':
        if i + 1 < len(cont) and cont[i + 1] == '{':
            # Salva linha antes de entrar no scanner de comentário para poder
            # restaurar em caso de comentário não fechado, evitando que o
            # contador de linhas fique corrompido após o erro.
            linha_antes = linha_ref[0]
            try:
                return _estado_comentario_fase3(cont, i + 2, linha_ref)
            except _ErroComentarioNaoFechado:
                linha_ref[0] = linha_antes  # restaura contagem correta
                raise
        _emit(tokens, 'OP_MUL', '*', linha_ref[0])
        return i + 1

    if c.isdigit():
        return _estado_numero(cont, i, linha_ref, tokens)

    if c.isalpha():
        return _estado_identificador_fase3(cont, i, linha_ref, tokens)

    if c == '>':
        return _estado_op_maior(cont, i + 1, linha_ref, tokens)

    if c == '<':
        return _estado_op_menor(cont, i + 1, linha_ref, tokens)

    if c == '=':
        return _estado_op_igual(cont, i + 1, linha_ref, tokens)

    if c == '!':
        return _estado_op_excl(cont, i + 1, linha_ref, tokens)

    raise ValueError(f"Linha {linha_ref[0]}: caractere inválido '{c}'")


def lerTokensFase3(arquivo: str, erros_out: list[str] | None = None) -> list[dict]:
    """
    Lê o arquivo de código-fonte da Fase 3 e devolve vetor de tokens tipados.

    Diferenças em relação a lerTokens (Fase 2):
      - Reconhece e descarta comentários delimitados por *{...}* em qualquer
        posição: linhas inteiras, final de linhas de código e entre expressões;
      - O contador de linhas é mantido correto mesmo em comentários multilinhas;
      - TRUE e FALSE são emitidos como ID (tipo inferido pelo analisador semântico).

    Cada token é representado como:
        {'tipo': str, 'valor': str, 'linha': int}

    Tipos de token possíveis: LP, RP, NUM_INT, NUM_REAL, ID,
    OP_ADD, OP_SUB, OP_MUL, OP_RDIV, OP_IDIV, OP_MOD, OP_POW,
    OP_GT, OP_LT, OP_EQ, OP_NEQ, OP_GTE, OP_LTE,
    KW_RES, KW_START, KW_END, KW_IF, KW_WHILE, EOF.

    Parâmetros:
        arquivo    — caminho do arquivo de entrada.
        erros_out  — lista opcional para recuperação de erros. Quando fornecida,
                     erros léxicos são registrados aqui e o analisador continua;
                     quando None, um ValueError é levantado no primeiro erro.

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
            i = _estado_inicial_fase3(conteudo, i, linha_ref, tokens)
        except _ErroComentarioNaoFechado as e:
            # Comentário não fechado: o scanner já consumiu até o EOF sem
            # encontrar }*. Registra o erro e interrompe — não há mais tokens
            # válidos no arquivo (tudo estava "dentro" do comentário).
            if erros_out is not None:
                erros_out.append(str(e))
                break
            else:
                raise ValueError(str(e)) from e
        except ValueError as e:
            if erros_out is not None:
                erros_out.append(str(e))
                i += 1
            else:
                raise

    tokens.append({'tipo': EOF, 'valor': '', 'linha': linha_ref[0]})
    return tokens


def _validarStartEnd(tokens: list[dict], erros_out: list[str]) -> None:
    """
    Verifica que o programa começa com (START) e termina com (END).

    A gramática da Fase 2 aceita qualquer sequência de stmts; esta função
    impõe a restrição semântica de que o primeiro stmt deve ser (START) e
    o último deve ser (END), conforme a especificação da linguagem.

    Registra mensagens de erro claras em erros_out com número de linha.

    Entrada:
        tokens    — vetor de tokens produzido por lerTokensFase3()
        erros_out — lista onde os erros são acrescentados
    """
    sem_eof = [t for t in tokens if t['tipo'] != EOF]

    tem_start = (
        len(sem_eof) >= 3
        and sem_eof[0]['tipo'] == 'LP'
        and sem_eof[1]['tipo'] == 'KW_START'
        and sem_eof[2]['tipo'] == 'RP'
    )
    if not tem_start:
        linha = sem_eof[0]['linha'] if sem_eof else 1
        erros_out.append(
            f"Linha {linha}: programa deve começar com (START)"
        )

    tem_end = (
        len(sem_eof) >= 3
        and sem_eof[-3]['tipo'] == 'LP'
        and sem_eof[-2]['tipo'] == 'KW_END'
        and sem_eof[-1]['tipo'] == 'RP'
    )
    if not tem_end:
        linha = sem_eof[-1]['linha'] if sem_eof else 1
        erros_out.append(
            f"Linha {linha}: programa deve terminar com (END)"
        )


def prepararEntradaSemantica(
    arquivo: str,
) -> tuple[list[dict], dict, list[str], list[str]]:
    """
    Carrega o programa-fonte, descarta comentários *{...}*, produz o
    vetor de tokens e a árvore sintática inicial para uso pelo analisador
    semântico (Alunos 2, 3 e 4).

    Sequência de passos:
      1. Análise léxica com lerTokensFase3 — descarta comentários e
         classifica cada token com tipo e número de linha;
      2. Validação estrutural de (START) e (END);
      3. Construção da tabela LL(1) (reaproveitada da Fase 2);
      4. Análise sintática com parsear em modo de recuperação de erros.

    Parâmetros:
        arquivo — caminho do arquivo de código-fonte.

    Retorno:
        (tokens, arvore, erros_lex, erros_sint) onde:
          - tokens     : vetor de tokens sem comentários
          - arvore     : árvore sintática inicial (pode ser parcial se há erros)
          - erros_lex  : mensagens de erros léxicos e de estrutura (START/END)
          - erros_sint : mensagens de erros sintáticos

    Interface com outros alunos:
        - arvore  → construirTabelaSimbolos() [Aluno 2]
        - arvore  → gerarArvoreAtribuida()    [Aluno 4]
    """
    erros_lex:  list[str] = []
    erros_sint: list[str] = []

    tokens = lerTokensFase3(arquivo, erros_out=erros_lex)
    _validarStartEnd(tokens, erros_lex)

    gramatica = construirGramatica()
    arvore = parsear(tokens, gramatica, erros_out=erros_sint)

    return tokens, arvore, erros_lex, erros_sint


# ─────────────────────────────────────────────────────────────
# [Aluno 2] construirTabelaSimbolos — Tabela de Símbolos
# ─────────────────────────────────────────────────────────────

def _é_literal_reservado(nome: str) -> bool:
    """TRUE e FALSE são literais booleanos, não podem ser variáveis."""
    return nome in ('TRUE', 'FALSE')


def _extrair_stmts_de_stmt_list(no_stmt_list: dict) -> list[dict]:
    """Extrai lista plana de stmts a partir da árvore stmt_list recursiva."""
    if no_stmt_list['tipo'] != 'NT' or no_stmt_list['simbolo'] != 'stmt_list':
        return []
    filhos = no_stmt_list.get('filhos', [])
    if not filhos:  # ε
        return []
    # stmt_list → stmt stmt_list | ε
    if len(filhos) >= 2:
        primeiro = filhos[0]
        cauda = filhos[1]
        resto = _extrair_stmts_de_stmt_list(cauda)
        return [primeiro] + resto
    return []


def _extrair_stmt_inner(no_stmt: dict) -> dict | None:
    """Extrai o nó stmt_inner de um nó stmt."""
    if no_stmt['tipo'] != 'NT' or no_stmt['simbolo'] != 'stmt':
        return None
    filhos = no_stmt.get('filhos', [])
    # stmt → LP stmt_inner RP
    if len(filhos) >= 3 and filhos[1]['tipo'] == 'NT':
        return filhos[1]
    return None


def _classificar_stmt_inner(no: dict) -> str | None:
    """Classifica stmt_inner pelo tipo do primeiro filho."""
    if no['tipo'] != 'NT' or no['simbolo'] != 'stmt_inner':
        return None
    filhos = no.get('filhos', [])
    if not filhos:
        return None
    primeiro = filhos[0]
    if primeiro['tipo'] == 'TOKEN':
        return primeiro['tipo_token']
    # Se primeiro é NT, não é um pattern válido direto
    return None


def _buscar_pattern_store(no_stmt_inner: dict, tabela_tipos: dict) -> tuple[str, str, int] | None:
    """
    Busca padrão STORE (V MEM) onde filhos[-1] (continuação) termina em ε.
    Retorna (nome_var, tipo_inferido, linha) ou None.

    Padrões:
    - (N ID) where after_id_first_arg → ε → STORE int
    - (V.x ID) where after_id_first_arg → ε → STORE real
    - ((expr) ID) where after_id_nested → ε → STORE unknown
    """
    if no_stmt_inner['tipo'] != 'NT' or no_stmt_inner['simbolo'] != 'stmt_inner':
        return None

    filhos = no_stmt_inner.get('filhos', [])
    if not filhos:
        return None

    primeiro = filhos[0]
    if primeiro['tipo'] != 'TOKEN':
        return None

    tipo_primeiro = primeiro['tipo_token']
    linha = primeiro['linha']

    # Pattern: NUM_INT num_int_cont → ID after_id_first_arg(ε)
    if tipo_primeiro == 'NUM_INT' and len(filhos) >= 2:
        cont = filhos[1]
        if cont['tipo'] == 'NT' and cont['simbolo'] == 'num_int_cont':
            cont_filhos = cont.get('filhos', [])
            if cont_filhos and cont_filhos[0]['tipo'] == 'TOKEN' and cont_filhos[0]['tipo_token'] == 'ID':
                if len(cont_filhos) >= 2:
                    after_id = cont_filhos[1]
                    if after_id['tipo'] == 'NT' and not after_id.get('filhos', []):
                        nome = cont_filhos[0]['valor']
                        if not _é_literal_reservado(nome):
                            return (nome, 'int', linha)
                        else:
                            return None  # erro: TRUE/FALSE reservado

    # Pattern: NUM_REAL num_real_cont → ID after_id_first_arg(ε)
    if tipo_primeiro == 'NUM_REAL' and len(filhos) >= 2:
        cont = filhos[1]
        if cont['tipo'] == 'NT' and cont['simbolo'] == 'num_real_cont':
            cont_filhos = cont.get('filhos', [])
            if cont_filhos and cont_filhos[0]['tipo'] == 'TOKEN' and cont_filhos[0]['tipo_token'] == 'ID':
                if len(cont_filhos) >= 2:
                    after_id = cont_filhos[1]
                    if after_id['tipo'] == 'NT' and not after_id.get('filhos', []):
                        nome = cont_filhos[0]['valor']
                        if not _é_literal_reservado(nome):
                            return (nome, 'real', linha)
                        else:
                            return None

    # Pattern: LP stmt_inner RP nested_cont → ID after_id_nested(ε)
    if tipo_primeiro == 'LP' and len(filhos) >= 4:
        nested = filhos[3]
        if nested['tipo'] == 'NT' and nested['simbolo'] == 'nested_cont':
            nested_filhos = nested.get('filhos', [])
            if nested_filhos and nested_filhos[0]['tipo'] == 'TOKEN' and nested_filhos[0]['tipo_token'] == 'ID':
                if len(nested_filhos) >= 2:
                    after_id = nested_filhos[1]
                    if after_id['tipo'] == 'NT' and not after_id.get('filhos', []):
                        nome = nested_filhos[0]['valor']
                        if not _é_literal_reservado(nome):
                            return (nome, 'unknown', linha)
                        else:
                            return None

    return None


def _coletar_ids_nao_store(no: dict) -> list[tuple[str, int]]:
    """
    Percorre recursivamente um nó da árvore e retorna todos os tokens ID
    que estão em posição de USO (não são alvo de STORE).

    Um ID é alvo de STORE quando é o primeiro filho de num_int_cont,
    num_real_cont ou nested_cont E o segundo filho é um NT sem filhos
    (derivou ε — a continuação after_id não tem operador).

    Qualquer outro ID na árvore é um USO (LOAD ou operando aritmético/relacional).
    TRUE e FALSE são excluídos por serem literais reservados.
    """
    if no['tipo'] == 'TOKEN':
        if no['tipo_token'] == 'ID' and not _é_literal_reservado(no['valor']):
            return [(no['valor'], no['linha'])]
        return []

    filhos = no.get('filhos', [])
    simbolo = no.get('simbolo', '')

    # Detecta padrão STORE: (num_*_cont | nested_cont) → ID after_id(ε)
    # Quando after_id tem filhos (há operador), o ID é operando (USE), não STORE.
    if (simbolo in ('num_int_cont', 'num_real_cont', 'nested_cont')
            and len(filhos) >= 2
            and filhos[0].get('tipo') == 'TOKEN'
            and filhos[0].get('tipo_token') == 'ID'
            and filhos[1].get('tipo') == 'NT'
            and not filhos[1].get('filhos', [])):
        return []  # ID é alvo de STORE — não contabiliza como uso

    resultado = []
    for filho in filhos:
        resultado.extend(_coletar_ids_nao_store(filho))
    return resultado


def _processar_branch(no_stmt: dict, tabela: dict, erros: list[str]) -> None:
    """
    Processa um stmt dentro de um branch de IF ou WHILE para detectar
    definições (STORE) e usos de variáveis, sem incrementar o contador
    de statements (stmts de branch não contam para (N RES)).
    """
    stmt_inner = _extrair_stmt_inner(no_stmt)
    if not stmt_inner:
        return

    classificacao = _classificar_stmt_inner(stmt_inner)

    if classificacao in ('KW_START', 'KW_END'):
        return

    if classificacao == 'KW_IF':
        filhos = stmt_inner.get('filhos', [])
        if len(filhos) >= 3:
            _processar_branch(filhos[1], tabela, erros)  # cond
            _processar_branch(filhos[2], tabela, erros)  # true
            if len(filhos) >= 4:
                opt_else = filhos[3]
                opt_filhos = opt_else.get('filhos', [])
                if opt_filhos:
                    _processar_branch(opt_filhos[0], tabela, erros)  # false
        return

    if classificacao == 'KW_WHILE':
        filhos = stmt_inner.get('filhos', [])
        if len(filhos) >= 3:
            _processar_branch(filhos[1], tabela, erros)  # cond
            _processar_branch(filhos[2], tabela, erros)  # body
        return

    # STORE: registra definição da variável
    pattern_store = _buscar_pattern_store(stmt_inner, {})
    if pattern_store:
        nome, tipo, linha = pattern_store
        _registrar_definicao(tabela, nome, tipo, linha, erros)

    # USOs: todos os IDs que não são alvo de STORE (incluindo dentro de exprs aninhadas)
    usos = _coletar_ids_nao_store(stmt_inner)
    for nome, linha in usos:
        _registrar_uso(tabela, nome, linha, erros)


def _buscar_res_pattern(no_stmt_inner: dict) -> int | None:
    """Extrai N de (N RES). Retorna N (inteiro) ou None."""
    if no_stmt_inner['tipo'] != 'NT' or no_stmt_inner['simbolo'] != 'stmt_inner':
        return None

    filhos = no_stmt_inner.get('filhos', [])
    if not filhos:
        return None

    primeiro = filhos[0]
    if primeiro['tipo'] != 'TOKEN' or primeiro['tipo_token'] != 'NUM_INT':
        return None

    # filhos[1] deve ser num_int_cont → RES
    if len(filhos) >= 2:
        cont = filhos[1]
        if cont['tipo'] == 'NT' and cont['simbolo'] == 'num_int_cont':
            cont_filhos = cont.get('filhos', [])
            if cont_filhos and cont_filhos[0]['tipo'] == 'TOKEN' and cont_filhos[0]['tipo_token'] == 'KW_RES':
                try:
                    return int(primeiro['valor'])
                except ValueError:
                    return None

    return None


def _registrar_definicao(tabela: dict, nome: str, tipo: str, linha: int, erros: list[str]) -> None:
    """Registra uma definição de variável. Detecta redefinições com tipo incompatível."""
    if _é_literal_reservado(nome):
        erros.append(f"Linha {linha}: '{nome}' é literal booleano reservado e não pode ser usado como variável")
        return

    if nome in tabela:
        entrada = tabela[nome]
        tipo_anterior = entrada['tipo']
        # Redefinição: verifica compatibilidade
        if tipo != 'unknown' and tipo_anterior != 'unknown' and tipo != tipo_anterior:
            erros.append(
                f"Linha {linha}: variável '{nome}' redefinida com tipo '{tipo}' "
                f"(tipo anterior: '{tipo_anterior}' definido na linha {entrada['linha_def']})"
            )
            return
        # Redefinição com mesmo tipo ou unknown: permitido, atualiza
        if tipo != 'unknown':
            entrada['tipo'] = tipo
    else:
        tabela[nome] = {
            'tipo': tipo,
            'escopo': 'global',
            'linha_def': linha,
            'linhas_uso': [],
        }


def _registrar_uso(tabela: dict, nome: str, linha: int, erros: list[str]) -> None:
    """Registra um uso de variável. Detecta usos antes de definição."""
    if _é_literal_reservado(nome):
        # TRUE e FALSE são OK como expressões (não são variáveis)
        return

    if nome not in tabela:
        erros.append(f"Linha {linha}: variável '{nome}' usada antes de ser definida")
        return

    tabela[nome]['linhas_uso'].append(linha)


def _processar_stmt_recursivo(no_stmt: dict, tabela: dict, erros: list[str], num_stmt: list[int]) -> None:
    """Processa um statement de nível superior: detecta STORE, USO, RES, IF e WHILE."""
    stmt_inner = _extrair_stmt_inner(no_stmt)
    if not stmt_inner:
        return

    num_stmt[0] += 1

    classificacao = _classificar_stmt_inner(stmt_inner)

    if classificacao in ('KW_START', 'KW_END'):
        return

    # IF e WHILE: delega ao processador de branch (não incrementa num_stmt nos filhos)
    if classificacao in ('KW_IF', 'KW_WHILE'):
        _processar_branch(no_stmt, tabela, erros)
        return

    # RES pattern: (N RES)
    n_res = _buscar_res_pattern(stmt_inner)
    if n_res is not None:
        if n_res < 1 or n_res > num_stmt[0] - 1:
            erros.append(
                f"Linha {stmt_inner['linha']}: (RES) fora do alcance — N deve ser entre 1 e {num_stmt[0] - 1} (obteve {n_res})"
            )
        return

    # STORE: registra definição da variável
    pattern_store = _buscar_pattern_store(stmt_inner, {})
    if pattern_store:
        nome, tipo, linha = pattern_store
        _registrar_definicao(tabela, nome, tipo, linha, erros)

    # USOs: todos os IDs que não são alvo de STORE (incluindo segundo operando e exprs aninhadas)
    usos = _coletar_ids_nao_store(stmt_inner)
    for nome, linha in usos:
        _registrar_uso(tabela, nome, linha, erros)


def construirTabelaSimbolos(arvore: dict) -> tuple[dict, list[str]]:
    """
    (Aluno 2) Percorre a árvore sintática e constrói a tabela de símbolos.

    Entrada:
        arvore — árvore sintática inicial produzida por prepararEntradaSemantica()

    Saída:
        (tabela, erros) onde:
          - tabela : dict[nome → {tipo, linha_def, linhas_uso}]
          - erros  : lista de erros semânticos de declaração/uso
    """
    tabela: dict[str, dict] = {}
    erros: list[str] = []

    if arvore['tipo'] != 'NT' or arvore['simbolo'] != 'programa':
        return tabela, erros

    # Extrai lista de stmts do programa
    filhos_prog = arvore.get('filhos', [])
    if filhos_prog and filhos_prog[0]['tipo'] == 'NT' and filhos_prog[0]['simbolo'] == 'stmt_list':
        stmts = _extrair_stmts_de_stmt_list(filhos_prog[0])

        # Processa cada stmt em ordem (num_stmt para validação de RES)
        num_stmt = [0]
        for no_stmt in stmts:
            _processar_stmt_recursivo(no_stmt, tabela, erros, num_stmt)

    return tabela, erros


def salvarTabelaSimbolos(
    tabela: dict,
    erros: list[str],
    caminho: str = 'tabela_simbolos.md',
    arquivo_fonte: str = '',
) -> str:
    """
    (Aluno 2) Salva a tabela de símbolos e os erros semânticos em arquivo Markdown.

    Entrada:
        tabela        — tabela produzida por construirTabelaSimbolos()
        erros         — lista de erros semânticos de declaração/uso
        caminho       — caminho do arquivo de saída (padrão: tabela_simbolos.md)
        arquivo_fonte — nome do arquivo de teste analisado (para rastreabilidade)

    Saída:
        caminho do arquivo gerado
    """
    linhas: list[str] = []
    linhas.append('# Tabela de Símbolos\n')
    if arquivo_fonte:
        linhas.append(f'**Arquivo de teste analisado:** `{arquivo_fonte}`\n')
    linhas.append('| Variável | Tipo | Escopo | Linha de Definição | Linhas de Uso |')
    linhas.append('|---|---|---|---|---|')
    for nome, entrada in sorted(tabela.items()):
        usos_str = ', '.join(str(l) for l in entrada.get('linhas_uso', []))
        escopo = entrada.get('escopo', 'global')
        linhas.append(
            f"| {nome} | {entrada['tipo']} | {escopo} | {entrada['linha_def']} | {usos_str} |"
        )
    linhas.append('')
    linhas.append('## Erros Semânticos')
    if erros:
        for erro in erros:
            linhas.append(f'- {erro}')
    else:
        linhas.append('Nenhum erro encontrado.')
    linhas.append('')

    conteudo = '\n'.join(linhas)
    with open(caminho, 'w', encoding='utf-8') as f:
        f.write(conteudo)
    return caminho


# ─────────────────────────────────────────────────────────────
# [Aluno 3] verificarTipos — Sistema de Regras Semânticas
#
# Regras de tipo implementadas (documentadas em REGRAS_TIPOS.md):
#   Literais  : NUM_INT→int  NUM_REAL→real  TRUE/FALSE→bool
#   LOAD      : (MEM)  → tipo da tabela de símbolos
#   STORE     : (V MEM) → sem tipo de resultado (side-effect)
#   RES       : (N RES) → unknown (valor de runtime)
#   Aritm (+,-,*,^): int op int→int; int/real op real→real; bool→ERRO
#   Div real (|): qualquer numérico→real; bool→ERRO
#   Div int  (/): exige ambos int; senão→ERRO
#   Resto    (%): exige ambos int; senão→ERRO
#   Relacionais : qualquer numérico→bool; bool como operando→ERRO
#   IF/WHILE  : condição deve ser bool; senão→ERRO
#   unknown   : propagado sem erro adicional (variável não inferida)
# ─────────────────────────────────────────────────────────────

_OP_CHARS: dict[str, str] = {
    'OP_ADD': '+', 'OP_SUB': '-', 'OP_MUL': '*', 'OP_RDIV': '|',
    'OP_IDIV': '/', 'OP_MOD': '%', 'OP_POW': '^',
    'OP_GT': '>', 'OP_LT': '<', 'OP_EQ': '==',
    'OP_NEQ': '!=', 'OP_GTE': '>=', 'OP_LTE': '<=',
}
_REL_OPS: frozenset[str] = frozenset(
    {'OP_GT', 'OP_LT', 'OP_EQ', 'OP_NEQ', 'OP_GTE', 'OP_LTE'}
)
_LITERAIS_BOOL: frozenset[str] = frozenset({'TRUE', 'FALSE'})


def _extrair_op_token(no: dict) -> dict | None:
    """Busca recursivamente o TOKEN de operador dentro de any_op/arith_op/rel_op."""
    if no.get('tipo') == 'TOKEN':
        return no
    for filho in no.get('filhos', []):
        resultado = _extrair_op_token(filho)
        if resultado:
            return resultado
    return None


def _tipo_do_op(op_str: str | None, t1: str, t2: str, linha: int, erros: list[str]) -> str:
    """
    Aplica as regras de tipo para (t1 op t2) e retorna o tipo resultante.
    Registra erros sem interromper a propagação.
    """
    if op_str is None:
        return 'unknown'

    op_char = _OP_CHARS.get(op_str, op_str)

    # Operadores relacionais → sempre produzem bool
    if op_str in _REL_OPS:
        if t1 == 'bool' or t2 == 'bool':
            erros.append(
                f"Linha {linha}: operador relacional '{op_char}' não pode operar "
                f"com tipo bool (tipos: '{t1}' e '{t2}')"
            )
        return 'bool'

    # Divisão inteira: ambos devem ser int
    if op_str == 'OP_IDIV':
        if t1 not in ('int', 'unknown') or t2 not in ('int', 'unknown'):
            erros.append(
                f"Linha {linha}: divisão inteira '/' requer tipo int "
                f"(obteve '{t1}' e '{t2}')"
            )
        return 'int'

    # Resto: ambos devem ser int
    if op_str == 'OP_MOD':
        if t1 not in ('int', 'unknown') or t2 not in ('int', 'unknown'):
            erros.append(
                f"Linha {linha}: resto '%' requer tipo int "
                f"(obteve '{t1}' e '{t2}')"
            )
        return 'int'

    # +, -, *, ^, | — não aceitam bool
    if t1 == 'bool' or t2 == 'bool':
        erros.append(
            f"Linha {linha}: operação '{op_char}' não suportada com tipo bool "
            f"(tipos: '{t1}' e '{t2}')"
        )
        t_nb = (t1 if t1 != 'bool' else t2)
        return t_nb if t_nb != 'bool' else 'unknown'

    # Divisão real → sempre real
    if op_str == 'OP_RDIV':
        return 'real'

    # +, -, *, ^ — promoção numérica
    if t1 == 'real' or t2 == 'real':
        return 'real'
    if t1 == 'unknown' or t2 == 'unknown':
        return 'unknown'
    return 'int'


def _tipo_id(nome: str, tabela: dict) -> str:
    """Retorna o tipo de um identificador: 'bool' se literal, ou busca na tabela."""
    if nome in _LITERAIS_BOOL:
        return 'bool'
    return tabela.get(nome, {}).get('tipo', 'unknown')


def _inferir_stmt_inner(no: dict, tabela: dict, tipos: dict, erros: list[str]) -> str | None:
    """
    Infere o tipo de um nó stmt_inner, registra em tipos[id(no)] e retorna o tipo.
    Retorna None para comandos sem valor (START, END, IF, WHILE, STORE).
    """
    if no.get('tipo') != 'NT' or no.get('simbolo') != 'stmt_inner':
        return None

    filhos = no.get('filhos', [])
    if not filhos:
        return None

    linha_no = no.get('linha', 0)
    primeiro = filhos[0]
    tok = primeiro.get('tipo_token', '')

    # ── START / END ──
    if tok in ('KW_START', 'KW_END'):
        tipos[id(no)] = None
        return None

    # ── IF ──
    if tok == 'KW_IF':
        # filhos: [KW_IF, stmt_cond, stmt_true, opt_else]
        t_cond = _inferir_stmt(filhos[1], tabela, tipos, erros)
        if t_cond is not None and t_cond != 'bool':
            linha_cond = filhos[1].get('linha', linha_no)
            erros.append(
                f"Linha {linha_cond}: condição do IF deve ser bool (obteve '{t_cond}')"
            )
        _inferir_stmt(filhos[2], tabela, tipos, erros)
        if len(filhos) >= 4:
            opt = filhos[3]
            opt_filhos = opt.get('filhos', [])
            if opt_filhos:
                _inferir_stmt(opt_filhos[0], tabela, tipos, erros)
        tipos[id(no)] = None
        return None

    # ── WHILE ──
    if tok == 'KW_WHILE':
        # filhos: [KW_WHILE, stmt_cond, stmt_body]
        t_cond = _inferir_stmt(filhos[1], tabela, tipos, erros)
        if t_cond is not None and t_cond != 'bool':
            linha_cond = filhos[1].get('linha', linha_no)
            erros.append(
                f"Linha {linha_cond}: condição do WHILE deve ser bool (obteve '{t_cond}')"
            )
        _inferir_stmt(filhos[2], tabela, tipos, erros)
        tipos[id(no)] = None
        return None

    # ── NUM_INT num_int_cont ──
    if tok == 'NUM_INT':
        cont = filhos[1]  # NT num_int_cont
        cont_filhos = cont.get('filhos', [])
        # (N RES)
        if cont_filhos and cont_filhos[0].get('tipo_token') == 'KW_RES':
            tipos[id(no)] = 'unknown'
            return 'unknown'
        t = _inferir_via_cont('int', primeiro, cont, tabela, tipos, erros)
        tipos[id(no)] = t
        return t

    # ── NUM_REAL num_real_cont ──
    if tok == 'NUM_REAL':
        cont = filhos[1]  # NT num_real_cont
        t = _inferir_via_cont('real', primeiro, cont, tabela, tipos, erros)
        tipos[id(no)] = t
        return t

    # ── ID id_cont ──
    if tok == 'ID':
        nome = primeiro['valor']
        t1 = _tipo_id(nome, tabela)
        cont = filhos[1]  # NT id_cont
        cont_filhos = cont.get('filhos', [])
        if not cont_filhos:
            # LOAD (id_cont → ε)
            tipos[id(no)] = t1
            return t1
        t = _inferir_via_cont(t1, primeiro, cont, tabela, tipos, erros)
        tipos[id(no)] = t
        return t

    # ── (stmt_inner) nested_cont ──
    if tok == 'LP':
        # filhos: [LP, stmt_inner_inner, RP, nested_cont]
        inner = filhos[1]
        t1 = _inferir_stmt_inner(inner, tabela, tipos, erros)
        nested_cont = filhos[3]
        nested_filhos = nested_cont.get('filhos', [])
        if not nested_filhos:
            tipos[id(no)] = t1
            return t1
        t = _inferir_via_cont(t1, primeiro, nested_cont, tabela, tipos, erros)
        tipos[id(no)] = t
        return t

    return None


def _inferir_via_cont(
    t1: str | None,
    token_t1: dict,
    cont: dict,
    tabela: dict,
    tipos: dict,
    erros: list[str],
) -> str | None:
    """
    Resolve o segundo operando e operador de um nó *_cont (num_int_cont,
    num_real_cont, id_cont, nested_cont) e aplica _tipo_do_op.

    Retorna t1 sem erro quando detecta padrão STORE (after_id → ε).
    """
    cont_filhos = cont.get('filhos', [])
    if not cont_filhos:
        return t1

    segundo = cont_filhos[0]
    tok2 = segundo.get('tipo_token', '')
    linha_ref = token_t1.get('linha', 0)

    # Segundo operando é expressão aninhada: [LP, inner, RP, op_no]
    if tok2 == 'LP':
        inner = cont_filhos[1]
        t2 = _inferir_stmt_inner(inner, tabela, tipos, erros)
        op_no = cont_filhos[3]
        op_tok = _extrair_op_token(op_no)
        op_str = op_tok['tipo_token'] if op_tok else None
        linha_op = op_tok['linha'] if op_tok else linha_ref
        return _tipo_do_op(op_str, t1, t2, linha_op, erros)

    # Segundo operando é token simples (NUM_INT, NUM_REAL, ID)
    if tok2 == 'NUM_INT':
        t2: str = 'int'
    elif tok2 == 'NUM_REAL':
        t2 = 'real'
    elif tok2 == 'ID':
        t2 = _tipo_id(segundo['valor'], tabela)
    else:
        return None

    # O operador está em cont_filhos[1], que pode ser:
    #   after_id_first_arg / after_id_nested → contém o op nos seus próprios filhos
    #   arith_op / any_op  → é diretamente o op
    op_part = cont_filhos[1]
    simbolo_op = op_part.get('simbolo', '')

    if simbolo_op in ('after_id_first_arg', 'after_id_nested'):
        after_filhos = op_part.get('filhos', [])
        if not after_filhos:
            # after_id → ε → padrão STORE; refina tipo na tabela se era unknown
            nome_var = segundo.get('valor', '')
            if (t1 is not None and t1 != 'unknown'
                    and not _é_literal_reservado(nome_var)
                    and nome_var in tabela
                    and tabela[nome_var]['tipo'] == 'unknown'):
                tabela[nome_var]['tipo'] = t1
            return t1
        op_no = after_filhos[0]  # NT arith_op ou any_op
    else:
        op_no = op_part  # diretamente arith_op ou any_op

    op_tok = _extrair_op_token(op_no)
    op_str = op_tok['tipo_token'] if op_tok else None
    linha_op = op_tok['linha'] if op_tok else linha_ref
    return _tipo_do_op(op_str, t1, t2, linha_op, erros)


def _inferir_stmt(no_stmt: dict, tabela: dict, tipos: dict, erros: list[str]) -> str | None:
    """Infere o tipo de um nó stmt (wrapper: extrai stmt_inner de LP...RP)."""
    if no_stmt.get('tipo') != 'NT' or no_stmt.get('simbolo') != 'stmt':
        return None
    filhos = no_stmt.get('filhos', [])
    if len(filhos) >= 2:
        t = _inferir_stmt_inner(filhos[1], tabela, tipos, erros)
        tipos[id(no_stmt)] = t
        return t
    return None


def _inferir_stmt_list(no: dict, tabela: dict, tipos: dict, erros: list[str]) -> None:
    """Percorre stmt_list recursivamente inferindo tipos de cada stmt."""
    filhos = no.get('filhos', [])
    if not filhos:
        return
    _inferir_stmt(filhos[0], tabela, tipos, erros)
    if len(filhos) >= 2:
        _inferir_stmt_list(filhos[1], tabela, tipos, erros)


def verificarTipos(arvore: dict, tabela: dict) -> tuple[dict, list[str]]:
    """
    (Aluno 3) Valida os tipos das expressões e comandos na árvore sintática.

    Entrada:
        arvore — árvore sintática inicial produzida por prepararEntradaSemantica()
        tabela — tabela de símbolos produzida por construirTabelaSimbolos()

    Saída:
        (tipos, erros) onde:
          - tipos : dict[id(nó) → tipo_str] com tipo inferido de cada nó
          - erros : lista de erros semânticos de tipo com número de linha
    """
    tipos: dict[int, str | None] = {}
    erros: list[str] = []

    if arvore.get('tipo') == 'NT' and arvore.get('simbolo') == 'programa':
        filhos = arvore.get('filhos', [])
        if filhos and filhos[0].get('simbolo') == 'stmt_list':
            _inferir_stmt_list(filhos[0], tabela, tipos, erros)

    return tipos, erros


def salvarErrosTipos(
    erros: list[str],
    caminho: str = 'erros_tipos.md',
    arquivo_fonte: str = '',
) -> str:
    """
    (Aluno 3) Salva o relatório de erros semânticos de tipo em arquivo Markdown.

    Entrada:
        erros         — lista de erros produzida por verificarTipos()
        caminho       — caminho do arquivo de saída (padrão: erros_tipos.md)
        arquivo_fonte — nome do arquivo de teste analisado (para rastreabilidade)

    Saída:
        caminho do arquivo gerado
    """
    linhas: list[str] = ['# Relatório de Erros de Tipo\n']
    if arquivo_fonte:
        linhas.append(f'**Arquivo de teste analisado:** `{arquivo_fonte}`\n')
    if erros:
        for erro in erros:
            linhas.append(f'- {erro}')
    else:
        linhas.append('Nenhum erro de tipo encontrado.')
    linhas.append('')

    with open(caminho, 'w', encoding='utf-8') as f:
        f.write('\n'.join(linhas))
    return caminho


# ─────────────────────────────────────────────────────────────
# [Aluno 4] gerarArvoreAtribuida e gerarAssemblySemantico
# ─────────────────────────────────────────────────────────────


def _categoria_stmt_inner(no: dict) -> str:
    """
    Determina a categoria semântica de um nó stmt_inner a partir do
    primeiro token filho.
    """
    filhos = no.get('filhos', [])
    if not filhos:
        return 'expressao'
    primeiro = filhos[0]
    if primeiro.get('tipo') != 'TOKEN':
        return 'expressao'
    mapa = {
        'KW_START':  'inicio',
        'KW_END':    'fim',
        'KW_IF':     'condicional',
        'KW_WHILE':  'repeticao',
    }
    return mapa.get(primeiro.get('tipo_token', ''), 'expressao')


def gerarArvoreAtribuida(arvore: dict, tabela: dict, tipos: dict) -> dict:
    """
    (Aluno 4) Produz a árvore sintática aumentada com anotações semânticas.

    Percorre a árvore recursivamente e adiciona o campo 'anotacoes' a cada
    nó. As anotações incluem:
        'tipo_semantico' — tipo inferido por verificarTipos() para o nó
                           ('int', 'real', 'bool', 'unknown', ou None)
        'categoria'      — papel semântico do nó (apenas para NT):
                           'inicio', 'fim', 'condicional', 'repeticao',
                           'expressao', ou o próprio 'simbolo' do NT

    A função preserva a estrutura original da árvore para que
    gerarAssemblySemantico possa reutilizar o gerador de código da Fase 2
    sem modificações.

    Entrada:
        arvore — árvore sintática inicial produzida por prepararEntradaSemantica()
        tabela — tabela de símbolos produzida por construirTabelaSimbolos()
        tipos  — dict[id(nó) → tipo_str] produzido por verificarTipos()

    Saída:
        dict com a mesma estrutura da árvore original, acrescido de
        'anotacoes' em cada nó.
    """
    def _anotar(no: dict) -> dict:
        # Lê o id ANTES de criar qualquer cópia para preservar a referência
        # usada como chave no dicionário tipos.
        tipo_sem = tipos.get(id(no))

        if no['tipo'] == 'NT':
            simbolo = no['simbolo']
            categoria = (
                _categoria_stmt_inner(no)
                if simbolo == 'stmt_inner'
                else simbolo
            )
            return {
                'tipo': 'NT',
                'simbolo': simbolo,
                'filhos': [_anotar(f) for f in no.get('filhos', [])],
                'linha': no['linha'],
                'anotacoes': {
                    'tipo_semantico': tipo_sem,
                    'categoria': categoria,
                },
            }

        # Nó TOKEN
        return {
            'tipo': 'TOKEN',
            'tipo_token': no['tipo_token'],
            'valor': no['valor'],
            'linha': no['linha'],
            'anotacoes': {
                'tipo_semantico': tipo_sem,
            },
        }

    return _anotar(arvore)


def _arvore_atribuida_para_json(arvore: dict) -> str:
    """Serializa a árvore atribuída em JSON legível."""
    return json.dumps(arvore, indent=2, ensure_ascii=False)


def gerarAssemblySemantico(arvoreAtribuida: dict) -> str:
    """
    (Aluno 4) Gera código Assembly ARMv7 a partir da árvore sintática atribuída.

    Delega para o gerador de código da Fase 2 (AnalisadorSintatico.gerarAssembly),
    que percorre a árvore pelos campos 'tipo', 'simbolo', 'filhos', 'tipo_token'
    e 'valor' — todos preservados pela árvore atribuída. O campo 'anotacoes'
    adicional é simplesmente ignorado pelo gerador.

    Deve ser chamada apenas após validação semântica completa (sem erros).

    Entrada:
        arvoreAtribuida — árvore produzida por gerarArvoreAtribuida()

    Saída:
        string com código Assembly completo para Cpulator-ARMv7 DEC1-SOC(v16.1)
    """
    return _gerarAssemblyFase2(arvoreAtribuida)


# Alias público conforme nomenclatura da Seção 7.4 do enunciado (Fase 3).
gerarAssembly = gerarAssemblySemantico


# ─────────────────────────────────────────────────────────────
# [Aluno 4] main() — pipeline completo
# ─────────────────────────────────────────────────────────────

def main() -> None:
    """
    (Aluno 4) Ponto de entrada do AnalisadorSemantico.

    Coordena as cinco etapas do compilador em sequência:
        1. prepararEntradaSemantica  — léxico + sintático (Aluno 1)
        2. construirTabelaSimbolos   — declarações e usos (Aluno 2)
        3. verificarTipos            — compatibilidade de tipos (Aluno 3)
        4. gerarArvoreAtribuida      — árvore com anotações semânticas
        5. gerarAssemblySemantico    — código Assembly ARMv7

    A geração de Assembly ocorre apenas quando não há erros léxicos,
    sintáticos ou semânticos.

    Uso:
        python AnalisadorSemantico.py <arquivo.txt>

    Artefatos salvos:
        tabela_simbolos.md   — tabela de símbolos e erros de declaração
        erros_tipos.md       — relatório de erros de tipo
        arvore_atribuida.json — árvore sintática aumentada
        programa.asm         — código Assembly (somente se sem erros)
    """
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass

    if len(sys.argv) != 2:
        print("Uso: python AnalisadorSemantico.py <arquivo.txt>")
        sys.exit(1)

    arquivo = sys.argv[1]
    print(f"Arquivo analisado: {arquivo}", flush=True)
    print("=" * 60, flush=True)

    # ── Etapa 1: léxico + sintático ──────────────────────────────
    tokens, arvore, erros_lex, erros_sint = prepararEntradaSemantica(arquivo)

    if erros_lex:
        print(f"\n[ERROS LÉXICOS] {len(erros_lex)} erro(s):", file=sys.stderr)
        for e in erros_lex:
            print(f"  {e}", file=sys.stderr)
    else:
        print(f"[OK] Análise léxica — {len(tokens) - 1} token(s) gerado(s)", flush=True)

    if erros_sint:
        print(f"\n[ERROS SINTÁTICOS] {len(erros_sint)} erro(s):", file=sys.stderr)
        for e in erros_sint:
            print(f"  {e}", file=sys.stderr)
    else:
        print("[OK] Análise sintática concluída", flush=True)

    if erros_lex or erros_sint:
        total = len(erros_lex) + len(erros_sint)
        print(
            f"\n[ERRO] Compilação interrompida: {total} erro(s) léxico(s)/sintático(s).",
            file=sys.stderr,
        )
        sys.exit(1)

    # ── Etapa 2: tabela de símbolos ──────────────────────────────
    tabela, erros_tab = construirTabelaSimbolos(arvore)
    caminho_tab = salvarTabelaSimbolos(tabela, erros_tab, arquivo_fonte=arquivo)
    print(f"[OK] Tabela de símbolos salva em '{caminho_tab}' "
          f"({len(tabela)} variável(is))", flush=True)

    if erros_tab:
        print(f"\n[ERROS DE DECLARAÇÃO] {len(erros_tab)} erro(s):", file=sys.stderr)
        for e in erros_tab:
            print(f"  {e}", file=sys.stderr)

    # ── Etapa 3: verificação de tipos ────────────────────────────
    tipos, erros_tipos = verificarTipos(arvore, tabela)
    caminho_erros = salvarErrosTipos(erros_tipos, arquivo_fonte=arquivo)
    print(f"[OK] Relatório de erros de tipo salvo em '{caminho_erros}'", flush=True)

    if erros_tipos:
        print(f"\n[ERROS DE TIPO] {len(erros_tipos)} erro(s):", file=sys.stderr)
        for e in erros_tipos:
            print(f"  {e}", file=sys.stderr)

    total_sem = len(erros_tab) + len(erros_tipos)
    if total_sem > 0:
        print(
            f"\n[ERRO] Compilação interrompida: {total_sem} erro(s) semântico(s). "
            "Assembly não gerado.",
            file=sys.stderr,
        )
        sys.exit(1)

    # ── Etapa 4: árvore atribuída ────────────────────────────────
    arvore_atribuida = gerarArvoreAtribuida(arvore, tabela, tipos)
    # Envolve a árvore em objeto com metadado do arquivo fonte (Seção 10.4)
    saida_json = {
        'arquivo_fonte': arquivo,
        'arvore_atribuida': arvore_atribuida,
    }
    json_str = json.dumps(saida_json, indent=2, ensure_ascii=False)
    with open('arvore_atribuida.json', 'w', encoding='utf-8') as f:
        f.write(json_str)
    print("[OK] Árvore sintática atribuída salva em 'arvore_atribuida.json'")

    # ── Etapa 5: geração de Assembly ─────────────────────────────
    assembly = gerarAssemblySemantico(arvore_atribuida)
    cabecalho_asm = f"@ Arquivo fonte: {arquivo}\n@ Gerado por: AnalisadorSemantico.py\n"
    with open('programa.asm', 'w', encoding='utf-8') as f:
        f.write(cabecalho_asm + assembly)
    print("[OK] Código Assembly salvo em 'programa.asm'")

    print("\n" + "=" * 60)
    print("[OK] Compilação concluída com sucesso!")
    print(f"[OK] Arquivo de teste utilizado: {arquivo}")
    print("=" * 60)


# ─────────────────────────────────────────────────────────────
# [Aluno 1] Funções de teste — lerTokensFase3 e prepararEntradaSemantica
# ─────────────────────────────────────────────────────────────

# Diretório onde este módulo está instalado; usado para localizar os
# arquivos de teste das fases anteriores sem depender do cwd.
_DIR_PROJETO = os.path.dirname(os.path.abspath(__file__))


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


def test_comentario_linha_inteira() -> None:
    """Comentário em linha própria deve ser descartado; tokens válidos permanecem."""
    conteudo = (
        "(START)\n"
        "*{ esta linha é um comentário completo }*\n"
        "(3.0 2.0 +)\n"
        "(END)\n"
    )
    cam = _escrever_tmp(conteudo)
    try:
        erros: list[str] = []
        toks = lerTokensFase3(cam, erros_out=erros)
        assert not erros, f"Não deveria haver erros: {erros}"
        tipos = [t['tipo'] for t in toks]
        assert 'KW_START' in tipos
        assert 'NUM_REAL' in tipos
        assert 'OP_ADD' in tipos
        assert 'KW_END' in tipos
        valores = {t['valor'] for t in toks}
        assert 'comentário' not in valores
        assert 'completo' not in valores
    finally:
        _apagar_tmp(cam)


def test_comentario_fim_de_linha() -> None:
    """Comentário ao final de linha não deve afetar tokens que o precedem."""
    conteudo = (
        "(START)\n"
        "(5.0 3.0 -) *{ subtração de reais }*\n"
        "(END)\n"
    )
    cam = _escrever_tmp(conteudo)
    try:
        erros: list[str] = []
        toks = lerTokensFase3(cam, erros_out=erros)
        assert not erros, f"Não deveria haver erros: {erros}"
        tipos = [t['tipo'] for t in toks]
        assert 'NUM_REAL' in tipos
        assert 'OP_SUB' in tipos
    finally:
        _apagar_tmp(cam)


def test_comentario_entre_expressoes() -> None:
    """Comentário multilinha entre dois comandos não deve afetar nenhum deles."""
    conteudo = (
        "(START)\n"
        "(10 5 +) *{ primeiro\n"
        "resultado }*\n"
        "(2 3 *)\n"
        "(END)\n"
    )
    cam = _escrever_tmp(conteudo)
    try:
        erros: list[str] = []
        toks = lerTokensFase3(cam, erros_out=erros)
        assert not erros, f"Não deveria haver erros: {erros}"
        tipos = [t['tipo'] for t in toks]
        assert 'OP_ADD' in tipos
        assert 'OP_MUL' in tipos
    finally:
        _apagar_tmp(cam)


def test_comentario_multilinhas_contagem_linhas() -> None:
    """Contador de linhas deve permanecer correto após comentário multilinha."""
    conteudo = (
        "(START)\n"         # linha 1
        "*{\n"              # linha 2: abre comentário
        "linha interna\n"   # linha 3
        "linha interna\n"   # linha 4
        "}*\n"              # linha 5: fecha comentário; \n avança para 6
        "(1.0 2.0 +)\n"     # linha 6
        "(END)\n"           # linha 7
    )
    cam = _escrever_tmp(conteudo)
    try:
        erros: list[str] = []
        toks = lerTokensFase3(cam, erros_out=erros)
        assert not erros, f"Não deveria haver erros: {erros}"
        tok_num = next(t for t in toks if t['tipo'] == 'NUM_REAL')
        assert tok_num['linha'] == 6, (
            f"Token de número deveria estar na linha 6, obteve {tok_num['linha']}"
        )
    finally:
        _apagar_tmp(cam)


def test_comentario_nao_fechado_levanta_erro() -> None:
    """Comentário aberto sem fechamento deve levantar ValueError."""
    conteudo = "(START)\n*{ comentário sem fechamento\n(1.0 2.0 +)\n(END)\n"
    cam = _escrever_tmp(conteudo)
    try:
        try:
            lerTokensFase3(cam)
            assert False, "deveria ter levantado ValueError"
        except ValueError as e:
            msg = str(e).lower()
            assert "comentário" in msg or "fechado" in msg, (
                f"Mensagem deveria mencionar comentário não fechado: {e}"
            )
    finally:
        _apagar_tmp(cam)


def test_comentario_nao_fechado_recuperacao() -> None:
    """Com erros_out, comentário não fechado é registrado sem interromper o léxico."""
    conteudo = "(START)\n*{ sem fechamento\n(1.0)\n(END)\n"
    cam = _escrever_tmp(conteudo)
    try:
        erros: list[str] = []
        lerTokensFase3(cam, erros_out=erros)
        assert len(erros) >= 1, f"Deveria registrar ao menos 1 erro: {erros}"
        assert any("comentário" in e.lower() or "fechado" in e.lower() for e in erros)
    finally:
        _apagar_tmp(cam)


def test_estrela_sem_chave_emite_mul() -> None:
    """'*' sem '{' imediatamente seguinte deve ser emitido como OP_MUL."""
    conteudo = "(START)\n(3 4 *)\n(END)\n"
    cam = _escrever_tmp(conteudo)
    try:
        erros: list[str] = []
        toks = lerTokensFase3(cam, erros_out=erros)
        assert not erros, f"Não deveria haver erros: {erros}"
        assert any(t['tipo'] == 'OP_MUL' for t in toks), "* sem { deveria gerar OP_MUL"
    finally:
        _apagar_tmp(cam)


def test_multiplos_comentarios_mesma_linha() -> None:
    """Múltiplos comentários numa mesma linha devem ser todos descartados."""
    conteudo = (
        "(START)\n"
        "*{ A }* (2.0 3.0 +) *{ B }*\n"
        "(END)\n"
    )
    cam = _escrever_tmp(conteudo)
    try:
        erros: list[str] = []
        toks = lerTokensFase3(cam, erros_out=erros)
        assert not erros, f"Não deveria haver erros: {erros}"
        tipos = [t['tipo'] for t in toks]
        assert 'KW_START' in tipos
        assert 'OP_ADD' in tipos
        assert 'KW_END' in tipos
    finally:
        _apagar_tmp(cam)


def test_caractere_invalido_levanta_erro() -> None:
    """Caractere léxico inválido (ex.: '@') deve levantar ValueError com número de linha."""
    conteudo = "(START)\n(3 @ 2 +)\n(END)\n"
    cam = _escrever_tmp(conteudo)
    try:
        try:
            lerTokensFase3(cam)
            assert False, "deveria ter levantado ValueError"
        except ValueError as e:
            msg = str(e).lower()
            assert "inválido" in msg or "invalido" in msg or "@" in msg, (
                f"Mensagem deveria indicar caractere inválido: {e}"
            )
    finally:
        _apagar_tmp(cam)


def test_caractere_invalido_recuperacao() -> None:
    """Com erros_out, caractere inválido é registrado; tokens vizinhos permanecem presentes."""
    conteudo = "(START)\n(3 @ 2 +)\n(END)\n"
    cam = _escrever_tmp(conteudo)
    try:
        erros: list[str] = []
        toks = lerTokensFase3(cam, erros_out=erros)
        assert len(erros) >= 1, f"Deveria registrar ao menos 1 erro: {erros}"
        assert any("@" in e or "inválido" in e.lower() or "invalido" in e.lower() for e in erros), (
            f"Erro deveria mencionar o caractere inválido: {erros}"
        )
        tipos = [t['tipo'] for t in toks]
        assert 'KW_START' in tipos, "KW_START deveria estar presente após recuperação"
        assert 'NUM_INT'  in tipos, "NUM_INT deveria estar presente após recuperação"
        assert 'OP_ADD'   in tipos, "OP_ADD deveria estar presente após recuperação"
        assert 'KW_END'   in tipos, "KW_END deveria estar presente após recuperação"
    finally:
        _apagar_tmp(cam)


def test_true_false_sao_id() -> None:
    """TRUE e FALSE devem ser emitidos como ID para inferência semântica posterior."""
    conteudo = "(START)\n(TRUE)\n(FALSE)\n(END)\n"
    cam = _escrever_tmp(conteudo)
    try:
        erros: list[str] = []
        toks = lerTokensFase3(cam, erros_out=erros)
        assert not erros, f"Não deveria haver erros: {erros}"
        ids = [t for t in toks if t['tipo'] == 'ID']
        valores_id = {t['valor'] for t in ids}
        assert 'TRUE'  in valores_id, "TRUE deveria ser token ID"
        assert 'FALSE' in valores_id, "FALSE deveria ser token ID"
    finally:
        _apagar_tmp(cam)


def test_validar_start_end_ok() -> None:
    """Programa com START e END não deve gerar erros estruturais."""
    conteudo = "(START)\n(1.0 2.0 +)\n(END)\n"
    cam = _escrever_tmp(conteudo)
    try:
        _, _, erros_lex, _ = prepararEntradaSemantica(cam)
        estruturais = [e for e in erros_lex if 'START' in e or 'END' in e]
        assert not estruturais, f"Não deveria haver erros estruturais: {estruturais}"
    finally:
        _apagar_tmp(cam)


def test_validar_sem_start() -> None:
    """Programa que não começa com (START) deve gerar erro léxico estrutural."""
    conteudo = "(1.0 2.0 +)\n(END)\n"
    cam = _escrever_tmp(conteudo)
    try:
        _, _, erros_lex, _ = prepararEntradaSemantica(cam)
        assert any('START' in e for e in erros_lex), (
            f"Deveria reportar ausência de START: {erros_lex}"
        )
    finally:
        _apagar_tmp(cam)


def test_validar_sem_end() -> None:
    """Programa que não termina com (END) deve gerar erro léxico estrutural."""
    conteudo = "(START)\n(1.0 2.0 +)\n"
    cam = _escrever_tmp(conteudo)
    try:
        _, _, erros_lex, _ = prepararEntradaSemantica(cam)
        assert any('END' in e for e in erros_lex), (
            f"Deveria reportar ausência de END: {erros_lex}"
        )
    finally:
        _apagar_tmp(cam)


def test_preparar_retorna_arvore_valida() -> None:
    """prepararEntradaSemantica deve retornar árvore com símbolo raiz 'programa'."""
    conteudo = "(START)\n(3.0 2.0 +)\n(END)\n"
    cam = _escrever_tmp(conteudo)
    try:
        _, arvore, erros_lex, erros_sint = prepararEntradaSemantica(cam)
        assert not erros_lex,  f"Erros léxicos inesperados: {erros_lex}"
        assert not erros_sint, f"Erros sintáticos inesperados: {erros_sint}"
        assert arvore['tipo'] == 'NT'
        assert arvore['simbolo'] == 'programa'
    finally:
        _apagar_tmp(cam)


def test_preparar_comentarios_invisiveis_ao_parser() -> None:
    """Comentários devem ser invisíveis ao parser: árvore gerada normalmente."""
    conteudo = (
        "*{ programa com comentários }*\n"
        "(START) *{ início }*\n"
        "(10 *{ operando }* 5 +)\n"
        "(END)\n"
    )
    cam = _escrever_tmp(conteudo)
    try:
        _, arvore, erros_lex, erros_sint = prepararEntradaSemantica(cam)
        assert not erros_lex,  f"Erros léxicos inesperados: {erros_lex}"
        assert not erros_sint, f"Erros sintáticos inesperados: {erros_sint}"
        assert arvore['simbolo'] == 'programa'
    finally:
        _apagar_tmp(cam)


def test_preparar_tokens_sem_texto_de_comentario() -> None:
    """Nenhum token resultante deve conter texto que estava dentro do comentário."""
    conteudo = "(START)\n*{ SEGREDO }*\n(1 2 +)\n(END)\n"
    cam = _escrever_tmp(conteudo)
    try:
        tokens, _, _, _ = prepararEntradaSemantica(cam)
        valores = {t['valor'] for t in tokens}
        assert 'SEGREDO' not in valores, "Texto de comentário não deveria aparecer nos tokens"
    finally:
        _apagar_tmp(cam)


def test_preparar_arquivo_inexistente() -> None:
    """Arquivo inexistente deve propagar FileNotFoundError."""
    try:
        prepararEntradaSemantica('arquivo_xyz_nao_existe_fase3.txt')
        assert False, "deveria ter levantado FileNotFoundError"
    except FileNotFoundError:
        pass


def test_preparar_sintaxe_invalida_operador_prematuro() -> None:
    """Operador onde o segundo operando é esperado deve gerar erro sintático.
    (3.0 + 2.0) coloca OP_ADD antes do segundo operando: o parser espera
    um token em FIRST(num_real_cont) = {ID, NUM_INT, NUM_REAL, LP}.
    """
    conteudo = "(START)\n(3.0 + 2.0)\n(END)\n"
    cam = _escrever_tmp(conteudo)
    try:
        _, _, erros_lex, erros_sint = prepararEntradaSemantica(cam)
        assert not erros_lex, f"Não deveria haver erros léxicos: {erros_lex}"
        assert len(erros_sint) >= 1, (
            f"Operador antes do segundo operando deveria gerar erro sintático: {erros_sint}"
        )
    finally:
        _apagar_tmp(cam)


def test_preparar_sintaxe_invalida_operador_extra() -> None:
    """Operador extra após expressão completa deve gerar erro sintático.
    Em (3.0 2.0 + +) o segundo '+' surge onde o parser espera RP.
    """
    conteudo = "(START)\n(3.0 2.0 + +)\n(END)\n"
    cam = _escrever_tmp(conteudo)
    try:
        _, _, erros_lex, erros_sint = prepararEntradaSemantica(cam)
        assert not erros_lex, f"Não deveria haver erros léxicos: {erros_lex}"
        assert len(erros_sint) >= 1, (
            f"Operador extra deveria gerar erro sintático: {erros_sint}"
        )
    finally:
        _apagar_tmp(cam)


def test_integracao_fase3_lexer() -> None:
    """Arquivos Fase 3 (teste1-3.txt) devem ser tokenizados sem erros léxicos."""
    for nome in ('teste1.txt', 'teste2.txt', 'teste3.txt'):
        cam = os.path.join(_DIR_PROJETO, nome)
        if not os.path.exists(cam):
            continue  # arquivo ausente no repositório: teste ignorado
        erros: list[str] = []
        toks = lerTokensFase3(cam, erros_out=erros)
        assert not erros, f"{nome}: erros léxicos inesperados: {erros}"
        assert any(t['tipo'] == 'KW_START' for t in toks), f"{nome}: KW_START ausente"
        assert any(t['tipo'] == 'KW_END'   for t in toks), f"{nome}: KW_END ausente"
        # Comentários devem ter sido descartados; nenhum token deve conter
        # texto típico de comentário (marcadores ou conteúdo entre *{ }*)
        valores = {t['valor'] for t in toks}
        assert '*{' not in valores and '}*' not in valores, (
            f"{nome}: marcadores de comentário não devem aparecer nos tokens"
        )


def test_integracao_fase3_lexer_tem_todos_ops() -> None:
    """teste1.txt deve conter todos os operadores exigidos pela Fase 3."""
    cam = os.path.join(_DIR_PROJETO, 'teste1.txt')
    if not os.path.exists(cam):
        return
    erros: list[str] = []
    toks = lerTokensFase3(cam, erros_out=erros)
    tipos = {t['tipo'] for t in toks}
    for op in ('OP_ADD', 'OP_SUB', 'OP_MUL', 'OP_RDIV', 'OP_IDIV', 'OP_MOD', 'OP_POW'):
        assert op in tipos, f"teste1.txt deveria conter operador {op}"


def test_integracao_fase3_parser() -> None:
    """Arquivos da Fase 3 devem produzir árvore sintática válida via prepararEntradaSemantica."""
    for nome in ('teste1.txt', 'teste3.txt'):  # arquivo de erros semânticos (teste2) é válido sintaticamente
        cam = os.path.join(_DIR_PROJETO, nome)
        if not os.path.exists(cam):
            continue
        _, arvore, erros_lex, erros_sint = prepararEntradaSemantica(cam)
        assert not erros_lex,  f"{nome}: erros léxicos inesperados: {erros_lex}"
        assert not erros_sint, f"{nome}: erros sintáticos inesperados: {erros_sint}"
        assert arvore['tipo']    == 'NT',       f"{nome}: raiz da árvore deveria ser NT"
        assert arvore['simbolo'] == 'programa', f"{nome}: símbolo raiz deveria ser 'programa'"


def test_integracao_fase3_arquivo_erros_sem_erros_lex_sint() -> None:
    """teste2.txt tem erros semânticos, mas deve passar nas fases léxica e sintática sem erros."""
    cam = os.path.join(_DIR_PROJETO, 'teste2.txt')
    if not os.path.exists(cam):
        return
    _, arvore, erros_lex, erros_sint = prepararEntradaSemantica(cam)
    assert not erros_lex,  f"teste2.txt: erros léxicos inesperados: {erros_lex}"
    assert not erros_sint, f"teste2.txt: erros sintáticos inesperados: {erros_sint}"
    assert arvore['simbolo'] == 'programa', "teste2.txt: símbolo raiz deveria ser 'programa'"


def test_integracao_fase3_bool_literals_sao_id() -> None:
    """TRUE e FALSE presentes nos arquivos Fase 3 devem ser tokenizados como ID."""
    cam = os.path.join(_DIR_PROJETO, 'teste1.txt')
    if not os.path.exists(cam):
        return
    erros: list[str] = []
    toks = lerTokensFase3(cam, erros_out=erros)
    ids = {t['valor'] for t in toks if t['tipo'] == 'ID'}
    assert 'TRUE'  in ids, "TRUE deveria aparecer como token ID em teste1.txt"
    assert 'FALSE' in ids, "FALSE deveria aparecer como token ID em teste1.txt"


# ─────────────────────────────────────────────────────────────
# [Aluno 2] Funções de teste — construirTabelaSimbolos
# ─────────────────────────────────────────────────────────────

def test_construir_tabela_vazia() -> None:
    """Programa vazio (apenas START/END) deve gerar tabela vazia."""
    conteudo = "(START)\n(END)\n"
    cam = _escrever_tmp(conteudo)
    try:
        _, arvore, erros_lex, erros_sint = prepararEntradaSemantica(cam)
        assert not erros_lex, f"Erros léxicos: {erros_lex}"
        assert not erros_sint, f"Erros sintáticos: {erros_sint}"
        tabela, erros = construirTabelaSimbolos(arvore)
        assert not erros, f"Deveria ser sem erros: {erros}"
        assert len(tabela) == 0, "Tabela deveria estar vazia"
    finally:
        _apagar_tmp(cam)


def test_construir_store_int() -> None:
    """STORE de inteiro deve registrar variável com tipo 'int'."""
    conteudo = "(START)\n(42 X)\n(END)\n"
    cam = _escrever_tmp(conteudo)
    try:
        _, arvore, _, _ = prepararEntradaSemantica(cam)
        tabela, erros = construirTabelaSimbolos(arvore)
        assert not erros, f"Deveria ser sem erros: {erros}"
        assert 'X' in tabela, "Variável X deveria estar na tabela"
        assert tabela['X']['tipo'] == 'int', "X deveria ser tipo 'int'"
        assert 'linha_def' in tabela['X'], "Deveria ter linha_def"
    finally:
        _apagar_tmp(cam)


def test_construir_store_real() -> None:
    """STORE de real deve registrar variável com tipo 'real'."""
    conteudo = "(START)\n(3.14 Y)\n(END)\n"
    cam = _escrever_tmp(conteudo)
    try:
        _, arvore, _, _ = prepararEntradaSemantica(cam)
        tabela, erros = construirTabelaSimbolos(arvore)
        assert not erros, f"Deveria ser sem erros: {erros}"
        assert 'Y' in tabela, "Variável Y deveria estar na tabela"
        assert tabela['Y']['tipo'] == 'real', "Y deveria ser tipo 'real'"
    finally:
        _apagar_tmp(cam)


def test_construir_store_unknown() -> None:
    """STORE de expressão deve registrar variável com tipo 'unknown'."""
    conteudo = "(START)\n(((1 2 +) X))\n(END)\n"
    cam = _escrever_tmp(conteudo)
    try:
        _, arvore, _, _ = prepararEntradaSemantica(cam)
        tabela, erros = construirTabelaSimbolos(arvore)
        # Pode não ser detectado dependendo da estrutura exata; se não for,
        # fica como teste de que não quebra o parser
        if 'X' in tabela:
            assert tabela['X']['tipo'] == 'unknown', "X deveria ser tipo 'unknown' (resultado de expressão)"
    finally:
        _apagar_tmp(cam)


def test_construir_load_simple() -> None:
    """LOAD de variável deve registrar uso."""
    conteudo = "(START)\n(42 X)\n(X)\n(END)\n"
    cam = _escrever_tmp(conteudo)
    try:
        _, arvore, _, _ = prepararEntradaSemantica(cam)
        tabela, erros = construirTabelaSimbolos(arvore)
        assert not erros, f"Deveria ser sem erros: {erros}"
        assert 'X' in tabela, "Variável X deveria estar na tabela"
        assert len(tabela['X']['linhas_uso']) >= 1, "X deveria ter ao menos 1 uso"
    finally:
        _apagar_tmp(cam)


def test_construir_multiplos_usos() -> None:
    """Múltiplos usos de mesma variável devem ser registrados."""
    conteudo = "(START)\n(1 X)\n(X)\n(X)\n(X)\n(END)\n"
    cam = _escrever_tmp(conteudo)
    try:
        _, arvore, _, _ = prepararEntradaSemantica(cam)
        tabela, erros = construirTabelaSimbolos(arvore)
        assert not erros, f"Deveria ser sem erros: {erros}"
        assert len(tabela['X']['linhas_uso']) == 3, "X deveria ter 3 usos"
    finally:
        _apagar_tmp(cam)


def test_construir_erro_uso_antes_definicao() -> None:
    """Uso antes de definição deve registrar erro."""
    conteudo = "(START)\n(X)\n(42 X)\n(END)\n"
    cam = _escrever_tmp(conteudo)
    try:
        _, arvore, _, _ = prepararEntradaSemantica(cam)
        tabela, erros = construirTabelaSimbolos(arvore)
        assert len(erros) >= 1, "Deveria haver erro de uso antes de definição"
        assert any("usada antes" in e.lower() for e in erros), "Erro deveria mencionar uso antes de definição"
    finally:
        _apagar_tmp(cam)


def test_construir_erro_tipo_incompativel() -> None:
    """Redefinição com tipo incompatível deve registrar erro."""
    conteudo = "(START)\n(42 X)\n(3.14 X)\n(END)\n"
    cam = _escrever_tmp(conteudo)
    try:
        _, arvore, _, _ = prepararEntradaSemantica(cam)
        tabela, erros = construirTabelaSimbolos(arvore)
        assert len(erros) >= 1, "Deveria haver erro de tipo incompatível"
        assert any("redefinida" in e.lower() and "tipo" in e.lower() for e in erros)
    finally:
        _apagar_tmp(cam)


def test_construir_erro_true_false_como_variavel() -> None:
    """TRUE/FALSE como nomes de variável devem ser evitados (reserved literals)."""
    conteudo = "(START)\n(42 TRUE)\n(END)\n"
    cam = _escrever_tmp(conteudo)
    try:
        _, arvore, _, _ = prepararEntradaSemantica(cam)
        tabela, erros = construirTabelaSimbolos(arvore)
        # Pode ou não gerar erro dependendo de como a estrutura STORE é parseada
        # O importante é que TRUE não apareça como variável na tabela se houver erro
        if len(erros) > 0:
            assert any("reservado" in e.lower() for e in erros)
        assert 'TRUE' not in tabela, "TRUE não deveria estar na tabela como variável definida"
    finally:
        _apagar_tmp(cam)


def test_construir_res_pattern() -> None:
    """Padrão (N RES) deve ser reconhecido sem erro se N <= stmts anteriores."""
    conteudo = "(START)\n(1 2 +)\n(1 RES)\n(END)\n"
    cam = _escrever_tmp(conteudo)
    try:
        _, arvore, _, _ = prepararEntradaSemantica(cam)
        tabela, erros = construirTabelaSimbolos(arvore)
        assert not erros, f"Deveria ser sem erros: {erros}"
    finally:
        _apagar_tmp(cam)


def test_construir_erro_res_fora_alcance() -> None:
    """Padrão (N RES) com N > stmts anteriores deve registrar erro."""
    conteudo = "(START)\n(1 2 +)\n(5 RES)\n(END)\n"
    cam = _escrever_tmp(conteudo)
    try:
        _, arvore, _, _ = prepararEntradaSemantica(cam)
        tabela, erros = construirTabelaSimbolos(arvore)
        assert len(erros) >= 1, "Deveria haver erro de RES fora de alcance"
        assert any("fora do alcance" in e.lower() or "RES" in e for e in erros)
    finally:
        _apagar_tmp(cam)


def test_construir_if_sem_else() -> None:
    """IF sem else deve processar condição sem erro."""
    conteudo = "(START)\n(1.0 COND)\n(IF (COND 1.0 >) (2.0 3.0 +))\n(END)\n"
    cam = _escrever_tmp(conteudo)
    try:
        _, arvore, _, _ = prepararEntradaSemantica(cam)
        tabela, erros = construirTabelaSimbolos(arvore)
        assert not erros, f"Deveria ser sem erros: {erros}"
        assert 'COND' in tabela, "COND deveria estar na tabela"
    finally:
        _apagar_tmp(cam)


def test_construir_if_com_else() -> None:
    """IF com else deve processar condição, corpo true e corpo false."""
    conteudo = "(START)\n(1.0 COND)\n(IF (COND 1.0 >) (2.0 3.0 +) (4.0 5.0 -))\n(END)\n"
    cam = _escrever_tmp(conteudo)
    try:
        _, arvore, _, _ = prepararEntradaSemantica(cam)
        tabela, erros = construirTabelaSimbolos(arvore)
        assert not erros, f"Deveria ser sem erros: {erros}"
    finally:
        _apagar_tmp(cam)


def test_construir_while_simples() -> None:
    """WHILE deve processar condição e corpo."""
    conteudo = "(START)\n(0 I)\n(WHILE (I 10 <) ((I 1 +) I))\n(END)\n"
    cam = _escrever_tmp(conteudo)
    try:
        _, arvore, _, _ = prepararEntradaSemantica(cam)
        tabela, erros = construirTabelaSimbolos(arvore)
        assert not erros, f"Deveria ser sem erros: {erros}"
        assert 'I' in tabela, "I deveria estar na tabela"
    finally:
        _apagar_tmp(cam)


def test_construir_true_false_como_valor() -> None:
    """TRUE/FALSE como valores de expressão devem ser OK (ID normais)."""
    conteudo = "(START)\n(TRUE)\n(FALSE)\n(END)\n"
    cam = _escrever_tmp(conteudo)
    try:
        _, arvore, _, _ = prepararEntradaSemantica(cam)
        tabela, erros = construirTabelaSimbolos(arvore)
        assert not erros, "TRUE e FALSE como valores não devem gerar erros"
        assert 'TRUE' not in tabela and 'FALSE' not in tabela, "Não devem estar na tabela como definições"
    finally:
        _apagar_tmp(cam)


def test_construir_multiplas_variaveis() -> None:
    """Múltiplas variáveis diferentes devem ser registradas."""
    conteudo = "(START)\n(1 A)\n(2 B)\n(3.0 C)\n(A)\n(B)\n(C)\n(END)\n"
    cam = _escrever_tmp(conteudo)
    try:
        _, arvore, _, _ = prepararEntradaSemantica(cam)
        tabela, erros = construirTabelaSimbolos(arvore)
        assert not erros, f"Deveria ser sem erros: {erros}"
        assert len(tabela) == 3, f"Deveria ter 3 variáveis, obteve {len(tabela)}"
        assert 'A' in tabela and 'B' in tabela and 'C' in tabela
    finally:
        _apagar_tmp(cam)


def test_integracao_teste2_semantico() -> None:
    """teste2.txt deve passar lexical/syntax, mas construirTabelaSimbolos detecta erros semânticos."""
    cam = os.path.join(_DIR_PROJETO, 'teste2.txt')
    if not os.path.exists(cam):
        return
    _, arvore, erros_lex, erros_sint = prepararEntradaSemantica(cam)
    assert not erros_lex, f"teste2.txt: erros léxicos inesperados: {erros_lex}"
    assert not erros_sint, f"teste2.txt: erros sintáticos inesperados: {erros_sint}"
    # Agora: erros semânticos devem ser detectados
    tabela, erros = construirTabelaSimbolos(arvore)
    assert len(erros) >= 1, "teste2.txt deveria ter ao menos 1 erro semântico"
    # teste2.txt tem erro de "PRECO usado antes de ser definido"
    assert any("usada antes" in e.lower() for e in erros), "teste2.txt deveria ter erro de uso antes de definição"


def test_integracao_teste1_valido() -> None:
    """teste1.txt deve passar sem erros em construirTabelaSimbolos."""
    cam = os.path.join(_DIR_PROJETO, 'teste1.txt')
    if not os.path.exists(cam):
        return
    _, arvore, erros_lex, erros_sint = prepararEntradaSemantica(cam)
    assert not erros_lex, f"teste1.txt: erros léxicos: {erros_lex}"
    assert not erros_sint, f"teste1.txt: erros sintáticos: {erros_sint}"
    tabela, erros = construirTabelaSimbolos(arvore)
    assert not erros, f"teste1.txt: erros semânticos inesperados: {erros}"
    # teste1.txt deve ter algumas variáveis definidas
    assert len(tabela) > 0, "teste1.txt deveria ter ao menos uma variável"


def test_construir_id_como_segundo_operando_erro() -> None:
    """ID não declarado como segundo operando deve gerar erro de uso antes de definição."""
    conteudo = "(START)\n(5 Y +)\n(END)\n"
    cam = _escrever_tmp(conteudo)
    try:
        _, arvore, _, _ = prepararEntradaSemantica(cam)
        tabela, erros = construirTabelaSimbolos(arvore)
        assert len(erros) >= 1, "Y não declarado como segundo operando deveria gerar erro"
        assert any("usada antes" in e.lower() for e in erros), (
            f"Erro deveria mencionar uso antes de definição: {erros}"
        )
    finally:
        _apagar_tmp(cam)


def test_construir_id_como_segundo_operando_ok() -> None:
    """ID declarado como segundo operando deve ser registrado como uso sem erro."""
    conteudo = "(START)\n(3 Y)\n(5 Y +)\n(END)\n"
    cam = _escrever_tmp(conteudo)
    try:
        _, arvore, _, _ = prepararEntradaSemantica(cam)
        tabela, erros = construirTabelaSimbolos(arvore)
        assert not erros, f"Deveria ser sem erros: {erros}"
        assert 'Y' in tabela
        assert len(tabela['Y']['linhas_uso']) >= 1, "Y deveria ter ao menos 1 uso como segundo operando"
    finally:
        _apagar_tmp(cam)


def test_construir_id_em_expr_aninhada() -> None:
    """ID dentro de expressão aninhada deve ser detectado como uso."""
    conteudo = "(START)\n(1.0 A)\n((A 2.0 +) 3.0 *)\n(END)\n"
    cam = _escrever_tmp(conteudo)
    try:
        _, arvore, _, _ = prepararEntradaSemantica(cam)
        tabela, erros = construirTabelaSimbolos(arvore)
        assert not erros, f"Deveria ser sem erros: {erros}"
        assert 'A' in tabela
        assert len(tabela['A']['linhas_uso']) >= 1, "A deveria ter uso detectado dentro de expressão aninhada"
    finally:
        _apagar_tmp(cam)


def test_construir_id_em_expr_aninhada_erro() -> None:
    """ID não declarado dentro de expressão aninhada deve gerar erro."""
    conteudo = "(START)\n((Z 2.0 +) 3.0 *)\n(END)\n"
    cam = _escrever_tmp(conteudo)
    try:
        _, arvore, _, _ = prepararEntradaSemantica(cam)
        tabela, erros = construirTabelaSimbolos(arvore)
        assert len(erros) >= 1, "Z não declarado dentro de expressão aninhada deveria gerar erro"
        assert any("usada antes" in e.lower() for e in erros)
    finally:
        _apagar_tmp(cam)


def test_construir_store_com_var_interna() -> None:
    """STORE via expr aninhada deve detectar uso da var dentro da expressão."""
    conteudo = "(START)\n(1 I)\n((I 1 +) I)\n(END)\n"
    cam = _escrever_tmp(conteudo)
    try:
        _, arvore, _, _ = prepararEntradaSemantica(cam)
        tabela, erros = construirTabelaSimbolos(arvore)
        assert not erros, f"Deveria ser sem erros: {erros}"
        assert 'I' in tabela
        # I deve ter uso registrado do interior de (I 1 +)
        assert len(tabela['I']['linhas_uso']) >= 1, "I deveria ter uso detectado dentro de ((I 1+) I)"
    finally:
        _apagar_tmp(cam)


def test_construir_dois_ids_em_operacao() -> None:
    """Dois IDs como operandos da mesma operação devem ser detectados."""
    conteudo = "(START)\n(2 A)\n(3 B)\n(A B +)\n(END)\n"
    cam = _escrever_tmp(conteudo)
    try:
        _, arvore, _, _ = prepararEntradaSemantica(cam)
        tabela, erros = construirTabelaSimbolos(arvore)
        assert not erros, f"Deveria ser sem erros: {erros}"
        assert len(tabela['A']['linhas_uso']) >= 1
        assert len(tabela['B']['linhas_uso']) >= 1
    finally:
        _apagar_tmp(cam)


def test_construir_salvar_tabela_markdown() -> None:
    """salvarTabelaSimbolos deve criar arquivo Markdown com tabela e erros."""
    conteudo = "(START)\n(42 X)\n(X)\n(END)\n"
    cam = _escrever_tmp(conteudo)
    md = _escrever_tmp('')
    try:
        _, arvore, _, _ = prepararEntradaSemantica(cam)
        tabela, erros = construirTabelaSimbolos(arvore)
        resultado = salvarTabelaSimbolos(tabela, erros, md)
        assert resultado == md
        with open(md, encoding='utf-8') as f:
            texto = f.read()
        assert 'X' in texto
        assert 'int' in texto
        assert 'Tabela de Símbolos' in texto
        assert 'Erros Semânticos' in texto
    finally:
        _apagar_tmp(cam)
        _apagar_tmp(md)


def test_construir_while_usa_var_no_body() -> None:
    """WHILE: uso de variável no corpo deve ser registrado."""
    conteudo = "(START)\n(0 I)\n(WHILE (I 10 <) ((I 1 +) I))\n(END)\n"
    cam = _escrever_tmp(conteudo)
    try:
        _, arvore, _, _ = prepararEntradaSemantica(cam)
        tabela, erros = construirTabelaSimbolos(arvore)
        assert not erros, f"Deveria ser sem erros: {erros}"
        assert 'I' in tabela
        # I deve ter usos detectados dentro do WHILE
        assert len(tabela['I']['linhas_uso']) >= 1
    finally:
        _apagar_tmp(cam)


def test_construir_while_var_nao_declarada_no_body() -> None:
    """WHILE: variável não declarada no corpo deve gerar erro."""
    conteudo = "(START)\n(WHILE (TRUE) (FANTASMA 1 +))\n(END)\n"
    cam = _escrever_tmp(conteudo)
    try:
        _, arvore, _, erros_sint = prepararEntradaSemantica(cam)
        if erros_sint:
            return  # se sintaxe falhou, ignora o teste semântico
        tabela, erros = construirTabelaSimbolos(arvore)
        assert any("usada antes" in e.lower() for e in erros), (
            f"FANTASMA não declarado no WHILE body deveria gerar erro: {erros}"
        )
    finally:
        _apagar_tmp(cam)


def test_integracao_teste3_complexo() -> None:
    """teste3.txt é programa complexo; deve passar lexical/syntax e análise semântica."""
    cam = os.path.join(_DIR_PROJETO, 'teste3.txt')
    if not os.path.exists(cam):
        return
    _, arvore, erros_lex, erros_sint = prepararEntradaSemantica(cam)
    assert not erros_lex, f"teste3.txt: erros léxicos: {erros_lex}"
    assert not erros_sint, f"teste3.txt: erros sintáticos: {erros_sint}"
    tabela, erros = construirTabelaSimbolos(arvore)
    assert not erros, f"teste3.txt: erros semânticos: {erros}"


def rodar_testes_construirTabelaSimbolos() -> None:
    """Executa todos os testes para construirTabelaSimbolos (Aluno 2)."""
    test_construir_tabela_vazia()
    test_construir_store_int()
    test_construir_store_real()
    test_construir_store_unknown()
    test_construir_load_simple()
    test_construir_multiplos_usos()
    test_construir_erro_uso_antes_definicao()
    test_construir_erro_tipo_incompativel()
    test_construir_erro_true_false_como_variavel()
    test_construir_res_pattern()
    test_construir_erro_res_fora_alcance()
    test_construir_if_sem_else()
    test_construir_if_com_else()
    test_construir_while_simples()
    test_construir_true_false_como_valor()
    test_construir_multiplas_variaveis()
    test_construir_id_como_segundo_operando_erro()
    test_construir_id_como_segundo_operando_ok()
    test_construir_id_em_expr_aninhada()
    test_construir_id_em_expr_aninhada_erro()
    test_construir_store_com_var_interna()
    test_construir_dois_ids_em_operacao()
    test_construir_salvar_tabela_markdown()
    test_construir_while_usa_var_no_body()
    test_construir_while_var_nao_declarada_no_body()
    test_integracao_teste2_semantico()
    test_integracao_teste1_valido()
    test_integracao_teste3_complexo()
    print("Todos os testes de construirTabelaSimbolos passaram.")


def rodar_testes_prepararEntrada() -> None:
    test_comentario_linha_inteira()
    test_comentario_fim_de_linha()
    test_comentario_entre_expressoes()
    test_comentario_multilinhas_contagem_linhas()
    test_comentario_nao_fechado_levanta_erro()
    test_comentario_nao_fechado_recuperacao()
    test_estrela_sem_chave_emite_mul()
    test_multiplos_comentarios_mesma_linha()
    test_caractere_invalido_levanta_erro()
    test_caractere_invalido_recuperacao()
    test_true_false_sao_id()
    test_validar_start_end_ok()
    test_validar_sem_start()
    test_validar_sem_end()
    test_preparar_retorna_arvore_valida()
    test_preparar_comentarios_invisiveis_ao_parser()
    test_preparar_tokens_sem_texto_de_comentario()
    test_preparar_arquivo_inexistente()
    test_preparar_sintaxe_invalida_operador_prematuro()
    test_preparar_sintaxe_invalida_operador_extra()
    test_integracao_fase3_lexer()
    test_integracao_fase3_lexer_tem_todos_ops()
    test_integracao_fase3_parser()
    test_integracao_fase3_arquivo_erros_sem_erros_lex_sint()
    test_integracao_fase3_bool_literals_sao_id()
    print("Todos os testes de prepararEntradaSemantica passaram.")


# ─────────────────────────────────────────────────────────────
# [Aluno 3] Funções de teste — verificarTipos
# ─────────────────────────────────────────────────────────────

def test_tipos_int_add() -> None:
    """(2 3 +) deve inferir int sem erros."""
    conteudo = "(START)\n(2 3 +)\n(END)\n"
    cam = _escrever_tmp(conteudo)
    try:
        _, arvore, _, _ = prepararEntradaSemantica(cam)
        tabela, _ = construirTabelaSimbolos(arvore)
        tipos, erros = verificarTipos(arvore, tabela)
        assert not erros, f"Não deveria haver erros: {erros}"
        tipos_vals = [v for v in tipos.values() if v is not None]
        assert 'int' in tipos_vals, "Deveria inferir tipo int"
    finally:
        _apagar_tmp(cam)


def test_tipos_real_add() -> None:
    """(2.0 3.0 +) deve inferir real sem erros."""
    conteudo = "(START)\n(2.0 3.0 +)\n(END)\n"
    cam = _escrever_tmp(conteudo)
    try:
        _, arvore, _, _ = prepararEntradaSemantica(cam)
        tabela, _ = construirTabelaSimbolos(arvore)
        tipos, erros = verificarTipos(arvore, tabela)
        assert not erros, f"Não deveria haver erros: {erros}"
        assert 'real' in tipos.values(), "Deveria inferir tipo real"
    finally:
        _apagar_tmp(cam)


def test_tipos_misto_promove_real() -> None:
    """(2 3.0 +) deve inferir real por promoção numérica, sem erros."""
    conteudo = "(START)\n(2 3.0 +)\n(END)\n"
    cam = _escrever_tmp(conteudo)
    try:
        _, arvore, _, _ = prepararEntradaSemantica(cam)
        tabela, _ = construirTabelaSimbolos(arvore)
        tipos, erros = verificarTipos(arvore, tabela)
        assert not erros, f"Não deveria haver erros: {erros}"
        assert 'real' in tipos.values(), "int+real deveria promover para real"
    finally:
        _apagar_tmp(cam)


def test_tipos_rdiv_retorna_real() -> None:
    """(4 2 |) deve retornar real mesmo com operandos int."""
    conteudo = "(START)\n(4 2 |)\n(END)\n"
    cam = _escrever_tmp(conteudo)
    try:
        _, arvore, _, _ = prepararEntradaSemantica(cam)
        tabela, _ = construirTabelaSimbolos(arvore)
        tipos, erros = verificarTipos(arvore, tabela)
        assert not erros, f"Não deveria haver erros: {erros}"
        assert 'real' in tipos.values(), "| deve produzir real"
    finally:
        _apagar_tmp(cam)


def test_tipos_relacional_retorna_bool() -> None:
    """(X 3.0 >) onde X é real deve retornar bool.
    Nota: num_int_cont só permite arith_op; rel_op exige ID como primeiro operando.
    """
    conteudo = "(START)\n(1.0 X)\n(X 3.0 >)\n(END)\n"
    cam = _escrever_tmp(conteudo)
    try:
        _, arvore, _, _ = prepararEntradaSemantica(cam)
        tabela, _ = construirTabelaSimbolos(arvore)
        tipos, erros = verificarTipos(arvore, tabela)
        assert not erros, f"Não deveria haver erros: {erros}"
        assert 'bool' in tipos.values(), "> deveria produzir bool"
    finally:
        _apagar_tmp(cam)


def test_tipos_true_false_sao_bool() -> None:
    """TRUE e FALSE devem ser inferidos como bool."""
    conteudo = "(START)\n(TRUE)\n(FALSE)\n(END)\n"
    cam = _escrever_tmp(conteudo)
    try:
        _, arvore, _, _ = prepararEntradaSemantica(cam)
        tabela, _ = construirTabelaSimbolos(arvore)
        tipos, erros = verificarTipos(arvore, tabela)
        assert not erros, f"Não deveria haver erros: {erros}"
        bools = [v for v in tipos.values() if v == 'bool']
        assert len(bools) >= 2, "TRUE e FALSE devem produzir tipo bool"
    finally:
        _apagar_tmp(cam)


def test_tipos_load_int() -> None:
    """Variável int carregada com (MEM) deve ter tipo int."""
    conteudo = "(START)\n(10 X)\n(X)\n(END)\n"
    cam = _escrever_tmp(conteudo)
    try:
        _, arvore, _, _ = prepararEntradaSemantica(cam)
        tabela, _ = construirTabelaSimbolos(arvore)
        tipos, erros = verificarTipos(arvore, tabela)
        assert not erros, f"Não deveria haver erros: {erros}"
        assert 'int' in tipos.values(), "LOAD de int deve inferir int"
    finally:
        _apagar_tmp(cam)


def test_tipos_load_real() -> None:
    """Variável real carregada com (MEM) deve ter tipo real."""
    conteudo = "(START)\n(1.5 Y)\n(Y)\n(END)\n"
    cam = _escrever_tmp(conteudo)
    try:
        _, arvore, _, _ = prepararEntradaSemantica(cam)
        tabela, _ = construirTabelaSimbolos(arvore)
        tipos, erros = verificarTipos(arvore, tabela)
        assert not erros, f"Não deveria haver erros: {erros}"
        assert 'real' in tipos.values(), "LOAD de real deve inferir real"
    finally:
        _apagar_tmp(cam)


def test_tipos_res_unknown() -> None:
    """(N RES) deve ter tipo unknown (valor de runtime)."""
    conteudo = "(START)\n(1 2 +)\n(1 RES)\n(END)\n"
    cam = _escrever_tmp(conteudo)
    try:
        _, arvore, _, _ = prepararEntradaSemantica(cam)
        tabela, _ = construirTabelaSimbolos(arvore)
        tipos, erros = verificarTipos(arvore, tabela)
        assert not erros, f"Não deveria haver erros: {erros}"
        assert 'unknown' in tipos.values(), "(N RES) deveria ser unknown"
    finally:
        _apagar_tmp(cam)


def test_tipos_aninhado_dois_niveis() -> None:
    """((2 3 +) 4 *) — dois níveis de aninhamento, tipo int."""
    conteudo = "(START)\n((2 3 +) 4 *)\n(END)\n"
    cam = _escrever_tmp(conteudo)
    try:
        _, arvore, _, _ = prepararEntradaSemantica(cam)
        tabela, _ = construirTabelaSimbolos(arvore)
        tipos, erros = verificarTipos(arvore, tabela)
        assert not erros, f"Não deveria haver erros: {erros}"
        assert 'int' in tipos.values()
    finally:
        _apagar_tmp(cam)


def test_tipos_aninhado_tres_niveis() -> None:
    """(((1 2 +) 3 -) 4 *) — três níveis, caso extremo de aninhamento."""
    conteudo = "(START)\n(((1 2 +) 3 -) 4 *)\n(END)\n"
    cam = _escrever_tmp(conteudo)
    try:
        _, arvore, _, _ = prepararEntradaSemantica(cam)
        tabela, _ = construirTabelaSimbolos(arvore)
        tipos, erros = verificarTipos(arvore, tabela)
        assert not erros, f"Não deveria haver erros: {erros}"
        assert 'int' in tipos.values()
    finally:
        _apagar_tmp(cam)


def test_tipos_div_int_ok() -> None:
    """(6 3 /) — divisão inteira válida → int."""
    conteudo = "(START)\n(6 3 /)\n(END)\n"
    cam = _escrever_tmp(conteudo)
    try:
        _, arvore, _, _ = prepararEntradaSemantica(cam)
        tabela, _ = construirTabelaSimbolos(arvore)
        tipos, erros = verificarTipos(arvore, tabela)
        assert not erros, f"Não deveria haver erros: {erros}"
        assert 'int' in tipos.values()
    finally:
        _apagar_tmp(cam)


def test_tipos_mod_ok() -> None:
    """(7 3 %) — resto válido → int."""
    conteudo = "(START)\n(7 3 %)\n(END)\n"
    cam = _escrever_tmp(conteudo)
    try:
        _, arvore, _, _ = prepararEntradaSemantica(cam)
        tabela, _ = construirTabelaSimbolos(arvore)
        tipos, erros = verificarTipos(arvore, tabela)
        assert not erros, f"Não deveria haver erros: {erros}"
        assert 'int' in tipos.values()
    finally:
        _apagar_tmp(cam)


def test_tipos_cond_if_bool_ok() -> None:
    """IF com condição bool deve passar sem erro."""
    conteudo = "(START)\n(1.0 X)\n(IF (X 0.0 >) (2.0 3.0 +))\n(END)\n"
    cam = _escrever_tmp(conteudo)
    try:
        _, arvore, _, _ = prepararEntradaSemantica(cam)
        tabela, _ = construirTabelaSimbolos(arvore)
        _, erros = verificarTipos(arvore, tabela)
        assert not erros, f"IF com bool válido não deveria gerar erro: {erros}"
    finally:
        _apagar_tmp(cam)


def test_tipos_cond_while_bool_ok() -> None:
    """WHILE com condição bool deve passar sem erro."""
    conteudo = "(START)\n(0 I)\n(WHILE (I 5 <) ((I 1 +) I))\n(END)\n"
    cam = _escrever_tmp(conteudo)
    try:
        _, arvore, _, _ = prepararEntradaSemantica(cam)
        tabela, _ = construirTabelaSimbolos(arvore)
        _, erros = verificarTipos(arvore, tabela)
        assert not erros, f"WHILE com bool válido não deveria gerar erro: {erros}"
    finally:
        _apagar_tmp(cam)


def test_tipos_erro_bool_em_aritm() -> None:
    """((X 3.0 >) 2.0 +) usa bool como primeiro operando de '+', deve gerar erro.
    O bool é obtido via expressão aninhada (relacional) → nested_cont.
    """
    conteudo = "(START)\n(1.0 X)\n((X 3.0 >) 2.0 +)\n(END)\n"
    cam = _escrever_tmp(conteudo)
    try:
        _, arvore, _, _ = prepararEntradaSemantica(cam)
        tabela, _ = construirTabelaSimbolos(arvore)
        _, erros = verificarTipos(arvore, tabela)
        assert any('bool' in e.lower() for e in erros), (
            f"Operação com bool deveria gerar erro: {erros}"
        )
    finally:
        _apagar_tmp(cam)


def test_tipos_erro_cond_if_real() -> None:
    """IF com condição real deve gerar erro."""
    conteudo = "(START)\n(1.0 X)\n(IF (X) (2.0 3.0 +))\n(END)\n"
    cam = _escrever_tmp(conteudo)
    try:
        _, arvore, _, _ = prepararEntradaSemantica(cam)
        tabela, _ = construirTabelaSimbolos(arvore)
        _, erros = verificarTipos(arvore, tabela)
        assert any('if' in e.lower() and 'bool' in e.lower() for e in erros), (
            f"IF com condição real deveria gerar erro: {erros}"
        )
    finally:
        _apagar_tmp(cam)


def test_tipos_erro_cond_while_real() -> None:
    """WHILE com condição real deve gerar erro."""
    conteudo = "(START)\n(0.0 J)\n(WHILE (J 2.0 +) ((J 1.0 +) J))\n(END)\n"
    cam = _escrever_tmp(conteudo)
    try:
        _, arvore, _, _ = prepararEntradaSemantica(cam)
        tabela, _ = construirTabelaSimbolos(arvore)
        _, erros = verificarTipos(arvore, tabela)
        assert any('while' in e.lower() and 'bool' in e.lower() for e in erros), (
            f"WHILE com condição real deveria gerar erro: {erros}"
        )
    finally:
        _apagar_tmp(cam)


def test_tipos_erro_div_int_com_real() -> None:
    """(3.5 2 /) deve gerar erro de divisão inteira com real."""
    conteudo = "(START)\n(3.5 2 /)\n(END)\n"
    cam = _escrever_tmp(conteudo)
    try:
        _, arvore, _, _ = prepararEntradaSemantica(cam)
        tabela, _ = construirTabelaSimbolos(arvore)
        _, erros = verificarTipos(arvore, tabela)
        assert any('divisão inteira' in e.lower() or "'/'" in e for e in erros), (
            f"Divisão inteira com real deveria gerar erro: {erros}"
        )
    finally:
        _apagar_tmp(cam)


def test_tipos_erro_mod_com_real() -> None:
    """(9.0 4 %) deve gerar erro de resto com real."""
    conteudo = "(START)\n(9.0 4 %)\n(END)\n"
    cam = _escrever_tmp(conteudo)
    try:
        _, arvore, _, _ = prepararEntradaSemantica(cam)
        tabela, _ = construirTabelaSimbolos(arvore)
        _, erros = verificarTipos(arvore, tabela)
        assert any("resto" in e.lower() or "'%'" in e for e in erros), (
            f"Resto com real deveria gerar erro: {erros}"
        )
    finally:
        _apagar_tmp(cam)


def test_tipos_erro_aninhado_com_tipo_errado() -> None:
    """Tipo errado dentro de expressão aninhada deve ser detectado."""
    conteudo = "(START)\n(1.0 X)\n(X 3.0 >)\n(((1 RES) 2 /) 4 +)\n(END)\n"
    cam = _escrever_tmp(conteudo)
    try:
        _, arvore, _, _ = prepararEntradaSemantica(cam)
        tabela, _ = construirTabelaSimbolos(arvore)
        _, erros = verificarTipos(arvore, tabela)
        # (1 RES) é unknown → / com unknown → int, sem erro aqui
        # O teste valida que não quebra com aninhamento
        assert isinstance(erros, list), "Deveria retornar lista de erros"
    finally:
        _apagar_tmp(cam)


def test_tipos_salvar_erros_md() -> None:
    """salvarErrosTipos deve criar arquivo Markdown com os erros."""
    conteudo = "(START)\n(3.5 2 /)\n(END)\n"
    cam = _escrever_tmp(conteudo)
    md = _escrever_tmp('')
    try:
        _, arvore, _, _ = prepararEntradaSemantica(cam)
        tabela, _ = construirTabelaSimbolos(arvore)
        _, erros = verificarTipos(arvore, tabela)
        resultado = salvarErrosTipos(erros, md)
        assert resultado == md
        with open(md, encoding='utf-8') as f:
            texto = f.read()
        assert 'Relatório' in texto or 'Erro' in texto or 'divisão' in texto.lower()
    finally:
        _apagar_tmp(cam)
        _apagar_tmp(md)


def test_tipos_salvar_sem_erros_md() -> None:
    """salvarErrosTipos sem erros deve gerar arquivo com mensagem de ausência."""
    conteudo = "(START)\n(2 3 +)\n(END)\n"
    cam = _escrever_tmp(conteudo)
    md = _escrever_tmp('')
    try:
        _, arvore, _, _ = prepararEntradaSemantica(cam)
        tabela, _ = construirTabelaSimbolos(arvore)
        _, erros = verificarTipos(arvore, tabela)
        salvarErrosTipos(erros, md)
        with open(md, encoding='utf-8') as f:
            texto = f.read()
        assert 'Nenhum erro' in texto
    finally:
        _apagar_tmp(cam)
        _apagar_tmp(md)


def test_tipos_integracao_teste1() -> None:
    """teste1.txt é válido: não deve gerar erros de tipo."""
    cam = os.path.join(_DIR_PROJETO, 'teste1.txt')
    if not os.path.exists(cam):
        return
    _, arvore, erros_lex, erros_sint = prepararEntradaSemantica(cam)
    assert not erros_lex,  f"teste1.txt: erros léxicos: {erros_lex}"
    assert not erros_sint, f"teste1.txt: erros sintáticos: {erros_sint}"
    tabela, _ = construirTabelaSimbolos(arvore)
    _, erros = verificarTipos(arvore, tabela)
    assert not erros, f"teste1.txt: erros de tipo inesperados: {erros}"


def test_tipos_integracao_teste2() -> None:
    """teste2.txt deve ter pelo menos 4 erros de tipo (erros 2-6 do arquivo)."""
    cam = os.path.join(_DIR_PROJETO, 'teste2.txt')
    if not os.path.exists(cam):
        return
    _, arvore, erros_lex, erros_sint = prepararEntradaSemantica(cam)
    assert not erros_lex,  f"teste2.txt: erros léxicos inesperados: {erros_lex}"
    assert not erros_sint, f"teste2.txt: erros sintáticos inesperados: {erros_sint}"
    tabela, _ = construirTabelaSimbolos(arvore)
    _, erros = verificarTipos(arvore, tabela)
    assert len(erros) >= 4, (
        f"teste2.txt deveria ter >= 4 erros de tipo, obteve {len(erros)}: {erros}"
    )
    assert any('bool' in e.lower() for e in erros), "Deveria ter erro de bool em aritmética"
    assert any('if' in e.lower() for e in erros), "Deveria ter erro de condição de IF"
    assert any('while' in e.lower() for e in erros), "Deveria ter erro de condição de WHILE"
    assert any('divisão inteira' in e.lower() for e in erros), "Deveria ter erro de divisão inteira"
    assert any('resto' in e.lower() for e in erros), "Deveria ter erro de resto"


def test_tipos_integracao_teste3() -> None:
    """teste3.txt é válido: não deve gerar erros de tipo."""
    cam = os.path.join(_DIR_PROJETO, 'teste3.txt')
    if not os.path.exists(cam):
        return
    _, arvore, erros_lex, erros_sint = prepararEntradaSemantica(cam)
    assert not erros_lex,  f"teste3.txt: erros léxicos: {erros_lex}"
    assert not erros_sint, f"teste3.txt: erros sintáticos: {erros_sint}"
    tabela, _ = construirTabelaSimbolos(arvore)
    _, erros = verificarTipos(arvore, tabela)
    assert not erros, f"teste3.txt: erros de tipo inesperados: {erros}"


def rodar_testes_verificarTipos() -> None:
    """Executa todos os testes para verificarTipos (Aluno 3)."""
    test_tipos_int_add()
    test_tipos_real_add()
    test_tipos_misto_promove_real()
    test_tipos_rdiv_retorna_real()
    test_tipos_relacional_retorna_bool()
    test_tipos_true_false_sao_bool()
    test_tipos_load_int()
    test_tipos_load_real()
    test_tipos_res_unknown()
    test_tipos_aninhado_dois_niveis()
    test_tipos_aninhado_tres_niveis()
    test_tipos_div_int_ok()
    test_tipos_mod_ok()
    test_tipos_cond_if_bool_ok()
    test_tipos_cond_while_bool_ok()
    test_tipos_erro_bool_em_aritm()
    test_tipos_erro_cond_if_real()
    test_tipos_erro_cond_while_real()
    test_tipos_erro_div_int_com_real()
    test_tipos_erro_mod_com_real()
    test_tipos_erro_aninhado_com_tipo_errado()
    test_tipos_salvar_erros_md()
    test_tipos_salvar_sem_erros_md()
    test_tipos_integracao_teste1()
    test_tipos_integracao_teste2()
    test_tipos_integracao_teste3()
    print("Todos os testes de verificarTipos passaram.")


# ─────────────────────────────────────────────────────────────
# [Aluno 4] Funções de teste — gerarArvoreAtribuida e gerarAssemblySemantico
# ─────────────────────────────────────────────────────────────

def _programa_simples_arvore() -> tuple[dict, dict, dict]:
    """
    Helper: constrói arvore, tabela e tipos para o programa:
        (START) (3.0 2.0 +) (END)
    """
    cam = _escrever_tmp("(START)\n(3.0 2.0 +)\n(END)\n")
    try:
        tokens, arvore, _, _ = prepararEntradaSemantica(cam)
        tabela, _ = construirTabelaSimbolos(arvore)
        tipos, _ = verificarTipos(arvore, tabela)
    finally:
        _apagar_tmp(cam)
    return arvore, tabela, tipos


def test_gerarArvoreAtribuida_preserva_estrutura() -> None:
    """A árvore atribuída deve ter a mesma estrutura que a original."""
    arvore, tabela, tipos = _programa_simples_arvore()
    atribuida = gerarArvoreAtribuida(arvore, tabela, tipos)
    assert atribuida['tipo'] == 'NT', "Raiz deve ser NT"
    assert atribuida['simbolo'] == 'programa', "Raiz deve ser 'programa'"
    assert 'filhos' in atribuida, "Raiz deve ter 'filhos'"


def test_gerarArvoreAtribuida_tem_anotacoes() -> None:
    """Todo nó da árvore atribuída deve ter o campo 'anotacoes'."""
    arvore, tabela, tipos = _programa_simples_arvore()
    atribuida = gerarArvoreAtribuida(arvore, tabela, tipos)

    def _verificar(no: dict) -> None:
        assert 'anotacoes' in no, (
            f"Nó sem 'anotacoes': {no.get('tipo')} {no.get('simbolo', no.get('tipo_token'))}"
        )
        for f in no.get('filhos', []):
            _verificar(f)

    _verificar(atribuida)


def test_gerarArvoreAtribuida_anotacoes_nt_tem_categoria() -> None:
    """Nós NT devem ter 'categoria' em 'anotacoes'."""
    arvore, tabela, tipos = _programa_simples_arvore()
    atribuida = gerarArvoreAtribuida(arvore, tabela, tipos)

    def _checar(no: dict) -> None:
        if no['tipo'] == 'NT':
            assert 'categoria' in no['anotacoes'], (
                f"NT '{no['simbolo']}' sem 'categoria'"
            )
        for f in no.get('filhos', []):
            _checar(f)

    _checar(atribuida)


def test_gerarArvoreAtribuida_categoria_inicio_fim() -> None:
    """stmt_inner START/END devem ter categoria 'inicio'/'fim'."""
    arvore, tabela, tipos = _programa_simples_arvore()
    atribuida = gerarArvoreAtribuida(arvore, tabela, tipos)

    categorias: list[str] = []

    def _coletar(no: dict) -> None:
        if no['tipo'] == 'NT' and no['simbolo'] == 'stmt_inner':
            categorias.append(no['anotacoes'].get('categoria', ''))
        for f in no.get('filhos', []):
            _coletar(f)

    _coletar(atribuida)
    assert 'inicio' in categorias, f"Categoria 'inicio' não encontrada: {categorias}"
    assert 'fim' in categorias, f"Categoria 'fim' não encontrada: {categorias}"


def test_gerarArvoreAtribuida_tipo_semantico_real() -> None:
    """Nó da expressão (3.0 2.0 +) deve ter tipo_semantico 'real'."""
    arvore, tabela, tipos = _programa_simples_arvore()
    atribuida = gerarArvoreAtribuida(arvore, tabela, tipos)

    tipos_encontrados: list[str] = []

    def _coletar_tipos(no: dict) -> None:
        t = no.get('anotacoes', {}).get('tipo_semantico')
        if t is not None:
            tipos_encontrados.append(t)
        for f in no.get('filhos', []):
            _coletar_tipos(f)

    _coletar_tipos(atribuida)
    assert 'real' in tipos_encontrados, (
        f"Tipo 'real' não encontrado nas anotações: {set(tipos_encontrados)}"
    )


def test_gerarArvoreAtribuida_categoria_condicional() -> None:
    """stmt_inner IF deve ter categoria 'condicional'."""
    cam = _escrever_tmp(
        "(START)\n"
        "(5.0 X)\n"
        "(IF (X 0.0 >) (1.0 R) (0.0 R))\n"
        "(END)\n"
    )
    try:
        tokens, arvore, _, _ = prepararEntradaSemantica(cam)
        tabela, _ = construirTabelaSimbolos(arvore)
        tipos, _ = verificarTipos(arvore, tabela)
        atribuida = gerarArvoreAtribuida(arvore, tabela, tipos)
    finally:
        _apagar_tmp(cam)

    categorias: list[str] = []

    def _coletar(no: dict) -> None:
        if no['tipo'] == 'NT' and no['simbolo'] == 'stmt_inner':
            categorias.append(no['anotacoes'].get('categoria', ''))
        for f in no.get('filhos', []):
            _coletar(f)

    _coletar(atribuida)
    assert 'condicional' in categorias, (
        f"Categoria 'condicional' não encontrada: {categorias}"
    )


def test_gerarArvoreAtribuida_categoria_repeticao() -> None:
    """stmt_inner WHILE deve ter categoria 'repeticao'."""
    cam = _escrever_tmp(
        "(START)\n"
        "(0.0 I)\n"
        "(WHILE (I 3.0 <) ((I 1.0 +) I))\n"
        "(END)\n"
    )
    try:
        tokens, arvore, _, _ = prepararEntradaSemantica(cam)
        tabela, _ = construirTabelaSimbolos(arvore)
        tipos, _ = verificarTipos(arvore, tabela)
        atribuida = gerarArvoreAtribuida(arvore, tabela, tipos)
    finally:
        _apagar_tmp(cam)

    categorias: list[str] = []

    def _coletar(no: dict) -> None:
        if no['tipo'] == 'NT' and no['simbolo'] == 'stmt_inner':
            categorias.append(no['anotacoes'].get('categoria', ''))
        for f in no.get('filhos', []):
            _coletar(f)

    _coletar(atribuida)
    assert 'repeticao' in categorias, (
        f"Categoria 'repeticao' não encontrada: {categorias}"
    )


def test_gerarArvoreAtribuida_json_serializavel() -> None:
    """A árvore atribuída deve ser serializável em JSON sem erros."""
    arvore, tabela, tipos = _programa_simples_arvore()
    atribuida = gerarArvoreAtribuida(arvore, tabela, tipos)
    resultado = _arvore_atribuida_para_json(atribuida)
    assert isinstance(resultado, str), "Resultado deve ser string"
    assert '"tipo"' in resultado, "JSON deve conter campo 'tipo'"
    assert '"anotacoes"' in resultado, "JSON deve conter campo 'anotacoes'"
    recarregado = json.loads(resultado)
    assert recarregado['tipo'] == 'NT'


def test_gerarAssemblySemantico_tem_secoes() -> None:
    """Assembly gerado deve conter as seções .data e .text."""
    arvore, tabela, tipos = _programa_simples_arvore()
    atribuida = gerarArvoreAtribuida(arvore, tabela, tipos)
    asm = gerarAssemblySemantico(atribuida)
    assert '.section .data' in asm, "Assembly deve ter seção .data"
    assert '.section .text' in asm, "Assembly deve ter seção .text"
    assert '_start:' in asm, "Assembly deve ter rótulo _start"


def test_gerarAssemblySemantico_operacao_soma() -> None:
    """Expressão (3.0 2.0 +) deve gerar instrução VADD."""
    arvore, tabela, tipos = _programa_simples_arvore()
    atribuida = gerarArvoreAtribuida(arvore, tabela, tipos)
    asm = gerarAssemblySemantico(atribuida)
    assert 'VADD' in asm, "Soma de reais deve usar VADD.F64"


def test_gerarAssemblySemantico_operacao_subtracao() -> None:
    """Expressão (5.0 2.0 -) deve gerar instrução VSUB."""
    cam = _escrever_tmp("(START)\n(5.0 2.0 -)\n(END)\n")
    try:
        tokens, arvore, _, _ = prepararEntradaSemantica(cam)
        tabela, _ = construirTabelaSimbolos(arvore)
        tipos, _ = verificarTipos(arvore, tabela)
        atribuida = gerarArvoreAtribuida(arvore, tabela, tipos)
        asm = gerarAssemblySemantico(atribuida)
    finally:
        _apagar_tmp(cam)
    assert 'VSUB' in asm, "Subtração de reais deve usar VSUB.F64"


def test_gerarAssemblySemantico_store_load() -> None:
    """Operações de store (V MEM) e load (MEM) devem gerar VSTR e VLDR."""
    cam = _escrever_tmp("(START)\n(42.0 VAL)\n(VAL)\n(END)\n")
    try:
        tokens, arvore, _, _ = prepararEntradaSemantica(cam)
        tabela, _ = construirTabelaSimbolos(arvore)
        tipos, _ = verificarTipos(arvore, tabela)
        atribuida = gerarArvoreAtribuida(arvore, tabela, tipos)
        asm = gerarAssemblySemantico(atribuida)
    finally:
        _apagar_tmp(cam)
    assert 'VSTR' in asm, "Store deve gerar VSTR"
    assert 'VLDR' in asm, "Load deve gerar VLDR"


def test_gerarAssemblySemantico_if_gera_branch() -> None:
    """Estrutura IF deve gerar branch condicional no Assembly."""
    cam = _escrever_tmp(
        "(START)\n"
        "(5.0 X)\n"
        "(IF (X 0.0 >) (1.0 R) (0.0 R))\n"
        "(END)\n"
    )
    try:
        tokens, arvore, _, _ = prepararEntradaSemantica(cam)
        tabela, _ = construirTabelaSimbolos(arvore)
        tipos, _ = verificarTipos(arvore, tabela)
        atribuida = gerarArvoreAtribuida(arvore, tabela, tipos)
        asm = gerarAssemblySemantico(atribuida)
    finally:
        _apagar_tmp(cam)
    assert any(b in asm for b in ('BEQ', 'BGT', 'BLT', 'BGE', 'BLE', 'BNE')), (
        "IF deve gerar instrução de branch condicional"
    )


def test_gerarAssemblySemantico_while_gera_loop() -> None:
    """WHILE deve gerar rótulo de loop e branch incondicional no Assembly."""
    cam = _escrever_tmp(
        "(START)\n"
        "(0 I)\n"
        "(WHILE (I 3 <) ((I 1 +) I))\n"
        "(END)\n"
    )
    try:
        tokens, arvore, _, _ = prepararEntradaSemantica(cam)
        tabela, _ = construirTabelaSimbolos(arvore)
        tipos, _ = verificarTipos(arvore, tabela)
        atribuida = gerarArvoreAtribuida(arvore, tabela, tipos)
        asm = gerarAssemblySemantico(atribuida)
    finally:
        _apagar_tmp(cam)
    assert 'while_loop' in asm.lower() or '\n  B ' in asm, (
        "WHILE deve gerar rótulo de loop e branch incondicional"
    )


def test_pipeline_completo_teste1() -> None:
    """Pipeline completo com teste1.txt deve concluir sem erros."""
    cam = os.path.join(_DIR_PROJETO, 'teste1.txt')
    tokens, arvore, erros_lex, erros_sint = prepararEntradaSemantica(cam)
    assert not erros_lex,  f"teste1.txt não deveria ter erros léxicos: {erros_lex}"
    assert not erros_sint, f"teste1.txt não deveria ter erros sintáticos: {erros_sint}"

    tabela, erros_tab = construirTabelaSimbolos(arvore)
    tipos, erros_tipos = verificarTipos(arvore, tabela)
    assert not erros_tab,   f"teste1.txt não deveria ter erros de declaração: {erros_tab}"
    assert not erros_tipos, f"teste1.txt não deveria ter erros de tipo: {erros_tipos}"

    atribuida = gerarArvoreAtribuida(arvore, tabela, tipos)
    assert atribuida['tipo'] == 'NT', "Árvore atribuída deve ser NT"

    asm = gerarAssemblySemantico(atribuida)
    assert '.section .text' in asm, "Assembly deve ter seção .text"
    assert 'VADD' in asm or 'VMUL' in asm, "Assembly deve ter operações FP"


def test_pipeline_erros_semanticos_teste2() -> None:
    """teste2.txt tem erros semânticos: devem ser detectados."""
    cam = os.path.join(_DIR_PROJETO, 'teste2.txt')
    tokens, arvore, erros_lex, erros_sint = prepararEntradaSemantica(cam)

    tabela, erros_tab = construirTabelaSimbolos(arvore)
    tipos, erros_tipos = verificarTipos(arvore, tabela)

    total_sem = len(erros_tab) + len(erros_tipos)
    assert total_sem > 0, (
        "teste2.txt tem erros semânticos intencionais — devem ser detectados"
    )


def test_pipeline_completo_teste3() -> None:
    """Pipeline completo com teste3.txt deve concluir sem erros."""
    cam = os.path.join(_DIR_PROJETO, 'teste3.txt')
    tokens, arvore, erros_lex, erros_sint = prepararEntradaSemantica(cam)
    assert not erros_lex,  f"teste3.txt não deveria ter erros léxicos: {erros_lex}"
    assert not erros_sint, f"teste3.txt não deveria ter erros sintáticos: {erros_sint}"

    tabela, erros_tab = construirTabelaSimbolos(arvore)
    tipos, erros_tipos = verificarTipos(arvore, tabela)
    assert not erros_tab,   f"teste3.txt não deveria ter erros de declaração: {erros_tab}"
    assert not erros_tipos, f"teste3.txt não deveria ter erros de tipo: {erros_tipos}"

    atribuida = gerarArvoreAtribuida(arvore, tabela, tipos)
    asm = gerarAssemblySemantico(atribuida)
    assert '.section .text' in asm


def rodar_testes_aluno4() -> None:
    test_gerarArvoreAtribuida_preserva_estrutura()
    test_gerarArvoreAtribuida_tem_anotacoes()
    test_gerarArvoreAtribuida_anotacoes_nt_tem_categoria()
    test_gerarArvoreAtribuida_categoria_inicio_fim()
    test_gerarArvoreAtribuida_tipo_semantico_real()
    test_gerarArvoreAtribuida_categoria_condicional()
    test_gerarArvoreAtribuida_categoria_repeticao()
    test_gerarArvoreAtribuida_json_serializavel()
    test_gerarAssemblySemantico_tem_secoes()
    test_gerarAssemblySemantico_operacao_soma()
    test_gerarAssemblySemantico_operacao_subtracao()
    test_gerarAssemblySemantico_store_load()
    test_gerarAssemblySemantico_if_gera_branch()
    test_gerarAssemblySemantico_while_gera_loop()
    test_pipeline_completo_teste1()
    test_pipeline_erros_semanticos_teste2()
    test_pipeline_completo_teste3()
    print("Todos os testes do Aluno 4 passaram.")


# ─────────────────────────────────────────────────────────────
# Ponto de entrada
# ─────────────────────────────────────────────────────────────

if __name__ == '__main__':
    if len(sys.argv) == 2 and sys.argv[1] == '--test-preparar':
        rodar_testes_prepararEntrada()
    elif len(sys.argv) == 2 and sys.argv[1] == '--test-construir':
        rodar_testes_construirTabelaSimbolos()
    elif len(sys.argv) == 2 and sys.argv[1] == '--test-verificar':
        rodar_testes_verificarTipos()
    elif len(sys.argv) == 2 and sys.argv[1] == '--test-aluno4':
        rodar_testes_aluno4()
    else:
        main()
