"""
Léxico da linguagem de especificação de gramáticas (Grammar Playground)

Tokens reconhecidos:
    START          →  'start'  (keyword reservada)
    TERMINAL_NAME  →  [A-Z][A-Z0-9_]*  ex: ID, NUMBER, PLUS
    NONTERM        →  [A-Z][a-zA-Z0-9]*  ex: Program, S, Expr
    STRING  →  '...'  terminal inline, ex: '0', '[', ','
    REGEX          →  /[^/]+/
    ARROW          →  -> ou →
    PIPE           →  |
    EQUALS         →  =
    COLON          →  :
    EPSILON        →  epsilon ou ε
    NEWLINE        →  uma ou mais quebras de linha (significativas para o parser)

Ignorados:
    espaços, tabs, comentários (# até fim da linha)
"""

import ply.lex as lex
import re

tokens = (
    'START',
    'TERMINAL_NAME',
    'NONTERM',
    'STRING',
    'REGEX',
    'ARROW',
    'PIPE',
    'EQUALS',
    'COLON',
    'EPSILON',
    'NEWLINE',
)

t_ignore = ' \t'


def t_ARROW(t):
    r'→|->'
    return t


def t_PIPE(t):
    r'\|'
    return t


def t_EQUALS(t):
    r'='
    return t


def t_COLON(t):
    r':'
    return t


def t_REGEX(t):
    r'/[^/]+/'
    t.value = t.value[1:-1]   # remove as barras delimitadoras
    return t


def t_STRING(t):
    r"""'[^']*'|\"[^\"]*\""""
    return t


def t_EPSILON(t):
    r'ε|epsilon'
    return t


def t_IDENTIFIER(t):
    r"[A-Za-z][A-Za-z0-9_]*'*"
    value = t.value
    base = value.rstrip("'")

    if base == 'start':
        t.type = 'START'
    elif re.fullmatch(r'[A-Z][A-Z0-9_]*', base):
        # letra única maiúscula → NONTERM (convencional em gramáticas: S, A, B)
        if len(base) == 1:
            t.type = 'NONTERM'
        else:
            t.type = 'TERMINAL_NAME'
    else:
        t.type = 'NONTERM'

    return t


def t_NEWLINE(t):
    r'\n+'
    t.lexer.lineno += len(t.value)
    return t


def t_COMMENT(t):
    r'\#[^\n]*'
    pass  # ignorar comentários


def t_error(t):
    print(f"[ERRO LÉXICO] Linha {t.lineno}: carácter inesperado '{t.value[0]}'")
    t.lexer.skip(1)


lexer = lex.lex()