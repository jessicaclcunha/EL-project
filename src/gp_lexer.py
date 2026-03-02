import ply.lex as lex
import re

tokens = (
    'START',
    'TERMINAL',
    'NON_TERMINAL',
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


def t_TERMINAL_STRING(t):
    r"""'[^']*'|"[^"]*\""""
    t.type = 'TERMINAL'
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
    # Classificação TERMINAL vs NON_TERMINAL
    elif re.fullmatch(r'[A-Z][A-Z0-9_]*', base):
        if len(base) == 1:
            # Letra maiúscula isolada → NON_TERMINAL (convencional: S, A, B)
            t.type = 'NON_TERMINAL'
        else:
            # Tudo maiúsculas com 2+ chars → TERMINAL (ID, NUMBER, PLUS)
            t.type = 'TERMINAL'
    else:
        # PascalCase, camelCase, etc. → NON_TERMINAL
        t.type = 'NON_TERMINAL'

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