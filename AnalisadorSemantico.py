# Integrantes do grupo (ordem alfabética):
# André Vinícius Zicka Schmidt - andrevzs
# Gabriel Fischer Domakoski - fochu3013
#
# Nome do grupo no Canvas: RA3_19

import sys
import os
import tempfile

from AnalisadorSintatico import (
    EPSILON,
    EOF,
    MAPA_TOKENS,
    construirGramatica,
    parsear,
    gerarArvore,
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
# [Aluno 2] construirTabelaSimbolos — stub
# ─────────────────────────────────────────────────────────────

def construirTabelaSimbolos(arvore: dict) -> tuple[dict, list[str]]:
    """
    (Aluno 2) Percorre a árvore sintática e constrói a tabela de símbolos.

    Entrada:
        arvore — árvore sintática inicial produzida por prepararEntradaSemantica()

    Saída:
        (tabela, erros) onde:
          - tabela : dict[nome → {tipo, linha_def, linha_uso}]
          - erros  : lista de erros semânticos de declaração/uso
    """
    raise NotImplementedError("construirTabelaSimbolos será implementado pelo Aluno 2")


# ─────────────────────────────────────────────────────────────
# [Aluno 3] verificarTipos — stub
# ─────────────────────────────────────────────────────────────

def verificarTipos(arvore: dict, tabela: dict) -> tuple[dict, list[str]]:
    """
    (Aluno 3) Valida os tipos das expressões e comandos na árvore.

    Entrada:
        arvore — árvore sintática inicial
        tabela — tabela de símbolos de construirTabelaSimbolos()

    Saída:
        (tipos, erros) onde:
          - tipos : dict mapeando id de nó → tipo inferido ('int', 'real', 'bool')
          - erros : lista de erros semânticos de tipo
    """
    raise NotImplementedError("verificarTipos será implementado pelo Aluno 3")


# ─────────────────────────────────────────────────────────────
# [Aluno 4] gerarArvoreAtribuida e gerarAssemblySemantico — stubs
# ─────────────────────────────────────────────────────────────

def gerarArvoreAtribuida(arvore: dict, tabela: dict, tipos: dict) -> dict:
    """
    (Aluno 4) Produz a árvore sintática aumentada com anotações semânticas.

    Entrada:
        arvore — árvore sintática inicial
        tabela — tabela de símbolos
        tipos  — tipos inferidos por verificarTipos()

    Saída:
        dict com a árvore anotada com tipo, categoria semântica e dados
        necessários para a geração de Assembly
    """
    raise NotImplementedError("gerarArvoreAtribuida será implementado pelo Aluno 4")


def gerarAssemblySemantico(arvoreAtribuida: dict) -> str:
    """
    (Aluno 4) Gera código Assembly ARMv7 a partir da árvore sintática atribuída.

    Só deve ser chamada após validação semântica completa (sem erros).

    Entrada:
        arvoreAtribuida — árvore produzida por gerarArvoreAtribuida()

    Saída:
        string com código Assembly para Cpulator-ARMv7 DEC1-SOC(v16.1)
    """
    raise NotImplementedError("gerarAssemblySemantico será implementado pelo Aluno 4")


# ─────────────────────────────────────────────────────────────
# [Aluno 4] main() — stub de integração
# ─────────────────────────────────────────────────────────────

def main() -> None:
    """
    (Aluno 4) Ponto de entrada do AnalisadorSemantico.

    Coordena: léxico → sintático → semântico → árvore atribuída → Assembly.
    Execução via linha de comando: python AnalisadorSemantico.py <arquivo.txt>
    """
    raise NotImplementedError("main() será implementado pelo Aluno 4")


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
    test_integracao_fase3_lexer()
    test_integracao_fase3_lexer_tem_todos_ops()
    test_integracao_fase3_parser()
    test_integracao_fase3_arquivo_erros_sem_erros_lex_sint()
    test_integracao_fase3_bool_literals_sao_id()
    print("Todos os testes de prepararEntradaSemantica passaram.")


# ─────────────────────────────────────────────────────────────
# Ponto de entrada
# ─────────────────────────────────────────────────────────────

if __name__ == '__main__':
    if len(sys.argv) == 2 and sys.argv[1] == '--test-preparar':
        rodar_testes_prepararEntrada()
    else:
        main()
