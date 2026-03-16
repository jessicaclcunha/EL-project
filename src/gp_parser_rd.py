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

def generate_rd_parser(grammar, first, follow):
    nts      = grammar.get_nonterminals()
    start    = grammar.get_start()
    rules    = grammar.get_rules()
    patterns = grammar.get_token_patterns()
    all_terminals = _collect_terminals(rules, patterns)

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
    w('import re')
    w('import sys')
    w('')

    w('# -----------------------------------------------------------------')
    w('# Árvore de derivação')
    w('# -----------------------------------------------------------------')
    w('')
    w('class TreeNode:')
    w('    def __init__(self, label, children=None, lexema=None):')
    w('        self.label    = label       # nome do NT ou tipo do terminal')
    w('        self.children = children or []')
    w('        self.lexema   = lexema      # preenchido nos nós folha (terminais)')
    w('')
    w('    def print_tree(self, prefix="", last=True):')
    w('        branch = "└── " if last else "├── "')
    w('        show   = f"{self.label}: {self.lexema!r}" if self.lexema is not None else self.label')
    w('        print(prefix + branch + show)')
    w('        ext = "    " if last else "│   "')
    w('        for i, child in enumerate(self.children):')
    w('            child.print_tree(prefix + ext, last=(i == len(self.children) - 1))')
    w('')

    w('# -----------------------------------------------------------------')
    w('# Tokenizador — devolve lista de (tipo, lexema)')
    w('# -----------------------------------------------------------------')
    w('')
    w('def tokenizer(source):')
    w('    tokens = []')
    w('    while source:')

    # terminais inline primeiro (mais longos primeiro), depois declarados
    _inline = {t: t[1:-1] for t in all_terminals if _is_inline(t)}
    branches = (
        [(re.escape(inner), inner)          # tipo = o próprio carácter/símbolo
         for _, inner in sorted(_inline.items(), key=lambda x: -len(x[1]))]
        + [(pat, nm) for nm, pat in patterns.items()]   # tipo = nome declarado
    )
    for idx, (pat, tipo) in enumerate(branches):
        kw = 'if' if idx == 0 else 'elif'
        w(f'        {kw} m := re.match(r"{pat}", source):')
        w(f'            tokens.append(({tipo!r}, m.group()))')
        w(f'            source = source[m.end():]')

    w('        elif source[0] in " \\n\\t":')
    w('            source = source[1:]')
    w('        else:')
    w('            raise SyntaxError(f"Símbolo inválido: {source[0]!r}")')
    w('    tokens.append(("$", "$"))')
    w('    return tokens')
    w('')

    w('')
    w('# -----------------------------------------------------------------')
    w('# Estado global')
    w('# -----------------------------------------------------------------')
    w('')
    w('_tokens     = []')
    w('actual_tipo = None   # tipo do token actual')
    w('actual_lex  = None   # lexema do token actual')
    w('')
    w('')
    w('def _advance():')
    w('    global actual_tipo, actual_lex')
    w('    _tokens.pop(0)')
    w('    actual_tipo, actual_lex = _tokens[0]')
    w('')
    w('')
    w('def rec(t):')
    w('    """Consome o terminal de tipo t. Devolve o lexema. ABORTA se não coincidir."""')
    w('    if actual_tipo == t:')
    w('        lex = actual_lex')
    w('        _advance()')
    w('        return lex')
    w('    raise SyntaxError(f"Esperado {t!r}, encontrado {actual_tipo!r} ({actual_lex!r})")')
    w('')

    w('')
    w('# -----------------------------------------------------------------')
    w('# Funções de reconhecimento — uma por não-terminal')
    w('# -----------------------------------------------------------------')

    for rule in rules:
        nt   = rule.get_head_name()
        seqs = rule.altlist.sequences
        fn   = _nt_func(nt)

        w('')
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

        for seq in seqs:
            if _is_epsilon_seq(seq):
                eps_seq = seq
                continue

            la = sorted(_lookahead(seq, nt, first, follow, nts))
            if not la:
                continue

            # lookahead usa o TIPO do token:
            #   inline '+' → tipo é '+'
            #   declarado ID → tipo é 'ID'
            def _tipo(t):
                return _inline_inner(t) if _is_inline(t) else t

            cond = ' or '.join(f'actual_tipo == {_tipo(t)!r}' for t in la)
            kw = 'if' if first_branch else 'elif'
            first_branch = False
            w(f'    {kw} {cond}:')
            w(f'        children = []')

            for sym in seq.symbols:
                if sym.get_is_terminal():
                    val  = sym.get_value()
                    tipo = _inline_inner(val) if _is_inline(val) else val
                    w(f'        children.append(TreeNode({tipo!r}, lexema=rec({tipo!r})))')
                else:
                    w(f'        children.append(parse_{_nt_func(sym.get_value())}())')

            w(f'        return TreeNode({nt!r}, children=children)')

        # ramo ε / erro
        if eps_seq is not None:
            if first_branch:
                w(f'    return TreeNode({nt!r}, children=[TreeNode("ε")])')
            else:
                w(f'    else:')
                w(f'        return TreeNode({nt!r}, children=[TreeNode("ε")])')
        else:
            if first_branch:
                w(f'    raise SyntaxError(f"Erro em {nt}: token inesperado {{actual_tipo!r}}")')
            else:
                w(f'    else:')
                w(f'        raise SyntaxError(f"Erro em {nt}: token inesperado {{actual_tipo!r}}")')


    w('')
    w('')
    w('def parse(source):')
    w('    global _tokens, actual_tipo, actual_lex')
    w('    _tokens = tokenizer(source)')
    w('    actual_tipo, actual_lex = _tokens[0]')
    w(f'    tree = parse_{_nt_func(start)}()')
    w('    if actual_tipo != "$":')
    w('        raise SyntaxError(f"Tokens extra após o fim: {actual_tipo!r}")')
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