import re
from gp_analysis import first_of_seq

def _collect_terminals(rules, patterns):
    result = list(patterns.keys())
    seen = set(result)
    for rule in rules:
        for seq in rule.altlist.sequences:
            for sym in seq.symbols:
                if sym.get_is_terminal():
                    v = sym.get_value()
                    if v not in seen:
                        result.append(v)
                        seen.add(v)
    return result


def _nt_func(nt):
    return re.sub(r'[^A-Za-z0-9_]', '_', nt.replace("'", "_prime"))


def _is_epsilon_seq(seq):
    return not seq.symbols or (
        len(seq.symbols) == 1 and seq.symbols[0].get_is_epsilon()
    )


def _lookahead(seq, nt, first, follow, nts):
    """
    lookahead(A -> rhs):
      se rhs é anulável  ->  first(rhs) - {e}  U  follow(A)
      caso contrário     ->  first(rhs) - {e}
    """
    sf = first_of_seq(seq.symbols, first, nts)
    if _is_epsilon_seq(seq) or 'ε' in sf:
        return (sf - {'ε'}) | follow.get(nt, set())
    return sf - {'ε'}


def _is_inline(val):
    """Terminal inline, ex. '+', '(' — delimitado por aspas na gramática."""
    return val.startswith(("'", '"'))


def _inline_inner(val):
    return val[1:-1]


def _inline_ply_name(inner):
    """Converte o símbolo inline num nome PLY válido. Ex: '[' -> 'LBRACK', ':=' -> 'COLON_EQ'"""
    nome = re.sub(r'[^A-Za-z0-9]', '_', inner).strip('_').upper()
    if not nome:
        nome = 'SYM_' + str(ord(inner[0]))
    return nome


def generate_rd_parser(grammar, first, follow):
    nts      = grammar.get_nonterminals()
    start    = grammar.get_start()
    rules    = grammar.get_rules()
    patterns = grammar.get_token_patterns()
    all_terminals = _collect_terminals(rules, patterns)

    # tokens inline: '[' -> 'LBRACK', ':=' -> 'COLON_EQ', etc.
    inline_tokens = {}
    for t in all_terminals:
        if _is_inline(t):
            inner = _inline_inner(t)
            inline_tokens[_inline_ply_name(inner)] = inner

    lines = []
    w = lines.append

    w('"""')
    w('Parser Recursivo Descendente — gerado pelo Grammar Playground.')
    w('')
    w('  actual_tipo  — tipo do token actual (string)')
    w('  actual_lex   — lexema do token actual (string)')
    w('  rec(t)       — consome o terminal de tipo t; devolve o lexema')
    w('  parse_X()    — reconhece o NT X; devolve TreeNode')
    w('"""')
    w('')
    w('import sys')
    w('')

    w('# Árvore de derivação')
    w('')
    w('class TreeNode:')
    w('    def __init__(self, label, children=None, lexema=None):')
    w('        self.label    = label       # nome do NT ou tipo do terminal')
    w('        self.children = children or []')
    w('        self.lexema   = lexema      # preenchido nos nós folha (terminais)')
    w('')
    w('    def print_tree(self, prefix="", last=True):')
    w('        branch = "└── " if last else "├── "')
    w('        show   = f"{self.label}: {self.lexema}" if self.lexema is not None else self.label')
    w('        print(prefix + branch + show)')
    w('        ext = "    " if last else "│   "')
    w('        for i, child in enumerate(self.children):')
    w('            child.print_tree(prefix + ext, last=(i == len(self.children) - 1))')
    w('')

    w('# LEXER')
    w('')
    w('import ply.lex as lex')
    w('')
    w('ply_tokens = (')
    for nome in patterns:
        w(f"    '{nome}',")
    for nome_ply in inline_tokens:
        w(f"    '{nome_ply}',")
    w(')')
    w('tokens = ply_tokens')
    w('')
    # tokens declarados como funções (mais longos primeiro)
    for nome, pat in sorted(patterns.items(), key=lambda x: -len(x[1])):
        w(f'def t_{nome}(t):')
        w(f'    r"{pat}"')
        w(f'    return t')
        w('')
    # tokens inline como strings (mais longos primeiro)
    for nome_ply, inner in sorted(inline_tokens.items(), key=lambda x: -len(x[1])):
        w(f't_{nome_ply} = r"{re.escape(inner)}"')
    w('')
    w('t_ignore = " \\t\\n"')
    w('')
    w('def t_error(t):')
    w('    raise SyntaxError(f"Símbolo inválido: {t.value[0]}")')
    w('')
    w('lexer = lex.lex()')
    w('')
    # mapa nome PLY -> símbolo original, para devolver '[' em vez de 'LBRACK'
    w('inline_map = {')
    for nome_ply, inner in inline_tokens.items():
        w(f'    "{nome_ply}": "{inner}",')
    w('}')
    w('')
    w('def tokenizer(source):')
    w('    lexer.input(source)')
    w('    result = []')
    w('    for token in lexer:')
    w('        tipo = inline_map.get(token.type, token.type)')
    w('        result.append((tipo, token.value))')
    w('    result.append(("$", "$"))')
    w('    return result')
    w('')

    w('')
    w('')
    w('token_stream = [] ')
    w('token_pos    = 0    # índice do token actual')
    w('actual_tipo = None   # tipo do token actual')
    w('actual_lex  = None   # lexema do token actual')
    w('')
    w('')
    w('def advance():')
    w('    global token_pos, actual_tipo, actual_lex')
    w('    if token_pos < len(token_stream) - 1:')
    w('        token_pos += 1')
    w('    actual_tipo, actual_lex = token_stream[token_pos]')
    w('')
    w('')
    w('def rec(t):')
    w('    """Consome o terminal de tipo t. Devolve o lexema. ABORTA se não coincidir."""')
    w('    if actual_tipo == t:')
    w('        lex_val = actual_lex')
    w('        advance()')
    w('        return lex_val')
    w("    raise SyntaxError(f\"Esperado '{t}', encontrado '{actual_tipo}' ('{actual_lex}')\")")
    w('')

    w('')
    w('# Funções de reconhecimento — uma por não-terminal')

    for rule in rules:
        nt   = rule.get_head_name()
        seqs = rule.altlist.sequences
        fn   = _nt_func(nt)

        w('')
        rhs_str = ' | '.join(
            'ε' if _is_epsilon_seq(s)
            else ' '.join(x.get_value() for x in s.symbols)
            for s in seqs
        )
        w(f'def parse_{fn}():')
        w(f'    # {nt} -> {rhs_str}')

        first_branch = True
        eps_seq      = None
        follow_tokens = sorted(follow.get(nt, set()))

        for seq in seqs:
            if _is_epsilon_seq(seq):
                eps_seq = seq
                continue

            la = sorted(_lookahead(seq, nt, first, follow, nts))
            if not la:
                continue

            def _tipo(t):
                return _inline_inner(t) if _is_inline(t) else t

            cond = ' or '.join(f'actual_tipo == "{_tipo(t)}"' for t in la)
            kw = 'if' if first_branch else 'elif'
            first_branch = False
            w(f'    {kw} {cond}:')
            w(f'        children = []')

            for sym in seq.symbols:
                if sym.get_is_terminal():
                    val  = sym.get_value()
                    tipo = _inline_inner(val) if _is_inline(val) else val
                    w(f'        children.append(TreeNode("{tipo}", lexema=rec("{tipo}")))')
                else:
                    w(f'        children.append(parse_{_nt_func(sym.get_value())}())')

            w(f'        return TreeNode("{nt}", children=children)')

        if eps_seq is not None:
            follow_cond = ' or '.join(
                f'actual_tipo == "{_tipo(t)}"' for t in follow_tokens
            ) if follow_tokens else 'True'

            if first_branch:
                w(f'    if {follow_cond}:')
                w(f'        return TreeNode("{nt}", children=[TreeNode("ε")])')
                w(f'    raise SyntaxError(f"Erro em {nt}: token inesperado {{actual_tipo}}")')
            else:
                w(f'    elif {follow_cond}:')
                w(f'        return TreeNode("{nt}", children=[TreeNode("ε")])')
                w(f'    else:')
                w(f'        raise SyntaxError(f"Erro em {nt}: token inesperado {{actual_tipo}} (esperado FOLLOW={{{repr(follow_tokens)}}})")')
        else:
            if first_branch:
                w(f'    raise SyntaxError(f"Erro em {nt}: token inesperado {{actual_tipo}}")')
            else:
                w(f'    else:')
                w(f'        raise SyntaxError(f"Erro em {nt}: token inesperado {{actual_tipo}}")')

    w('')
    w('')
    w('def parse(source):')
    w('    global token_stream, token_pos, actual_tipo, actual_lex')
    w('    token_stream = tokenizer(source)')
    w('    token_pos    = 0')
    w('    actual_tipo, actual_lex = token_stream[0]')
    w(f'    tree = parse_{_nt_func(start)}()')
    w('    if actual_tipo != "$":')
    w('        raise SyntaxError(f"Tokens extra após o fim: {actual_tipo}")')
    w('    return tree')
    w('')
    w('')
    w('def main():')
    w('    if len(sys.argv) > 1:')
    w('        with open(sys.argv[1], encoding="utf-8") as f:')
    w('            source = f.read()')
    w('    else:')
    w('        source = input("? ")')
    w('    try:')
    w('        tree = parse(source)')
    w('        tree.print_tree()')
    w('    except (ValueError, SyntaxError) as e:')
    w('        print(f"Erro: {e}", file=sys.stderr)')
    w('')
    w('')
    w('if __name__ == "__main__":')
    w('    main()')

    return '\n'.join(lines)