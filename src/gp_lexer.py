"""
    START_KW      →  'start:'
    ARROW         →  '→' ou '->'
    PIPE          →  '|'
    EPSILON       →  'ε'
    IDENTIFIER    →  [A-Za-z][A-Za-z0-9_']*
    QUOTED_STRING →  '...'
    NEWLINE       →  uma ou mais \n
"""

import ply.lex as lex


tokens = (
    'START_KW',
    'ARROW',
    'PIPE',
    'EPSILON',
    'IDENTIFIER',
    'QUOTED_STRING',
    'NEWLINE',
)


t_ignore = ' \t'   # espaços e tabs ignorados


def t_START_KW(t):
    r'start:'
    return t


def t_ARROW(t):
    r'→|->'
    return t


def t_EPSILON(t):
    r'ε'
    return t


def t_PIPE(t):
    r'\|'
    return t


def t_QUOTED_STRING(t):
    r"'[^']*'"
    t.value = t.value[1:-1]   # remove as aspas simples
    return t


def t_IDENTIFIER(t):
    r"[A-Za-z][A-Za-z0-9_']*"
    return t


def t_NEWLINE(t):
    r'\n+'
    t.lexer.lineno += len(t.value)
    return t


def t_COMMENT(t):
    r'\#[^\n]*'
    pass   # comentários descartados


def t_error(t):
    print(f"[ERRO LÉXICO] Linha {t.lineno}: carácter inesperado '{t.value[0]}'")
    t.lexer.skip(1)


lexer = lex.lex()