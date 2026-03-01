"""
Léxico da linguagem de especificação de gramáticas (Grammar Playground)

Tokens reconhecidos:
    START          →  'start'  (keyword reservada)
    TERMINAL_NAME  →  [A-Z][A-Z0-9_]*  (2+ chars, ex: ID, NUMBER, PLUS)
    NONTERM        →  PascalCase ou maiúscula isolada (ex: Program, S, Expr)
    STRING         →  '...' ou "..."  terminal inline
    REGEX          →  /[^/]+/
    ARROW          →  -> ou →
    PIPE           →  |
    EQUALS         →  =
    COLON          →  :
    EPSILON        →  epsilon ou ε  (keyword reservada)
    NEWLINE        →  uma ou mais quebras de linha (significativas para o parser)

Ignorados:
    espaços, tabs, comentários (# até fim da linha)

Convenções de nomes:
    - Não-terminais: PascalCase ou letra maiúscula isolada (Program, S, A)
    - Terminais nomeados: TUDO_MAIUSCULAS com 2+ chars (ID, NUMBER, PLUS)
    - 'start' e 'epsilon' são palavras reservadas
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
    r"""'[^']*'|"[^"]*\""""
    return t


# Carácter unicode ε tratado à parte (não é apanhado pelo regex de t_IDENTIFIER)
def t_EPSILON_UNICODE(t):
    r'ε'
    t.type = 'EPSILON'
    return t


def t_IDENTIFIER(t):
    r"[A-Za-z][A-Za-z0-9_]*'*"
    value = t.value
    base = value.rstrip("'")

    # Palavras reservadas
    if base == 'start':
        t.type = 'START'
    elif base == 'epsilon':
        t.type = 'EPSILON'
    # Classificação TERMINAL_NAME vs NONTERM
    elif re.fullmatch(r'[A-Z][A-Z0-9_]*', base):
        if len(base) == 1:
            # Letra maiúscula isolada → NONTERM (convencional: S, A, B)
            t.type = 'NONTERM'
        else:
            # Tudo maiúsculas com 2+ chars → TERMINAL_NAME (ID, NUMBER, PLUS)
            t.type = 'TERMINAL_NAME'
    else:
        # PascalCase, camelCase, etc. → NONTERM
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