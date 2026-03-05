import re
from gp_analysis import compute_first, compute_follow, build_parse_table, first_of_seq


# =====================================================================
# Nó da árvore de derivação (igual ao do parser RD gerado)
# =====================================================================

class TreeNode:
    """Nó da árvore de derivação."""

    def __init__(self, label, children=None, token_value=None):
        self.label = label
        self.children = children or []
        self.token_value = token_value

    def is_leaf(self):
        return not self.children

    def print_tree(self, prefix="", is_last=True):
        connector = "└── " if is_last else "├── "
        if self.token_value is not None:
            display = f"{self.label}: {self.token_value!r}"
        else:
            display = self.label
        print(prefix + connector + display)
        extension = "    " if is_last else "│   "
        for i, child in enumerate(self.children):
            child.print_tree(prefix + extension, is_last=(i == len(self.children) - 1))


# =====================================================================
# Lexer genérico (reutilizável para qualquer gramática com TokenSection)
# =====================================================================

class Token:
    def __init__(self, type_, value, line):
        self.type = type_
        self.value = value
        self.line = line

    def __repr__(self):
        return f"Token({self.type!r}, {self.value!r})"


class Lexer:
    """Lexer genérico parametrizado pelos padrões da TokenSection."""

    def __init__(self, source, token_patterns):
        """
        source         : str  — texto a tokenizar
        token_patterns : dict — {NOME: regex_str, ...}  (da TokenSection)
        """
        self.source = source
        self.token_patterns = token_patterns
        self.tokens = []
        self._tokenize()

    def _tokenize(self):
        token_spec = list(self.token_patterns.items())
        pos = 0
        line = 1
        while pos < len(self.source):
            # Ignorar espaços e tabs
            m = re.match(r"[ \t]+", self.source[pos:])
            if m:
                pos += m.end()
                continue
            # Newlines
            m = re.match(r"\n", self.source[pos:])
            if m:
                line += 1
                pos += 1
                continue
            # Tentar cada padrão de token
            matched = False
            for name, pattern in token_spec:
                m = re.match(pattern, self.source[pos:])
                if m:
                    self.tokens.append(Token(name, m.group(), line))
                    pos += m.end()
                    matched = True
                    break
            if not matched:
                raise SyntaxError(
                    f"Linha {line}: carácter inesperado {self.source[pos]!r}"
                )
        self.tokens.append(Token("$", "", line))


# =====================================================================
# Parser Top-Down dirigido por tabela
# =====================================================================

class TableParser:
    """
    Parser LL(1) com pilha explícita.

    Parâmetros:
        grammar  : SpecNode  — gramática (para obter NTs, start, padrões)
        table    : dict      — tabela LL(1): {(NT, terminal): [SeqNode]}
        source   : str       — frase a analisar
    """

    def __init__(self, grammar, table, source):
        self.grammar = grammar
        self.table = table
        self.nts = grammar.get_nonterminals()
        self.start = grammar.get_start()

        # Tokenizar o input
        patterns = grammar.get_token_patterns()
        lex = Lexer(source, patterns)
        self.tokens = lex.tokens
        self.pos = 0

        # Rastreio de passos (para mostrar ao utilizador)
        self.steps = []

    def current(self):
        return self.tokens[self.pos]

    def _consume(self):
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def parse(self):
        """
        Algoritmo principal do parser LL(1) com pilha.

        Devolve a raiz da árvore de derivação se a frase for aceite,
        ou lança SyntaxError em caso de erro.
        """
        start_node = TreeNode(self.start)

        # Pilha de (símbolo_string, TreeNode_pai_ou_None)
        # Cada entrada é (símbolo, nó_da_árvore_a_preencher)
        stack = [("$", None), (self.start, start_node)]

        step_num = 0

        while stack:
            top_sym, top_node = stack[-1]
            lookahead = self.current()

            step_num += 1
            stack_display = [s for s, _ in reversed(stack)]
            self.steps.append({
                'step': step_num,
                'stack': list(stack_display),
                'input': lookahead.value or '$',
                'action': '',
            })

            # ── Caso 1: topo == $ e lookahead == $ → ACEITE ──────────────
            if top_sym == "$" and lookahead.type == "$":
                self.steps[-1]['action'] = "ACEITE"
                return start_node

            # ── Caso 2: topo == $ mas ainda há input → ERRO ──────────────
            if top_sym == "$":
                raise SyntaxError(
                    f"Linha {lookahead.line}: tokens extra após o fim do programa: "
                    f"{lookahead.type!r} ({lookahead.value!r})"
                )

            # ── Caso 3: topo é terminal ───────────────────────────────────
            if top_sym not in self.nts:
                # Verificar se corresponde ao lookahead
                if self._matches_terminal(top_sym, lookahead):
                    stack.pop()
                    tok = self._consume()
                    if top_node is not None:
                        top_node.token_value = tok.value
                    self.steps[-1]['action'] = f"match {tok.type!r} = {tok.value!r}"
                else:
                    raise SyntaxError(
                        f"Linha {lookahead.line}: esperado {top_sym!r}, "
                        f"encontrado {tok.type!r} ({tok.value!r})"
                        if False else
                        f"Linha {lookahead.line}: esperado {top_sym!r}, "
                        f"encontrado {lookahead.type!r} ({lookahead.value!r})"
                    )
                continue

            # ── Caso 4: topo é não-terminal ───────────────────────────────
            # Determinar o token de lookahead para consultar a tabela
            la_key = self._lookahead_key(lookahead)

            cell = self.table.get((top_sym, la_key), [])

            if not cell:
                # Tentar com '$' se estamos no fim
                expected = self._expected_tokens(top_sym)
                raise SyntaxError(
                    f"Linha {lookahead.line}: token inesperado {lookahead.type!r} "
                    f"({lookahead.value!r}) ao expandir {top_sym!r}. "
                    f"Esperado: {{{', '.join(sorted(expected))}}}"
                )

            if len(cell) > 1:
                raise SyntaxError(
                    f"Conflito na tabela para ({top_sym!r}, {la_key!r}): "
                    f"gramática não é LL(1)."
                )

            seq = cell[0]
            stack.pop()

            # Registar a produção usada
            prod_str = f"{top_sym} → {repr(seq)}"
            self.steps[-1]['action'] = f"produção: {prod_str}"

            # Criar nós filhos e empilhar em ordem inversa
            child_nodes = []
            symbols = seq.symbols

            # Verificar se é a produção epsilon
            is_epsilon = (
                len(symbols) == 1 and symbols[0].get_is_epsilon()
            ) or not symbols

            if is_epsilon:
                eps_node = TreeNode("ε")
                top_node.children.append(eps_node)
                # Não empilha nada — produção vazia
            else:
                for sym in symbols:
                    child_node = TreeNode(sym.get_value())
                    top_node.children.append(child_node)
                    child_nodes.append((sym.get_value(), child_node))

                # Empilhar em ordem inversa (topo = primeiro símbolo)
                for sym_str, child_nd in reversed(child_nodes):
                    stack.append((sym_str, child_nd))

        raise SyntaxError("Fim inesperado da pilha.")

    def _lookahead_key(self, token):
        """
        Determina a chave a usar na tabela para o token dado.
        Terminais nomeados (ID, NUMBER) → usa o tipo.
        Terminais inline ('(', '+') → usa o valor.
        """
        # Tentar pelo tipo primeiro (terminais nomeados)
        if token.type != "$":
            return token.type
        return "$"

    def _matches_terminal(self, top_sym, token):
        """Verifica se o terminal no topo da pilha corresponde ao lookahead."""
        # Terminal inline: o símbolo é o valor esperado (e.g. ';', '+')
        if top_sym.startswith(("'", '"')):
            inner = top_sym[1:-1]
            return token.value == inner
        # Terminal nomeado: comparar com o tipo do token
        return token.type == top_sym

    def _expected_tokens(self, nt):
        """Devolve o conjunto de terminais para os quais há entrada na tabela para nt."""
        return {t for (n, t) in self.table if n == nt}

    def print_steps(self):
        """Imprime os passos do parsing numa tabela legível."""
        if not self.steps:
            print("  (sem passos registados)")
            return

        w_step  = 5
        w_stack = max(30, max(len(' '.join(s['stack'])) for s in self.steps) + 2)
        w_input = max(10, max(len(s['input']) for s in self.steps) + 2)

        header = (f"{'Passo':>{w_step}}  "
                  f"{'Pilha':<{w_stack}}  "
                  f"{'Input':<{w_input}}  "
                  f"Ação")
        print(header)
        print("─" * (len(header) + 20))

        for s in self.steps:
            stack_str = ' '.join(s['stack'])
            print(f"{s['step']:>{w_step}}  "
                  f"{stack_str:<{w_stack}}  "
                  f"{s['input']:<{w_input}}  "
                  f"{s['action']}")


# =====================================================================
# Gerador de código Python do parser dirigido por tabela
# =====================================================================

def generate_table_parser(grammar, first, follow):
    """
    Gera o código Python completo de um parser LL(1) dirigido por tabela.

    Incorpora a tabela LL(1) como dicionário Python estático no código gerado,
    tornando o parser completamente autónomo (sem dependência do Grammar Playground).

    Parâmetros:
        grammar : SpecNode
        first   : dict
        follow  : dict

    Devolve:
        str — código Python completo do parser gerado
    """
    nts      = grammar.get_nonterminals()
    start    = grammar.get_start()
    rules    = grammar.get_rules()
    patterns = grammar.get_token_patterns()

    table = build_parse_table(grammar, first, follow)

    lines = []
    w = lines.append

    # ── Cabeçalho ────────────────────────────────────────────────────
    w('"""')
    w('Parser LL(1) dirigido por tabela — gerado automaticamente pelo Grammar Playground.')
    w('')
    w('Gramática:')
    for rule in rules:
        alts = ' | '.join(repr(seq) for seq in rule.altlist.sequences)
        w(f'    {rule.get_head_name()} -> {alts}')
    w('')
    w(f'Símbolo inicial: {start}')
    w('"""')
    w('')
    w('import re')
    w('import sys')
    w('')

    # ── TreeNode ─────────────────────────────────────────────────────
    w('# ' + '=' * 67)
    w('# Árvore de derivação')
    w('# ' + '=' * 67)
    w('')
    w('class TreeNode:')
    w('    """Nó da árvore de derivação."""')
    w('    def __init__(self, label, children=None, token_value=None):')
    w('        self.label = label')
    w('        self.children = children or []')
    w('        self.token_value = token_value')
    w('')
    w('    def is_leaf(self):')
    w('        return not self.children')
    w('')
    w('    def print_tree(self, prefix="", is_last=True):')
    w('        connector = "└── " if is_last else "├── "')
    w('        if self.token_value is not None:')
    w('            display = f"{self.label}: {self.token_value!r}"')
    w('        else:')
    w('            display = self.label')
    w('        print(prefix + connector + display)')
    w('        extension = "    " if is_last else "│   "')
    w('        for i, child in enumerate(self.children):')
    w('            child.print_tree(prefix + extension, is_last=(i == len(self.children) - 1))')
    w('')

    # ── Token / Lexer ─────────────────────────────────────────────────
    w('# ' + '=' * 67)
    w('# Lexer')
    w('# ' + '=' * 67)
    w('')
    w('class Token:')
    w('    def __init__(self, type_, value, line):')
    w('        self.type = type_')
    w('        self.value = value')
    w('        self.line = line')
    w('    def __repr__(self):')
    w('        return f"Token({self.type!r}, {self.value!r})"')
    w('')
    w('class Lexer:')
    w('    TOKEN_SPEC = [')
    for name, pattern in patterns.items():
        w(f"        ({name!r}, r'{pattern}'),")
    w('    ]')
    w('    def __init__(self, source):')
    w('        self.source = source')
    w('        self.tokens = []')
    w('        self._tokenize()')
    w('    def _tokenize(self):')
    w('        pos = 0; line = 1')
    w('        while pos < len(self.source):')
    w('            m = re.match(r"[ \\t]+", self.source[pos:])')
    w('            if m: pos += m.end(); continue')
    w('            m = re.match(r"\\n", self.source[pos:])')
    w('            if m: line += 1; pos += 1; continue')
    w('            matched = False')
    w('            for name, pattern in self.TOKEN_SPEC:')
    w('                m = re.match(pattern, self.source[pos:])')
    w('                if m:')
    w('                    self.tokens.append(Token(name, m.group(), line))')
    w('                    pos += m.end(); matched = True; break')
    w('            if not matched:')
    w('                raise SyntaxError(f"Linha {line}: carácter inesperado {self.source[pos]!r}")')
    w('        self.tokens.append(Token("$", "", line))')
    w('')

    # ── Tabela LL(1) estática ─────────────────────────────────────────
    w('# ' + '=' * 67)
    w('# Tabela LL(1) (gerada estaticamente)')
    w('# ' + '=' * 67)
    w('')
    w('# Formato: {(NT, terminal): [lista de símbolos da produção]}')
    w('# Uma lista vazia representa a produção epsilon.')
    w('PARSE_TABLE = {')
    for (nt, terminal), seqs in sorted(table.items(), key=lambda x: (x[0][0], x[0][1])):
        if seqs:
            seq = seqs[0]  # LL(1): no máximo uma entrada por célula
            symbols_repr = [s.get_value() for s in seq.symbols]
            # Verificar se é epsilon
            is_eps = (len(seq.symbols) == 1 and seq.symbols[0].get_is_epsilon()) or not seq.symbols
            if is_eps:
                w(f'    ({nt!r}, {terminal!r}): [],  # {nt} → ε')
            else:
                w(f'    ({nt!r}, {terminal!r}): {symbols_repr!r},  # {nt} → {repr(seq)}')
    w('}')
    w('')

    # ── NTs (para distinguir terminais de NTs na pilha) ───────────────
    nts_sorted = sorted(nts)
    w(f'NONTERMINALS = {nts_sorted!r}')
    w(f'START = {start!r}')
    w('')

    # ── Parser ─────────────────────────────────────────────────────────
    w('# ' + '=' * 67)
    w('# Parser LL(1) dirigido por tabela')
    w('# ' + '=' * 67)
    w('')
    w('class Parser:')
    w('    def __init__(self, tokens):')
    w('        self.tokens = tokens')
    w('        self.pos = 0')
    w('        self.steps = []')
    w('')
    w('    def current(self):')
    w('        return self.tokens[self.pos]')
    w('')
    w('    def _consume(self):')
    w('        tok = self.tokens[self.pos]; self.pos += 1; return tok')
    w('')
    w('    def _matches(self, top_sym, token):')
    w('        if top_sym.startswith(("\'", \'"\')):\n            return token.value == top_sym[1:-1]')
    w('        return token.type == top_sym')
    w('')
    w('    def parse(self):')
    w('        root = TreeNode(START)')
    w('        stack = [("$", None), (START, root)]')
    w('        step = 0')
    w('        while stack:')
    w('            top_sym, top_node = stack[-1]')
    w('            la = self.current()')
    w('            step += 1')
    w('            self.steps.append({')
    w('                "step": step,')
    w('                "stack": [s for s, _ in reversed(stack)],')
    w('                "input": la.value or "$",')
    w('                "action": "",')
    w('            })')
    w('            if top_sym == "$" and la.type == "$":')
    w('                self.steps[-1]["action"] = "ACEITE"')
    w('                return root')
    w('            if top_sym == "$":')
    w('                raise SyntaxError(f"Linha {la.line}: tokens extra: {la.type!r} ({la.value!r})")')
    w('            if top_sym not in NONTERMINALS:')
    w('                if self._matches(top_sym, la):')
    w('                    stack.pop(); tok = self._consume()')
    w('                    if top_node is not None: top_node.token_value = tok.value')
    w('                    self.steps[-1]["action"] = f"match {tok.type!r} = {tok.value!r}"')
    w('                else:')
    w('                    raise SyntaxError(f"Linha {la.line}: esperado {top_sym!r}, encontrado {la.type!r} ({la.value!r})")')
    w('                continue')
    w('            la_key = la.type if la.type != "$" else "$"')
    w('            prod = PARSE_TABLE.get((top_sym, la_key))')
    w('            if prod is None:')
    w('                expected = {t for (n, t) in PARSE_TABLE if n == top_sym}')
    w('                raise SyntaxError(f"Linha {la.line}: token inesperado {la.type!r} ao expandir {top_sym!r}. Esperado: {expected}")')
    w('            stack.pop()')
    w('            self.steps[-1]["action"] = f"produção: {top_sym} → {chr(32).join(prod) if prod else chr(949)}"')
    w('            if not prod:')
    w('                if top_node: top_node.children.append(TreeNode("ε"))')
    w('            else:')
    w('                children = [TreeNode(sym) for sym in prod]')
    w('                if top_node: top_node.children.extend(children)')
    w('                for sym, cn in reversed(list(zip(prod, children))): stack.append((sym, cn))')
    w('        raise SyntaxError("Fim inesperado da pilha.")')
    w('')
    w('    def print_steps(self):')
    w('        w_stack = max(30, max(len(" ".join(s["stack"])) for s in self.steps) + 2)')
    w('        w_input = max(10, max(len(s["input"]) for s in self.steps) + 2)')
    w('        print(f\'{"Passo":>5}  {"Pilha":<{w_stack}}  {"Input":<{w_input}}  Ação\')')
    w('        print("─" * (w_stack + w_input + 30))')
    w('        for s in self.steps:')
    w('            print(f\'{s["step"]:>5}  {" ".join(s["stack"]):<{w_stack}}  {s["input"]:<{w_input}}  {s["action"]}\')')
    w('')

    # ── Main ──────────────────────────────────────────────────────────
    w('# ' + '=' * 67)
    w('# Main')
    w('# ' + '=' * 67)
    w('')
    w('def main():')
    w('    if len(sys.argv) > 1:')
    w('        with open(sys.argv[1], encoding="utf-8") as f:')
    w('            source = f.read()')
    w('    else:')
    w('        source = input("Frase a analisar: ")')
    w('    lex = Lexer(source)')
    w('    print("Tokens:", lex.tokens)')
    w('    print()')
    w('    p = Parser(lex.tokens)')
    w('    try:')
    w('        tree = p.parse()')
    w('        print("Passos do parsing:")')
    w('        p.print_steps()')
    w('        print()')
    w('        print("Árvore de derivação:")')
    w('        tree.print_tree()')
    w('    except SyntaxError as e:')
    w('        print(f"Erro: {e}")')
    w('        print("Passos até ao erro:")')
    w('        p.print_steps()')
    w('')
    w('if __name__ == "__main__":')
    w('    main()')
    w('')

    return '\n'.join(lines)