import re

from gp_analysis import first_of_seq
from gp_helpers  import strip_quotes, is_epsilon_seq



class SimpleLexer:
    """Tokenizador inline — recebe {tipo: regex} e devolve lista de (tipo, lexema)."""

    def __init__(self, source: str, token_patterns: dict):
        self.tokens: list[tuple[str, str]] = []
        pos  = 0
        line = 1
        spec = list(token_patterns.items())

        while pos < len(source):
            ch = source[pos]
            if ch in (' ', '\t'):
                pos += 1; continue
            if ch == '\n':
                line += 1; pos += 1; continue

            matched = False
            for name, pat in spec:
                m = re.match(pat, source[pos:])
                if m:
                    self.tokens.append((name, m.group()))
                    pos += m.end()
                    matched = True
                    break

            if not matched:
                raise SyntaxError(
                    f"Linha {line}: carácter inesperado {source[pos]!r}"
                )

        self.tokens.append(('$', '$'))


class TreeNode:
    def __init__(self, label: str, children=None, lexema=None):
        self.label    = label
        self.children = children or []
        self.lexema   = lexema


def parse_with_rd(grammar, first, follow, phrase: str, patterns: dict):
    nts   = grammar.get_nonterminals()
    start = grammar.get_start()

    # (nt, seq) para todas as alternativas de todas as regras
    flat_rules = [
        (rule.get_head_name(), seq)
        for rule in grammar.get_rules()
        for seq in rule.altlist.sequences
    ]

    tokens = SimpleLexer(phrase, patterns).tokens
    pos    = [0]
    steps  = []

    def current():
        return tokens[pos[0]] if pos[0] < len(tokens) else ('$', '$')

    def advance():
        if pos[0] < len(tokens) - 1:
            pos[0] += 1

    def rec(t: str) -> TreeNode:
        """Consome o terminal t (pode vir com aspas da gramática)."""
        t_norm         = strip_quotes(t)
        tipo, lex_val  = current()
        if tipo == t_norm:
            steps.append({
                'step':   len(steps) + 1,
                'stack':  [],
                'input':  lex_val,
                'action': f'avança: {t_norm} = {lex_val!r}',
            })
            node = TreeNode(t_norm, lexema=lex_val)
            advance()
            return node
        raise SyntaxError(f"Esperado {t_norm!r}, encontrado {tipo!r} ({lex_val!r})")

    def parse_nt(nt: str) -> TreeNode:
        tipo, lex_val = current()
        for nt_name, seq in flat_rules:
            if nt_name != nt:
                continue
            sf       = first_of_seq(seq.symbols, first, nts)
            nullable = 'ε' in sf
            la       = (sf - {'ε'}) | (follow.get(nt, set()) if nullable else set())
            la_norm  = {strip_quotes(x) for x in la}

            if tipo not in la_norm:
                continue

            steps.append({
                'step':   len(steps) + 1,
                'stack':  [],
                'input':  lex_val,
                'action': f'produção: {nt} → {repr(seq)}',
            })

            if is_epsilon_seq(seq):
                return TreeNode(nt, children=[TreeNode('ε')])

            children = []
            for sym in seq.symbols:
                if sym.get_is_terminal():
                    children.append(rec(sym.get_value()))
                else:
                    children.append(parse_nt(sym.get_value()))
            return TreeNode(nt, children=children)

        raise SyntaxError(f"Erro ao expandir {nt!r}: token {tipo!r} inesperado")

    tree = parse_nt(start)
    tipo, _ = current()
    if tipo != '$':
        raise SyntaxError(f"Tokens extra após o fim: {tipo!r}")

    steps.append({
        'step':   len(steps) + 1,
        'stack':  [],
        'input':  '$',
        'action': 'ACEITE',
    })
    return tree, steps