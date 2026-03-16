import re
from gp_analysis import compute_first, compute_follow, build_parse_table, first_of_seq


class TreeNode:
    def __init__(self, label, children=None, token_value=None):
        self.label = label
        self.children = children or []
        self.token_value = token_value

    def print_tree(self, prefix="", is_last=True):
        connector = "└── " if is_last else "├── "
        display = (f"{self.label}: {self.token_value!r}"
                   if self.token_value is not None else self.label)
        print(prefix + connector + display)
        ext = "    " if is_last else "│   "
        for i, child in enumerate(self.children):
            child.print_tree(prefix + ext,
                             is_last=(i == len(self.children) - 1))


# =====================================================================
# Funções auxiliares internas (partilhadas com o RD)
# =====================================================================

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


def _enum_name(terminal):
    # O marcador de fim-de-cadeia $ mapeia para o membro EOF do enum
    if terminal == '$':
        return 'EOF'
    if terminal.startswith(("'", '"')):
        inner = terminal[1:-1]
        _MAP = {
            '+': 'PLUS',  '-': 'MINUS',  '*': 'TIMES',  '/': 'DIVIDE',
            '(': 'LPAREN', ')': 'RPAREN', '[': 'LBRACKET', ']': 'RBRACKET',
            '{': 'LBRACE', '}': 'RBRACE', ';': 'SEMI',   ',': 'COMMA',
            '.': 'DOT',   ':': 'COLON',  '=': 'EQ',     '!': 'BANG',
            '<': 'LT',    '>': 'GT',    ':=': 'ASSIGN',  '==': 'EQEQ',
            '!=': 'NEQ',  '<=': 'LEQ',  '>=': 'GEQ',    '->': 'ARROW',
            '|': 'PIPE',  '&': 'AMP',   '%': 'PERCENT',  '^': 'CARET',
        }
        if inner in _MAP:
            return _MAP[inner]
        name = re.sub(r'[^A-Za-z0-9]', '_', inner).upper()
        return name or 'TOK'
    return terminal.upper()


# =====================================================================
# Gerador de código Python do parser dirigido por tabela
# =====================================================================

def generate_table_parser(grammar, first, follow):
    """
    Gera o código Python completo de um parser LL(1) dirigido por tabela,
    no mesmo estilo do parser recursivo descendente gerado.

    Algoritmo: pilha explícita (secção 4.3.2 do livro de referência).
      - Pilha inicializada com ['$', start]
      - Loop:
          a. topo=='$' e lookahead==EOF  →  ACEITE
          b. topo é terminal             →  match e avança
          c. topo é NT                   →  consultar tabela, expandir produção
    """
    nts      = grammar.get_nonterminals()
    start    = grammar.get_start()
    rules    = grammar.get_rules()
    patterns = grammar.get_token_patterns()

    table = build_parse_table(grammar, first, follow)
    all_terminals = _collect_terminals(rules, patterns)

    lines = []
    p = lines.append

    p('''"""''')
    p('Parser LL(1) dirigido por tabela — gerado automaticamente pelo Grammar Playground.')
    p('''"""''')
    p('')
    p('from enum import Enum')
    p('import re')
    p('import sys')
    p('')

    # --- Enum Tokens ---
    p('# Tokens')
    p('')
    p('class Tokens(Enum):')
    for i, name in enumerate(all_terminals):
        p(f'    {_enum_name(name)} = {i}')
    p('    EOF = -1')
    p('')

    # --- TreeNode ---
    p('# Árvore de derivação')
    p('')
    p('class TreeNode:')
    p('    def __init__(self, label, children=None, token_value=None):')
    p('        self.label = label')
    p('        self.children = children or []')
    p('        self.token_value = token_value')
    p('')
    p('    def print_tree(self, prefix="", is_last=True):')
    p('        connector = "└── " if is_last else "├── "')
    p('        display = (f"{self.label}: {self.token_value!r}"')
    p('                   if self.token_value is not None else self.label)')
    p('        print(prefix + connector + display)')
    p('        ext = "    " if is_last else "│   "')
    p('        for i, child in enumerate(self.children):')
    p('            child.print_tree(prefix + ext,')
    p('                             is_last=(i == len(self.children) - 1))')
    p('')

    # --- Tokenizador ---
    p('# Tokenizador')
    p('')
    p('def tokenizer(source):')
    p('    result = []')
    p('    while len(source) > 0:')

    _inline = {t: t[1:-1] for t in all_terminals if t.startswith(("'", '"'))}
    _branches = (
        [(re.escape(inner), _enum_name(lit))
         for lit, inner in sorted(_inline.items(), key=lambda x: -len(x[1]))]
        + [(pat, _enum_name(nm)) for nm, pat in patterns.items()]
    )
    for idx, (pat, enum_n) in enumerate(_branches):
        kw = 'if' if idx == 0 else 'elif'
        p(f'        {kw} m := re.match(r"{pat}", source):')
        p(f'            result.append((Tokens.{enum_n}, m.group()))')
        p(f'            source = source[m.end():]')

    p('        elif source[0] in " \\n\\t":')
    p('            source = source[1:]')
    p('        else:')
    p('            raise ValueError(f"Carácter inválido: {source[0]!r}")')
    p('    return result + [(Tokens.EOF, None)]')
    p('')

    # --- Tabela LL(1) ---
    p('# Tabela LL(1)')
    p('# {(NT: str, Tokens.<T>): [símbolos: str]}  — lista vazia = epsilon')
    p('')
    p('PARSE_TABLE = {')
    for (nt, terminal), seqs in sorted(table.items(), key=lambda x: (x[0][0], x[0][1])):
        if not seqs:
            continue
        seq = seqs[0]
        enum_n = _enum_name(terminal)
        is_eps = (
            (len(seq.symbols) == 1 and seq.symbols[0].get_is_epsilon())
            or not seq.symbols
        )
        if is_eps:
            p(f'    ({nt!r}, Tokens.{enum_n}): [],  # {nt} → ε')
        else:
            syms = [s.get_value() for s in seq.symbols]
            p(f'    ({nt!r}, Tokens.{enum_n}): {syms!r},  # {nt} → {repr(seq)}')
    p('}')
    p('')

    p(f'NONTERMINALS = {sorted(nts)!r}')
    p(f'START = {start!r}')
    p('')

    # --- Estado global ---
    p('tokens = None')
    p('_steps = []')
    p('')
    p('')
    p('def current_token():')
    p('    return tokens[0]')
    p('')
    p('')
    p('def next_token():')
    p('    tokens.pop(0)')
    p('')

    # --- match terminal ---
    # Usar raw string para evitar problemas com aspas
    p('')
    p('def _match_terminal(top_sym, tok_type, tok_val):')
    p('    if top_sym[0] in (chr(39), chr(34)): return tok_val == top_sym[1:-1]')
    p('    try: return tok_type == Tokens[top_sym]')
    p('    except KeyError: return False')
    p('')

    # --- parse() ---
    p('')
    p('def parse(tk):')
    p('    """Parser LL(1) com pilha explícita."""')
    p('    global tokens, _steps')
    p('    tokens = list(tk)')
    p('    _steps = []')
    p('')
    p('    root = TreeNode(START)')
    p('    # Pilha: [(símbolo_str, TreeNode|None)]')
    p('    # Inicializar com [$, start] conforme algoritmo do livro')
    p('    stack = [("$", None), (START, root)]')
    p('    step = 0')
    p('')
    p('    while stack:')
    p('        top_sym, top_node = stack[-1]')
    p('        la_type, la_val = current_token()')
    p('')
    p('        step += 1')
    p('        _steps.append({')
    p('            "step": step,')
    p('            "stack": [s for s, _ in reversed(stack)],')
    p('            "input": la_val if la_val is not None else "$",')
    p('            "action": "",')
    p('        })')
    p('')
    p('        # a) ACEITE')
    p('        if top_sym == "$" and la_type == Tokens.EOF:')
    p('            _steps[-1]["action"] = "ACEITE"')
    p('            return root')
    p('')
    p('        if top_sym == "$":')
    p('            raise ValueError(f"Tokens extra: {la_type!r} ({la_val!r})")')
    p('')
    p('        # b) terminal -> match')
    p('        if top_sym not in NONTERMINALS:')
    p('            if _match_terminal(top_sym, la_type, la_val):')
    p('                stack.pop()')
    p('                if top_node is not None: top_node.token_value = la_val')
    p('                _steps[-1]["action"] = f"match {la_type.name!r} = {la_val!r}"')
    p('                next_token()')
    p('            else:')
    p('                raise ValueError(f"Esperado {top_sym!r}, encontrado {la_type.name!r} ({la_val!r})")')
    p('            continue')
    p('')
    p('        # c) NT -> consultar tabela')
    p('        prod = PARSE_TABLE.get((top_sym, la_type))')
    p('        if prod is None:')
    p('            expected = {t.name for (n, t) in PARSE_TABLE if n == top_sym}')
    p('            raise ValueError(f"Token inesperado {la_type.name!r} ao expandir {top_sym!r}. Esperado: {expected}")')
    p('')
    p('        stack.pop()')
    p('        prod_display = " ".join(prod) if prod else "ε"')
    p('        _steps[-1]["action"] = f"produção: {top_sym} → {prod_display}"')
    p('')
    p('        if not prod:')
    p('            if top_node is not None: top_node.children.append(TreeNode("ε"))')
    p('        else:')
    p('            children = [TreeNode(sym) for sym in prod]')
    p('            if top_node is not None: top_node.children.extend(children)')
    p('            for sym, cn in reversed(list(zip(prod, children))): stack.append((sym, cn))')
    p('')
    p('    raise ValueError("Fim inesperado da pilha.")')
    p('')

    # --- print_steps ---
    p('')
    p('def print_steps():')
    p('    if not _steps: print("  (sem passos registados)"); return')
    p('    ws = max(30, max(len(" ".join(s["stack"])) for s in _steps) + 2)')
    p('    wi = max(10, max(len(str(s["input"])) for s in _steps) + 2)')
    p("    header = f\"{'Passo':>5}  {'Pilha':<{ws}}  {'Input':<{wi}}  Ação\"")
    p('    print(header)')
    p('    print("-" * (len(header) + 20))')
    p('    for s in _steps:')
    p('        ss = " ".join(s["stack"])')
    p('        inp = str(s["input"])')
    p('        print(f\'{s["step"]:>5}  {ss:<{ws}}  {inp:<{wi}}  {s["action"]}\')')
    p('')

    # --- Main ---
    p('')
    p('def main():')
    p('    if len(sys.argv) > 1:')
    p('        with open(sys.argv[1], encoding="utf-8") as f: source = f.read()')
    p('    else: source = input("? ")')
    p('    try:')
    p('        tk = tokenizer(source)')
    p('        tree = parse(tk)')
    p('        print("Passos do parsing:")')
    p('        print_steps()')
    p('        print()')
    p('        print("Árvore de derivação:")')
    p('        tree.print_tree()')
    p('    except (ValueError, SyntaxError) as e:')
    p('        print(f"Erro: {e}", file=sys.stderr)')
    p('        print("Passos até ao erro:")')
    p('        print_steps()')
    p('')
    p('')
    p('if __name__ == "__main__":')
    p('    main()')
    p('')

    return chr(10).join(lines)


# =====================================================================
# Token / Lexer / TableParser  —  interpretador em tempo de execução
# Usado directamente pelo main.py e pelos testes.
# =====================================================================

class Token:
    def __init__(self, type_, value, line):
        self.type = type_; self.value = value; self.line = line
    def __repr__(self):
        return f"Token({self.type!r}, {self.value!r})"


class Lexer:
    """Lexer genérico parametrizado pelos padrões da TokenSection."""

    def __init__(self, source, token_patterns):
        self.source = source
        self.token_patterns = token_patterns
        self.tokens = []
        self._tokenize()

    def _tokenize(self):
        token_spec = list(self.token_patterns.items())
        pos = 0; line = 1
        while pos < len(self.source):
            m = re.match(r"[ \t]+", self.source[pos:])
            if m: pos += m.end(); continue
            m = re.match(r"\n", self.source[pos:])
            if m: line += 1; pos += 1; continue
            matched = False
            for name, pattern in token_spec:
                m = re.match(pattern, self.source[pos:])
                if m:
                    self.tokens.append(Token(name, m.group(), line))
                    pos += m.end(); matched = True; break
            if not matched:
                raise SyntaxError(f"Linha {line}: carácter inesperado {self.source[pos]!r}")
        self.tokens.append(Token("$", "", line))


class TableParser:
    """
    Parser LL(1) com pilha explícita — interpretador em tempo de execução.

    Algoritmo (secção 4.3.2 do livro de referência):
      Pilha inicializada com ["$", start].
      Loop:
        - topo == "$" e lookahead == "$"  →  ACEITE
        - topo é terminal                 →  match e avança
        - topo é NT                       →  consultar tabela, expandir produção
    """

    def __init__(self, grammar, table, source):
        self.grammar = grammar
        self.table = table
        self.nts = grammar.get_nonterminals()
        self.start = grammar.get_start()
        lex = Lexer(source, grammar.get_token_patterns())
        self.tokens = lex.tokens
        self.pos = 0
        self.steps = []

    def current(self): return self.tokens[self.pos]

    def _consume(self):
        tok = self.tokens[self.pos]; self.pos += 1; return tok

    def parse(self):
        start_node = TreeNode(self.start)
        stack = [("$", None), (self.start, start_node)]
        step_num = 0

        while stack:
            top_sym, top_node = stack[-1]
            la = self.current()

            step_num += 1
            self.steps.append({
                'step': step_num,
                'stack': [s for s, _ in reversed(stack)],
                'input': la.value or "$",
                'action': "",
            })

            # ACEITE
            if top_sym == "$" and la.type == "$":
                self.steps[-1]['action'] = "ACEITE"
                return start_node

            # tokens extra
            if top_sym == "$":
                raise SyntaxError(
                    f"Linha {la.line}: tokens extra: {la.type!r} ({la.value!r})")

            # terminal → match
            if top_sym not in self.nts:
                if self._match(top_sym, la):
                    stack.pop(); tok = self._consume()
                    if top_node is not None: top_node.token_value = tok.value
                    self.steps[-1]['action'] = f"match {tok.type!r} = {tok.value!r}"
                else:
                    raise SyntaxError(
                        f"Linha {la.line}: esperado {top_sym!r}, "
                        f"encontrado {la.type!r} ({la.value!r})")
                continue

            # NT → consultar tabela
            la_key = la.type if la.type != "$" else "$"
            cell = self.table.get((top_sym, la_key), [])
            if not cell:
                exp = self._expected(top_sym)
                raise SyntaxError(
                    f"Linha {la.line}: token inesperado {la.type!r} "
                    f"({la.value!r}) ao expandir {top_sym!r}. "
                    f"Esperado: {{{chr(44).join(sorted(exp))}}}")
            if len(cell) > 1:
                raise SyntaxError(f"Conflito ({top_sym!r}, {la_key!r}): não é LL(1).")

            seq = cell[0]; stack.pop()
            self.steps[-1]['action'] = f"produção: {top_sym} → {repr(seq)}"

            symbols = seq.symbols
            is_eps = (len(symbols) == 1 and symbols[0].get_is_epsilon()) or not symbols
            if is_eps:
                if top_node is not None: top_node.children.append(TreeNode("ε"))
            else:
                cns = [TreeNode(s.get_value()) for s in symbols]
                if top_node is not None: top_node.children.extend(cns)
                for s, cn in reversed(list(zip(symbols, cns))):
                    stack.append((s.get_value(), cn))

        raise SyntaxError("Fim inesperado da pilha.")

    def _match(self, top_sym, token):
        if top_sym[0] in (chr(39), chr(34)): return token.value == top_sym[1:-1]
        return token.type == top_sym

    def _expected(self, nt):
        return {t for (n, t) in self.table if n == nt}

    def print_steps(self):
        if not self.steps: print("  (sem passos registados)"); return
        ws = max(30, max(len(" ".join(s["stack"])) for s in self.steps) + 2)
        wi = max(10, max(len(s["input"]) for s in self.steps) + 2)
        header = f"{'Passo':>5}  {'Pilha':<{ws}}  {'Input':<{wi}}  Ação"
        print(header)
        print("─" * (len(header) + 20))
        for s in self.steps:
            ss = " ".join(s["stack"])
            print(f'{s["step"]:>5}  {ss:<{ws}}  {s["input"]:<{wi}}  {s["action"]}')