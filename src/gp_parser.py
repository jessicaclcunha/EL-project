"""
Gramática da linguagem de especificação (Grammar Playground):

    Spec          -> Axioma RuleList TokenSection

    Axioma        -> START COLON NONTERM

    RuleList      -> Rule RuleList | ε
    Rule          -> NONTERM ARROW AltList newlines

    AltList       -> Body AltList'
    AltList'      -> PIPE Body AltList' | ε

    Body          -> Symbol SymbolList | epsilon
    SymbolList    -> Symbol SymbolList | ε

    Symbol        -> NONTERM | TERMINAL_NAME

    TokenSection  -> TokenDecl TokenSection | ε
    TokenDecl     -> TERMINAL_NAME EQUALS REGEX newlines

Notas:
    - O axioma é declarado explicitamente com 'start: NonTerm'.
      são TERMINAL_NAME declarados na TokenSection.
    - As newlines delimitam o fim de Axioma, Rule e TokenDecl.
    - Comentários (# ...) são ignorados pelo lexer.
"""

import ply.yacc as yacc
from gp_lexer import tokens, lexer
from gp_ast import (
    SpecNode, AxiomaNode, RuleListNode, RuleNode,
    AltListNode, SeqNode, SymbolNode,
    IdentifierNode, TerminalNameNode, StringNode, EpsilonNode,
    TokenSectionNode, TokenDeclNode, RegexNode,
)


# ---------------------------------------------------------------------------
# Spec
# ---------------------------------------------------------------------------

def p_spec(p):
    """spec : axioma newlines rulelist tokensection"""
    p[0] = SpecNode(axioma=p[1], rulelist=RuleListNode(p[3]), tokensection=TokenSectionNode(p[4]))


# ---------------------------------------------------------------------------
# Axioma
# ---------------------------------------------------------------------------

def p_axioma(p):
    """axioma : START COLON NONTERM"""
    p[0] = AxiomaNode(nonterm=IdentifierNode(p[3]))


# ---------------------------------------------------------------------------
# RuleList
# ---------------------------------------------------------------------------

def p_rulelist_nonempty(p):
    """rulelist : rule rulelist"""
    p[0] = [p[1]] + p[2]


def p_rulelist_empty(p):
    """rulelist : """
    p[0] = []


# ---------------------------------------------------------------------------
# Rule
# ---------------------------------------------------------------------------

def p_rule_with_newline(p):
    """rule : NONTERM ARROW altlist newlines"""
    p[0] = RuleNode(head=IdentifierNode(p[1]), altlist=AltListNode(p[3]))


def p_rule_without_newline(p):
    """rule : NONTERM ARROW altlist"""
    # Suporte para última regra sem newline no fim do ficheiro
    p[0] = RuleNode(head=IdentifierNode(p[1]), altlist=AltListNode(p[3]))


# ---------------------------------------------------------------------------
# AltList
# ---------------------------------------------------------------------------

def p_altlist(p):
    """altlist : body altlist_rest"""
    p[0] = [p[1]] + p[2]


def p_altlist_rest_nonempty(p):
    """altlist_rest : PIPE body altlist_rest"""
    p[0] = [p[2]] + p[3]


def p_altlist_rest_empty(p):
    """altlist_rest : """
    p[0] = []


# ---------------------------------------------------------------------------
# Body
# ---------------------------------------------------------------------------

def p_body_symbols(p):
    """body : symbol symbollist"""
    p[0] = SeqNode(symbols=[p[1]] + p[2])


def p_body_epsilon(p):
    """body : EPSILON"""
    p[0] = SeqNode(symbols=[SymbolNode(EpsilonNode())])


# ---------------------------------------------------------------------------
# SymbolList
# ---------------------------------------------------------------------------

def p_symbollist_nonempty(p):
    """symbollist : symbol symbollist"""
    p[0] = [p[1]] + p[2]


def p_symbollist_empty(p):
    """symbollist : """
    p[0] = []


# ---------------------------------------------------------------------------
# Symbol — NONTERM | TERMINAL_NAME | STRING
# ---------------------------------------------------------------------------

def p_symbol_nonterm(p):
    """symbol : NONTERM"""
    p[0] = SymbolNode(IdentifierNode(p[1]))


def p_symbol_quoted(p):
    """symbol : STRING"""
    p[0] = SymbolNode(StringNode(p[1]))


def p_symbol_terminal_name(p):
    """symbol : TERMINAL_NAME"""
    p[0] = SymbolNode(TerminalNameNode(p[1]))


# ---------------------------------------------------------------------------
# TokenSection
# ---------------------------------------------------------------------------

def p_tokensection_nonempty(p):
    """tokensection : tokendecl tokensection"""
    p[0] = [p[1]] + p[2]


def p_tokensection_empty(p):
    """tokensection : """
    p[0] = []


def p_tokendecl_with_newline(p):
    """tokendecl : TERMINAL_NAME EQUALS REGEX newlines"""
    p[0] = TokenDeclNode(name=TerminalNameNode(p[1]), regex=RegexNode(p[3]))


def p_tokendecl_without_newline(p):
    """tokendecl : TERMINAL_NAME EQUALS REGEX"""
    # Suporte para último token sem newline no fim do ficheiro
    p[0] = TokenDeclNode(name=TerminalNameNode(p[1]), regex=RegexNode(p[3]))


# ---------------------------------------------------------------------------
# Newlines (auxiliar)
# ---------------------------------------------------------------------------

def p_newlines(p):
    """newlines : NEWLINE
               | NEWLINE newlines"""
    pass


# ---------------------------------------------------------------------------
# Erros
# ---------------------------------------------------------------------------

def p_error(p):
    if p:
        print(f"[ERRO SINTÁTICO] Linha {p.lineno}: token inesperado '{p.value}' ({p.type})")
    else:
        print("[ERRO SINTÁTICO] Fim de ficheiro inesperado")


parser = yacc.yacc(start='spec')


def parse_grammar(source: str) -> SpecNode | None:
    """
    Recebe o texto da gramática e devolve a ASA (SpecNode) ou None em caso de erro.
    O axioma é declarado explicitamente via 'start: NonTerm'.
    """
    lexer.lineno = 1
    return parser.parse(source, lexer=lexer)