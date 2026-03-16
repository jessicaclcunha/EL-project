import re
from gp_analysis import build_parse_table

from gp_parser_rd import (
    _collect_terminals, _nt_func, _is_epsilon_seq,
    _is_inline, _inline_inner,
)


def generate_table_parser(grammar, first, follow):
    nts      = grammar.get_nonterminals()
    start    = grammar.get_start()
    rules    = grammar.get_rules()
    patterns = grammar.get_token_patterns()

    table         = build_parse_table(grammar, first, follow)
    all_terminals = _collect_terminals(rules, patterns)

    lines = []
    w = lines.append

    # ------------------------------------------------------------------
    # Cabeçalho
    # ------------------------------------------------------------------
    w('"""')
    w('Parser Top-Down Dirigido por Tabela — gerado pelo Grammar Playground.')
    w('')
    w('  oraculo        — tabela LL(1): oraculo[NT][tipo] = [símbolos]')
    w('  pilha          — lista de strings (topo = pilha[-1])')
    w('  actual_tipo    — tipo do token actual')
    w('  actual_lex     — lexema do token actual')
    w('"""')
    w('')
    w('import re')
    w('import sys')
    w('')

    # ------------------------------------------------------------------
    # TreeNode — igual ao RD
    # ------------------------------------------------------------------
    w('# -----------------------------------------------------------------')
    w('# Árvore de derivação')
    w('# -----------------------------------------------------------------')
    w('')
    w('class TreeNode:')
    w('    def __init__(self, label, children=None, lexema=None):')
    w('        self.label    = label')
    w('        self.children = children or []')
    w('        self.lexema   = lexema')
    w('')
    w('    def print_tree(self, prefix="", last=True):')
    w('        branch = "└── " if last else "├── "')
    w('        show   = f"{self.label}: {self.lexema!r}" if self.lexema is not None else self.label')
    w('        print(prefix + branch + show)')
    w('        ext = "    " if last else "│   "')
    w('        for i, child in enumerate(self.children):')
    w('            child.print_tree(prefix + ext, last=(i == len(self.children) - 1))')
    w('')

    # ------------------------------------------------------------------
    # Tokenizador — igual ao RD
    # ------------------------------------------------------------------
    w('# -----------------------------------------------------------------')
    w('# Tokenizador — devolve lista de (tipo, lexema)')
    w('# -----------------------------------------------------------------')
    w('')
    w('def tokenizer(source):')
    w('    tokens = []')
    w('    while source:')

    _inline_map = {t: t[1:-1] for t in all_terminals if _is_inline(t)}
    branches = (
        [(re.escape(inner), inner)
         for _, inner in sorted(_inline_map.items(), key=lambda x: -len(x[1]))]
        + [(pat, nm) for nm, pat in patterns.items()]
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

    # ------------------------------------------------------------------
    # Tabela LL(1) — oraculo[NT][tipo_terminal] = [símbolos]
    # A chave é sempre o TIPO do token (inline ou declarado).
    # ------------------------------------------------------------------
    w('# -----------------------------------------------------------------')
    w('# Tabela LL(1) — oraculo')
    w('# oraculo[NT][tipo] = lista de símbolos do lado direito ([] = ε)')
    w('# -----------------------------------------------------------------')
    w('')
    w('oraculo = {')

    by_nt = {}
    for (nt, terminal), seqs in table.items():
        if not seqs:
            continue
        seq  = seqs[0]
        # converter terminal da tabela para TIPO usado no tokenizador
        tipo = _inline_inner(terminal) if _is_inline(terminal) else terminal
        by_nt.setdefault(nt, {})[tipo] = seq

    for nt in sorted(by_nt):
        w(f'    {nt!r}: {{')
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
            w(f'        {tipo!r}: {rhs!r},  # {nt} → {rhs_comment}')
        w(f'    }},')

    w('}')
    w('')
    w(f'NONTERMINALS = {sorted(nts)!r}')
    w(f'START = {start!r}')
    w('')

    # ------------------------------------------------------------------
    # Estado global
    # ------------------------------------------------------------------
    w('# -----------------------------------------------------------------')
    w('# Estado global')
    w('# -----------------------------------------------------------------')
    w('')
    w('_tokens     = []')
    w('actual_tipo = None')
    w('actual_lex  = None')
    w('')
    w('')
    w('def _advance():')
    w('    global actual_tipo, actual_lex')
    w('    _tokens.pop(0)')
    w('    actual_tipo, actual_lex = _tokens[0]')
    w('')

    # ------------------------------------------------------------------
    # parse() — algoritmo da secção 4.3.2
    # ------------------------------------------------------------------
    w('# -----------------------------------------------------------------')
    w('# parse(source) — algoritmo Top-Down dirigido por tabela')
    w('# -----------------------------------------------------------------')
    w('')
    w('')
    w('def parse(source):')
    w('    global _tokens, actual_tipo, actual_lex')
    w('    _tokens = tokenizer(source)')
    w('    actual_tipo, actual_lex = _tokens[0]')
    w('')
    w('    # nós da árvore indexados por símbolo na pilha')
    w('    raiz = TreeNode(START)')
    w('    # pilha: lista de (símbolo: str, nó: TreeNode|None)')
    w('    pilha = [("$", None), (START, raiz)]')
    w('')
    w('    while True:')
    w('        topo, topo_no = pilha[-1]')
    w('')
    w('        # ACEITE')
    w('        if topo == "$" and actual_tipo == "$":')
    w('            return raiz')
    w('')
    w('        if topo == "$":')
    w('            raise SyntaxError(f"Tokens extra: {actual_tipo!r} ({actual_lex!r})")')
    w('')
    w('        # AVANÇA — topo é terminal')
    w('        if topo not in NONTERMINALS:')
    w('            if actual_tipo == topo:')
    w('                pilha.pop()')
    w('                if topo_no is not None:')
    w('                    topo_no.lexema = actual_lex')
    w('                _advance()')
    w('            else:')
    w('                raise SyntaxError(')
    w('                    f"Esperado {topo!r}, encontrado {actual_tipo!r} ({actual_lex!r})"')
    w('                )')
    w('            continue')
    w('')
    w('        # PRODUÇÃO — consultar oraculo')
    w('        entradas = oraculo.get(topo, {})')
    w('        rhs = entradas.get(actual_tipo)')
    w('        if rhs is None:')
    w('            raise SyntaxError(')
    w('                f"Erro ao expandir {topo!r}: {actual_tipo!r} inesperado. "')
    w('                f"Esperado um de: {list(entradas.keys())}"')
    w('            )')
    w('')
    w('        pilha.pop()')
    w('        if not rhs:')
    w('            # produção ε')
    w('            if topo_no is not None:')
    w('                topo_no.children.append(TreeNode("ε"))')
    w('        else:')
    w('            filhos = [TreeNode(sym) for sym in rhs]')
    w('            if topo_no is not None:')
    w('                topo_no.children.extend(filhos)')
    w('            for sym, filho in reversed(list(zip(rhs, filhos))):')
    w('                pilha.append((sym, filho))')
    w('')

    # ------------------------------------------------------------------
    # Main
    # ------------------------------------------------------------------
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


# =====================================================================
# Lexer + TableParser — interpretadores em tempo de execução
# Usados directamente pelo main.py (não fazem parte do código gerado)
# =====================================================================

class Lexer:
    """Tokenizador parametrizado pelos padrões da gramática."""

    def __init__(self, source, token_patterns):
        self.tokens = []
        pos = 0; line = 1
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
    Parser LL(1) com pilha explícita — interpretador em tempo de execução.
    Segue o algoritmo da secção 4.3.2 do livro.

    Uso:
        p = TableParser(grammar, table, source)
        tree = p.parse()
        p.print_steps()
    """

    def __init__(self, grammar, table, source):
        self.nts   = grammar.get_nonterminals()
        self.start = grammar.get_start()
        self.table = table   # {(NT, terminal): [SeqNode]}
        lex = Lexer(source, grammar.get_token_patterns())
        self.tokens = lex.tokens
        self.pos    = 0
        self.steps  = []

    def _current(self):
        return self.tokens[self.pos]

    def _advance(self):
        self.pos += 1

    def _is_eps(self, seq):
        return not seq.symbols or (
            len(seq.symbols) == 1 and seq.symbols[0].get_is_epsilon()
        )

    def _match_terminal(self, topo, la_tipo):
        """Verifica se o topo da pilha (terminal) corresponde ao tipo actual."""
        # terminal inline na gramática: ex. "'+'" → compara com '+'
        if topo.startswith(("'", '"')):
            return la_tipo == topo[1:-1]
        # terminal declarado: ex. 'ID' → compara directamente
        return la_tipo == topo

    def parse(self):
        raiz  = _TreeNode(self.start)
        pilha = [('$', None), (self.start, raiz)]
        step  = 0

        while True:
            topo, topo_no = pilha[-1]
            la_tipo, la_lex = self._current()

            step += 1
            self.steps.append({
                'step':   step,
                'stack':  [s for s, _ in reversed(pilha)],
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
                    pilha.pop()
                    if topo_no is not None:
                        topo_no.lexema = la_lex
                    self.steps[-1]['action'] = f'avança: {la_tipo!r} = {la_lex!r}'
                    self._advance()
                else:
                    raise SyntaxError(
                        f"Esperado {topo!r}, encontrado {la_tipo!r} ({la_lex!r})"
                    )
                continue

            # PRODUÇÃO — consultar tabela
            # a tabela usa chaves como estão na gramática: 'ID', "'+'" etc.
            cell = self.table.get((topo, la_tipo), [])
            if not cell:
                # tentar com terminal inline entre aspas
                for q in ("'", '"'):
                    cell = self.table.get((topo, f"{q}{la_tipo}{q}"), [])
                    if cell:
                        break

            if not cell:
                esperados = {t for (n, t) in self.table if n == topo}
                raise SyntaxError(
                    f"Símbolo {la_tipo!r} inesperado ao expandir {topo!r}. "
                    f"Esperado: {sorted(esperados)}"
                )

            seq = cell[0]
            pilha.pop()
            is_eps = self._is_eps(seq)
            rhs_str = 'ε' if is_eps else ' '.join(s.get_value() for s in seq.symbols)
            self.steps[-1]['action'] = f'produção: {topo} → {rhs_str}'

            if is_eps:
                if topo_no is not None:
                    topo_no.children.append(_TreeNode('ε'))
            else:
                filhos = [_TreeNode(s.get_value()) for s in seq.symbols]
                if topo_no is not None:
                    topo_no.children.extend(filhos)
                for sym, filho in reversed(list(zip(seq.symbols, filhos))):
                    pilha.append((sym.get_value(), filho))

    def print_steps(self):
        if not self.steps:
            print("  (sem passos)")
            return
        ws = max(30, max(len(' '.join(s['stack'])) for s in self.steps) + 2)
        wi = max(10,  max(len(s['input'])           for s in self.steps) + 2)
        header = f"{'Passo':>5}  {'Pilha':<{ws}}  {'Input':<{wi}}  Ação"
        print(header)
        print('─' * (len(header) + 10))
        for s in self.steps:
            print(f'{s["step"]:>5}  {" ".join(s["stack"]):<{ws}}  {s["input"]:<{wi}}  {s["action"]}')