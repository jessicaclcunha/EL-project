import re
from gp_analysis import build_parse_table

from gp_parser_rd import (
    _collect_terminals, _nt_func, _is_epsilon_seq,
    _is_inline, _inline_inner, _inline_ply_name,
)


def generate_table_parser(grammar, first, follow):
    nts      = grammar.get_nonterminals()
    start    = grammar.get_start()
    rules    = grammar.get_rules()
    patterns = grammar.get_token_patterns()

    table         = build_parse_table(grammar, first, follow)
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
    w('Parser Top-Down Dirigido por Tabela — gerado pelo Grammar Playground.')
    w('')
    w('  parsing_table        — tabela LL(1): parsing_table [NT][tipo] = [símbolos]')
    w('  stack          — lista de strings (topo = stack[-1])')
    w('  actual_tipo    — tipo do token actual')
    w('  actual_lex     — lexema do token actual')
    w('"""')
    w('')
    w('import sys')
    w('')

    w('# Árvore de derivação')
    w('')
    w('class TreeNode:')
    w('    def __init__(self, label, children=None, lexema=None):')
    w('        self.label    = label')
    w('        self.children = children or []')
    w('        self.lexema   = lexema')
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
    w('tokens = (')
    for nome in patterns:
        w(f"    '{nome}',")
    for nome_ply in inline_tokens:
        w(f"    '{nome_ply}',")
    w(')')
    w('')
    # tokens declarados como funções (mais longos primeiro)
    for nome, pat in sorted(patterns.items(), key=lambda x: -len(x[1])):
        w(f'def t_{nome}(t):')
        w(f'    r"{pat}"')
        w(f'    return t')
        w('')
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


    w('# Tabela LL(1) — parsing_table ')
    w('# parsing_table [NT][tipo] = lista de símbolos do lado direito ([] = ε)')
    w('')
    w('parsing_table  = {')

    by_nt = {}
    for (nt, terminal), seqs in table.items():
        if not seqs:
            continue
        seq  = seqs[0]
        tipo = _inline_inner(terminal) if _is_inline(terminal) else terminal
        by_nt.setdefault(nt, {})[tipo] = seq

    for nt in sorted(by_nt):
        w(f'    "{nt}": {{')
        for tipo in sorted(by_nt[nt]):
            seq = by_nt[nt][tipo]
            if _is_epsilon_seq(seq):
                rhs = []
            else:
                rhs = [
                    _inline_inner(s.get_value()) if _is_inline(s.get_value())
                    else s.get_value()
                    for s in seq.symbols
                ]
            rhs_comment = 'ε' if not rhs else ' '.join(rhs)
            w(f'        "{tipo}": {repr(rhs)},  # {nt} -> {rhs_comment}')
        w(f'    }},')

    w('}')
    w('')
    w(f'NONTERMINALS = {repr(sorted(nts))}')
    w(f'START = "{start}"')
    w('')

    w('# Estado global')
    w('')
    w('tokens     = []')
    w('actual_tipo = None')
    w('actual_lex  = None')
    w('')
    w('')
    w('def advance():')
    w('    global actual_tipo, actual_lex')
    w('    tokens.pop(0)')
    w('    actual_tipo, actual_lex = tokens[0]')
    w('')

    w('# parse(source) — algoritmo Top-Down dirigido por tabela')
    w('')
    w('')
    w('def parse(source):')
    w('    global tokens, actual_tipo, actual_lex')
    w('    tokens = tokenizer(source)')
    w('    actual_tipo, actual_lex = tokens[0]')
    w('')
    w('    # nós da árvore indexados por símbolo na stack')
    w('    raiz = TreeNode(START)')
    w('    # stack: lista de (símbolo: str, nó: TreeNode|None)')
    w('    stack = [("$", None), (START, raiz)]')
    w('')
    w('    while True:')
    w('        topo, topo_no = stack[-1]')
    w('')
    w('        # ACEITE')
    w('        if topo == "$" and actual_tipo == "$":')
    w('            return raiz')
    w('')
    w('        if topo == "$":')
    w('            raise SyntaxError(f"Tokens extra: \'{actual_tipo}\' (\'{actual_lex}\')")')
    w('')
    w('        # AVANÇA — topo é terminal')
    w('        if topo not in NONTERMINALS:')
    w('            if actual_tipo == topo:')
    w('                stack.pop()')
    w('                if topo_no is not None:')
    w('                    topo_no.lexema = actual_lex')
    w('                advance()')
    w('            else:')
    w('                raise SyntaxError(')
    w('                    f"Esperado \'{topo}\', encontrado \'{actual_tipo}\' (\'{actual_lex}\')"')
    w('                )')
    w('            continue')
    w('')
    w('        # PRODUÇÃO — consultar parsing_table ')
    w('        entradas = parsing_table .get(topo, {})')
    w('        rhs = entradas.get(actual_tipo)')
    w('        if rhs is None:')
    w('            raise SyntaxError(')
    w('                f"Erro ao expandir \'{topo}\': \'{actual_tipo}\' inesperado. "')
    w('                f"Esperado um de: {list(entradas.keys())}"')
    w('            )')
    w('')
    w('        stack.pop()')
    w('        if not rhs:')
    w('            if topo_no is not None:')
    w('                topo_no.children.append(TreeNode("ε"))')
    w('        else:')
    w('            filhos = [TreeNode(sym) for sym in rhs]')
    w('            if topo_no is not None:')
    w('                topo_no.children.extend(filhos)')
    w('            for sym, filho in reversed(list(zip(rhs, filhos))):')
    w('                stack.append((sym, filho))')
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



class Lexer:
    """Tokenizador parametrizado pelos padrões da gramática."""

    def __init__(self, source, token_patterns):
        self.tokens = []
        pos = 0
        line = 1
        token_spec = list(token_patterns.items())
        while pos < len(source):
            if re.match(r'[ \t]', source[pos]):
                pos += 1; continue
            if source[pos] == '\n':
                line += 1; pos += 1; continue
            matched = False
            for name, pat in token_spec:
                m = re.match(pat, source[pos:])
                if m:
                    self.tokens.append((name, m.group()))
                    pos += m.end(); matched = True; break
            if not matched:
                raise SyntaxError(f"Linha {line}: carácter inesperado {source[pos]!r}")
        self.tokens.append(('$', '$'))


class _TreeNode:
    """TreeNode interno usado pelo TableParser."""
    def __init__(self, label, children=None, lexema=None):
        self.label    = label
        self.children = children or []
        self.lexema   = lexema

    def print_tree(self, prefix='', last=True):
        branch = '└── ' if last else '├── '
        show   = f'{self.label}: {self.lexema!r}' if self.lexema is not None else self.label
        print(prefix + branch + show)
        ext = '    ' if last else '│   '
        for i, child in enumerate(self.children):
            child.print_tree(prefix + ext, last=(i == len(self.children) - 1))


class TableParser:
    """
    Parser LL(1)
    """

    def __init__(self, grammar, table, source):
        self.nts   = grammar.get_nonterminals()
        self.start = grammar.get_start()
        self.table = table
        lex        = Lexer(source, grammar.get_token_patterns())
        self.tokens = lex.tokens
        self.pos    = 0
        self.steps  = []

    def _current(self):
        return self.tokens[self.pos]

    def advance(self):
        self.pos += 1

    def _is_eps(self, seq):
        return not seq.symbols or (
            len(seq.symbols) == 1 and seq.symbols[0].get_is_epsilon()
        )

    def _match_terminal(self, topo, la_tipo):
        if topo.startswith(("'", '"')):
            return la_tipo == topo[1:-1]
        return la_tipo == topo

    def parse(self):
        raiz  = _TreeNode(self.start)
        stack = [('$', None), (self.start, raiz)]
        step  = 0

        while True:
            topo, topo_no = stack[-1]
            la_tipo, la_lex = self._current()

            step += 1
            self.steps.append({
                'step':   step,
                'stack':  [s for s, _ in reversed(stack)],
                'input':  la_lex or '$',
                'action': '',
            })

            # ACEITE
            if topo == '$' and la_tipo == '$':
                self.steps[-1]['action'] = 'ACEITE'
                return raiz

            if topo == '$':
                raise SyntaxError(f"Tokens extra: {la_tipo!r} ({la_lex!r})")

            # AVANÇA — topo é terminal
            if topo not in self.nts:
                if self._match_terminal(topo, la_tipo):
                    stack.pop()
                    if topo_no is not None:
                        topo_no.lexema = la_lex
                    self.steps[-1]['action'] = f'avança: {la_tipo!r} = {la_lex!r}'
                    self.advance()
                else:
                    raise SyntaxError(
                        f"Esperado {topo!r}, encontrado {la_tipo!r} ({la_lex!r})"
                    )
                continue

            # PRODUÇÃO — consultar tabela
            cell = self.table.get((topo, la_tipo), [])
            if not cell:
                for q in ("'", '"'):
                    cell = self.table.get((topo, f"{q}{la_tipo}{q}"), [])
                    if cell:
                        break

            if not cell:
                esperados = {t for (n, t) in self.table if n == topo}
                raise SyntaxError(
                    f"Símbolo {la_tipo!r} inesperado ao expandir {topo!r}. "
                    f"Esperado um de: {sorted(esperados)}"
                )

            seq = cell[0]
            self.steps[-1]['action'] = f'produção: {topo} -> {repr(seq)}'

            stack.pop()
            if self._is_eps(seq):
                if topo_no is not None:
                    topo_no.children.append(_TreeNode('ε'))
            else:
                syms  = seq.symbols
                filhos = [_TreeNode(
                    s.get_value()[1:-1] if s.get_value().startswith(("'", '"')) else s.get_value()
                ) for s in syms]
                if topo_no is not None:
                    topo_no.children.extend(filhos)
                for sym, filho in reversed(list(zip(syms, filhos))):
                    val = sym.get_value()
                    key = val[1:-1] if val.startswith(("'", '"')) else val
                    stack.append((key, filho))

    def print_steps(self):
        for s in self.steps:
            stack_str = ' '.join(s['stack'])
            print(f"  {s['step']:3}  stack: {stack_str:<30}  input: {s['input']:<10}  {s['action']}")