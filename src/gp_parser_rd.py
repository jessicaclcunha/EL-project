import re
from gp_analysis import first_of_seq


def generate_rd_parser(grammar, first, follow):
    nts      = grammar.get_nonterminals()
    start    = grammar.get_start()
    rules    = grammar.get_rules()
    patterns = grammar.get_token_patterns()

    all_terminals = _collect_terminals(rules, patterns)

    lines = []
    w = lines.append

    # Cabeçalho
    w('"""')
    w('Parser recursivo descendente — gerado automaticamente pelo Grammar Playground.')
    w('"""')
    w('')
    w('from enum import Enum')
    w('import re')
    w('import sys')
    w('')

    w('# Tokens')
    w('')
    w('class Tokens(Enum):')
    for i, name in enumerate(all_terminals):
        enum_name = _enum_name(name)
        w(f'    {enum_name} = {i}')
    w(f'    EOF = -1')
    w('')

    w('# Árvore de derivação')
    w('')
    w('class TreeNode:')
    w('    def __init__(self, label, children=None, token_value=None):')
    w('        self.label = label')
    w('        self.children = children or []')
    w('        self.token_value = token_value')
    w('')
    w('    def print_tree(self, prefix="", is_last=True):')
    w('        connector = "└── " if is_last else "├── "')
    w('        display = (f"{self.label}: {self.token_value!r}"')
    w('                   if self.token_value is not None else self.label)')
    w('        print(prefix + connector + display)')
    w('        ext = "    " if is_last else "│   "')
    w('        for i, child in enumerate(self.children):')
    w('            child.print_tree(prefix + ext,')
    w('                             is_last=(i == len(self.children) - 1))')
    w('')


    w('# Tokenizador')
    w('')
    w('def tokenizer(source):')
    w('    result = []')
    w('    while len(source) > 0:')

    _inline = {t: t[1:-1] for t in all_terminals if t.startswith(("'", '"'))}
    _branches = (
        [(re.escape(inner), _enum_name(lit))
         for lit, inner in sorted(_inline.items(), key=lambda x: -len(x[1]))]
        + [(pat, _enum_name(nm)) for nm, pat in patterns.items()]
    )
    for _idx, (_pat, _enum_n) in enumerate(_branches):
        _kw = 'if' if _idx == 0 else 'elif'
        w(f'        {_kw} m := re.match(r"{_pat}", source):')
        w(f'            result.append((Tokens.{_enum_n}, m.group()))')
        w(f'            source = source[m.end():]')

    w('        elif source[0] in " \\n\\t":')
    w('            source = source[1:]')
    w('        else:')
    w('            raise ValueError(f"Carácter inválido: {source[0]!r}")')
    w('    return result + [(Tokens.EOF, None)]')
    w('')


    w('')
    w('tokens = None')
    w('')
    w('')
    w('def current_token():')
    w('    global tokens')
    w('    return tokens[0]')
    w('')
    w('')
    w('def next_token():')
    w('    global tokens')
    w('    tokens.pop(0)')
    w('')


    w('')
    w('# Funções de reconhecimento')

    for rule in rules:
        nt      = rule.get_head_name()
        seqs    = rule.altlist.sequences
        fn      = _nt_func(nt)

        w('')
        w('')
        alts_str = ' | '.join(repr(s) for s in seqs)
        w(f'def parse_{fn}():')
        w(f'    """Reconhece {nt} -> {alts_str}"""')

        seq_firsts   = [first_of_seq(seq.symbols, first, nts) for seq in seqs]
        first_branch = True
        epsilon_idx  = None

        for i, (seq, sf) in enumerate(zip(seqs, seq_firsts)):
            is_eps = (
                (len(seq.symbols) == 1 and seq.symbols[0].get_is_epsilon())
                or not seq.symbols
            )
            if is_eps or sf == {'ε'}:
                epsilon_idx = i
                continue

            terms = sorted(sf - {'ε'})
            if not terms:
                continue

            # Gerar case do match — múltiplos tokens com '|'
            if first_branch:
                w(f'    match current_token():')
                first_branch = False

            # Python match/case: vários padrões no mesmo case com '|'
            case_patterns = ' | '.join(
                f'(Tokens.{_enum_name(t)}, _)' for t in terms
            )
            w(f'        case {case_patterns}:')
            w(f'            # {nt} -> {repr(seq)}')
            _emit_seq(w, seq, nt, nts)

        # Alternativa epsilon / anulável  →  case _:
        if epsilon_idx is not None:
            fol_str = ', '.join(sorted(follow.get(nt, set())))
            if first_branch:
                # Só existe epsilon — nem precisamos de match
                w(f'    # {nt} -> ε  [FOLLOW: {{{fol_str}}}]')
                w(f'    return TreeNode({nt!r}, children=[TreeNode("ε")])')
            else:
                w(f'        case _:')
                w(f'            # {nt} -> ε  [FOLLOW: {{{fol_str}}}]')
                w(f'            return TreeNode({nt!r}, children=[TreeNode("ε")])')
        else:
            if not first_branch:
                w(f'        case err:')
                w(f'            raise ValueError(')
                w(f'                f"Estava à espera de {nt}, mas recebi {{err}}"')
                w(f'            )')
            else:
                w(f'    raise ValueError(f"Token inesperado ao expandir {nt}: {{current_token()}}")')


    w('')
    w('')
    w('def parse(tk):')
    w('    global tokens')
    w('    tokens = tk')
    w(f'    result = parse_{_nt_func(start)}()')
    w('    if current_token()[0] != Tokens.EOF:')
    w('        raise ValueError(f"Tokens extra após o fim: {current_token()}")')
    w('    return result')
    w('')


    w('')
    w('def main():')
    w('    if len(sys.argv) > 1:')
    w('        with open(sys.argv[1], encoding="utf-8") as f:')
    w('            source = f.read()')
    w('    else:')
    w('        source = input("? ")')
    w('    try:')
    w('        tk = tokenizer(source)')
    w('        tree = parse(tk)')
    w('        tree.print_tree()')
    w('    except (ValueError, SyntaxError) as e:')
    w('        print(f"Erro: {e}", file=sys.stderr)')
    w('')
    w('')
    w('if __name__ == "__main__":')
    w('    main()')
    w('')

    return '\n'.join(lines)




def _collect_terminals(rules, patterns):
    """Recolhe todos os terminais: declarados + inline."""
    result = list(patterns.keys())  # declarados com regex
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


def _enum_name(terminal):
    """
    Converte um terminal para nome de membro do Enum.
    'ID' → ID,  '+'  → PLUS,  ':=' → ASSIGN_EQ, etc.
    Para inline strings: strip aspas, escapar caracteres especiais.
    """
    if terminal.startswith(("'", '"')):
        inner = terminal[1:-1]
        # Mapeamentos comuns
        _MAP = {
            '+': 'PLUS', '-': 'MINUS', '*': 'TIMES', '/': 'DIVIDE',
            '(': 'LPAREN', ')': 'RPAREN', '[': 'LBRACKET', ']': 'RBRACKET',
            '{': 'LBRACE', '}': 'RBRACE', ';': 'SEMI', ',': 'COMMA',
            '.': 'DOT', ':': 'COLON', '=': 'EQ', '!': 'BANG',
            '<': 'LT', '>': 'GT', ':=': 'ASSIGN', '==': 'EQEQ',
            '!=': 'NEQ', '<=': 'LEQ', '>=': 'GEQ', '->': 'ARROW',
            '|': 'PIPE', '&': 'AMP', '%': 'PERCENT', '^': 'CARET',
        }
        if inner in _MAP:
            return _MAP[inner]
        # Fallback: usar repr escapado
        name = re.sub(r'[^A-Za-z0-9]', '_', inner).upper()
        return name or 'TOK'
    else:
        return terminal.upper()


def _nt_func(nt):
    """Converte nome do NT para sufixo de função.
    Ex: Expr' → Expr_prime,  StmtList → StmtList"""
    name = nt.replace("'", "_prime")
    return re.sub(r'[^A-Za-z0-9_]', '_', name)


def _emit_seq(w, seq, nt, nts):
    """
    Emite o corpo de uma alternativa dentro de um `case`:
      - terminal → next_token(); children.append(TreeNode(...))
      - NT       → children.append(parse_X())
      - epsilon  → children.append(TreeNode('ε'))
    """
    w(f'            children = []')
    for sym in seq.symbols:
        if sym.get_is_epsilon():
            w(f'            children.append(TreeNode("ε"))')
        elif sym.get_is_terminal():
            val = sym.get_value()
            enum_n = _enum_name(val)
            w(f'            _, _v = current_token()')
            w(f'            next_token()')
            w(f'            children.append(TreeNode({val!r}, token_value=_v))')
        else:
            fn = _nt_func(sym.get_value())
            w(f'            children.append(parse_{fn}())')
    w(f'            return TreeNode({nt!r}, children=children)')