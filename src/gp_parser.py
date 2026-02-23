import ply.yacc as yacc
from gp_lexer import tokens, lexer
from gp_ast import (
    GrammarNode, RuleListNode, RuleNode,
    AltListNode, SeqNode, SymbolNode,
    NonTermNode, TermNode, EpsilonNode,
    IdentifierNode, QuotedStringNode, NewlineNode,
)


def p_grammar(p):
    """grammar : START_KW IDENTIFIER newlines rulelist"""
    p[0] = GrammarNode(
        start_nonterm=NonTermNode(identifier=IdentifierNode(p[2])),
        rulelist=RuleListNode(rules=p[4]),
    )


def p_rulelist_multiple(p):
    """rulelist : rule rulelist"""
    p[0] = [p[1]] + p[2]


def p_rulelist_single(p):
    """rulelist : rule"""
    p[0] = [p[1]]


def p_rule(p):
    """rule : IDENTIFIER ARROW altlist newlines
            | IDENTIFIER ARROW altlist"""
    p[0] = RuleNode(
        head=NonTermNode(identifier=IdentifierNode(p[1])),
        altlist=AltListNode(sequences=p[3]),
        newline=NewlineNode(),
    )


def p_altlist_multiple(p):
    """altlist : seq PIPE altlist"""
    p[0] = [p[1]] + p[3]


def p_altlist_single(p):
    """altlist : seq"""
    p[0] = [p[1]]


def p_seq_symbol(p):
    """seq : symbol seq"""
    p[0] = SeqNode(symbols=[p[1]] + p[2].symbols)


def p_seq_empty(p):
    """seq : """
    p[0] = SeqNode(symbols=[])


def p_symbol_identifier(p):
    """symbol : IDENTIFIER"""
    p[0] = SymbolNode(child=NonTermNode(identifier=IdentifierNode(p[1])))


def p_symbol_quoted(p):
    """symbol : QUOTED_STRING"""
    p[0] = SymbolNode(child=TermNode(quoted=QuotedStringNode(p[1])))


def p_symbol_epsilon(p):
    """symbol : EPSILON"""
    p[0] = SymbolNode(child=EpsilonNode())


def p_newlines(p):
    """newlines : NEWLINE
               | NEWLINE newlines"""
    pass


def p_error(p):
    if p:
        print(f"[ERRO SINTÁTICO] Linha {p.lineno}: token inesperado '{p.value}' ({p.type})")
    else:
        print("[ERRO SINTÁTICO] Fim de ficheiro inesperado")


parser = yacc.yacc()


def parse_grammar(source):
    lexer.lineno = 1
    return parser.parse(source, lexer=lexer)