import ply.yacc as yacc
from gp_lexer import tokens, lexer
from gp_ast import (
    SpecNode, AxiomaNode, RuleListNode, RuleNode,
    AltListNode, SeqNode, SymbolNode,
    IdentifierNode, TerminalNameNode, EpsilonNode,
    TokenSectionNode, TokenDeclNode, RegexNode,
)


_parse_errors = []


def p_spec(p):
    """spec : axioma newlines rulelist tokensection"""
    p[0] = SpecNode(
        axioma=p[1],
        rulelist=RuleListNode(p[3]),
        tokensection=TokenSectionNode(p[4]),
    )



def p_axioma(p):
    """axioma : START COLON NON_TERMINAL"""
    p[0] = AxiomaNode(nonterm=IdentifierNode(p[3]))



def p_rulelist_nonempty(p):
    """rulelist : rule rulelist"""
    p[0] = [p[1]] + p[2]


def p_rulelist_empty(p):
    """rulelist : """
    p[0] = []



def p_rule_with_newline(p):
    """rule : NON_TERMINAL ARROW altlist newlines"""
    p[0] = RuleNode(head=IdentifierNode(p[1]), altlist=AltListNode(p[3]))


def p_rule_without_newline(p):
    """rule : NON_TERMINAL ARROW altlist"""
    p[0] = RuleNode(head=IdentifierNode(p[1]), altlist=AltListNode(p[3]))



def p_altlist(p):
    """altlist : body altlist_rest"""
    p[0] = [p[1]] + p[2]


def p_altlist_rest_nonempty(p):
    """altlist_rest : PIPE body altlist_rest"""
    p[0] = [p[2]] + p[3]


def p_altlist_rest_empty(p):
    """altlist_rest : """
    p[0] = []



def p_body_symbols(p):
    """body : symbol symbollist"""
    p[0] = SeqNode(symbols=[p[1]] + p[2])


def p_body_epsilon(p):
    """body : EPSILON"""
    p[0] = SeqNode(symbols=[SymbolNode(EpsilonNode())])



def p_symbollist_nonempty(p):
    """symbollist : symbol symbollist"""
    p[0] = [p[1]] + p[2]


def p_symbollist_empty(p):
    """symbollist : """
    p[0] = []



def p_symbol_nonterm(p):
    """symbol : NON_TERMINAL"""
    p[0] = SymbolNode(IdentifierNode(p[1]))


def p_symbol_terminal(p):
    """symbol : TERMINAL"""
    p[0] = SymbolNode(TerminalNameNode(p[1]))



def p_tokensection_nonempty(p):
    """tokensection : tokendecl tokensection"""
    p[0] = [p[1]] + p[2]


def p_tokensection_empty(p):
    """tokensection : """
    p[0] = []


def p_tokendecl_with_newline(p):
    """tokendecl : TERMINAL EQUALS REGEX newlines"""
    p[0] = TokenDeclNode(name=TerminalNameNode(p[1]), regex=RegexNode(p[3]))


def p_tokendecl_without_newline(p):
    """tokendecl : TERMINAL EQUALS REGEX"""
    p[0] = TokenDeclNode(name=TerminalNameNode(p[1]), regex=RegexNode(p[3]))



def p_newlines(p):
    """newlines : NEWLINE
               | NEWLINE newlines"""
    pass



def p_error(p):
    if p:
        msg = f"[ERRO SINTÁTICO] Linha {p.lineno}: token inesperado '{p.value}' ({p.type})"
    else:
        msg = "[ERRO SINTÁTICO] Fim de ficheiro inesperado"
    _parse_errors.append(msg)
    print(msg)


parser = yacc.yacc(start='spec')



def _merge_rules(rules):
    """
    Funde regras com o mesmo não-terminal numa única RuleNode.
    """
    if not rules:
        return rules

    merged = {}   # nome → RuleNode
    order = []    # preservar ordem de primeira aparição

    for rule in rules:
        name = rule.get_head_name()
        if name in merged:
            # Adicionar as alternativas à regra existente
            merged[name].altlist.sequences.extend(rule.altlist.sequences)
        else:
            merged[name] = rule
            order.append(name)

    return [merged[name] for name in order]



_parse_warnings = []


def parse_grammar(source: str) -> SpecNode | None:
    """
    Recebe o texto da gramática e devolve a ASA (SpecNode) ou None em caso de erro.
        1. Parsing (lexer + parser PLY)
        2. Fusão de regras do mesmo não-terminal
        3. Validação semântica
    """
    _parse_errors.clear()
    _parse_warnings.clear()
    lexer.lineno = 1
    result = parser.parse(source, lexer=lexer)

    if result is None:
        return None

    # Fundir regras do mesmo não-terminal
    result.rulelist.rules = _merge_rules(result.rulelist.rules)

    # Validação semântica
    errors, warnings = result.validate()
    for e in errors:
        msg = f"[ERRO SEMÂNTICO] {e}"
        _parse_errors.append(msg)
        print(msg)
    for w in warnings:
        msg = f"[AVISO] {w}"
        _parse_warnings.append(msg)
        print(msg)

    if errors:
        return None

    return result


def get_parse_errors() -> list[str]:
    """Devolve a lista de erros acumulados no último parse."""
    return list(_parse_errors)


def get_parse_warnings() -> list[str]:
    """Devolve a lista de avisos acumulados no último parse."""
    return list(_parse_warnings)