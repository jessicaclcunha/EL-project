"""
Gerador de parser recursivo descendente.

Dado um SpecNode (gramática parseada) e os conjuntos FIRST/FOLLOW,
gera código Python de um parser recursivo descendente que:
  - Tokeniza o input com base nos padrões da TokenSection
  - Tem uma função parse_<NT>() para cada não-terminal
  - Usa os conjuntos FIRST para decidir que alternativa seguir
  - Constrói a árvore de derivação durante o parsing

Uso:
    from gp_gen_rd import generate_rd_parser
    code = generate_rd_parser(grammar, first, follow)
    # code é uma string com o ficheiro Python gerado
"""

import re

from gp_analysis import compute_first, compute_follow, first_of_seq


def generate_rd_parser(grammar, first, follow):
    """
    Gera o código Python de um parser recursivo descendente.

    Parâmetros:
        grammar : SpecNode  — gramática parseada
        first   : dict      — conjuntos FIRST (NT → set)
        follow  : dict      — conjuntos FOLLOW (NT → set)

    Devolve:
        str — código Python completo do parser gerado
    """
    nts = grammar.get_nonterminals()
    start = grammar.get_start()
    rules = grammar.get_rules()
    patterns = grammar.get_token_patterns()
    terminals = grammar.get_terminals()

    lines = []
    w = lines.append  # shortcut para adicionar linhas

    # -----------------------------------------------------------------
    # Cabeçalho
    # -----------------------------------------------------------------
    w('"""')
    w('Parser recursivo descendente — gerado automaticamente pelo Grammar Playground.')
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

    # -----------------------------------------------------------------
    # Nó da árvore de derivação
    # -----------------------------------------------------------------
    w('# ' + '=' * 67)
    w('# Árvore de derivação')
    w('# ' + '=' * 67)
    w('')
    w('class TreeNode:')
    w('    """Nó da árvore de derivação."""')
    w('')
    w('    def __init__(self, label, children=None, token_value=None):')
    w('        self.label = label             # nome do NT ou terminal')
    w('        self.children = children or [] # filhos (TreeNode)')
    w('        self.token_value = token_value # valor do token (só para folhas)')
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

    # -----------------------------------------------------------------
    # Lexer
    # -----------------------------------------------------------------
    w('# ' + '=' * 67)
    w('# Lexer')
    w('# ' + '=' * 67)
    w('')
    w('class Token:')
    w('    def __init__(self, type_, value, line):')
    w('        self.type = type_')
    w('        self.value = value')
    w('        self.line = line')
    w('')
    w('    def __repr__(self):')
    w('        return f"Token({self.type!r}, {self.value!r})"')
    w('')
    w('')
    w('class Lexer:')
    w('    def __init__(self, source):')
    w('        self.source = source')
    w('        self.tokens = []')
    w('        self._tokenize()')
    w('')
    w('    def _tokenize(self):')
    w('        token_spec = [')

    # Terminais declarados na TokenSection (com regex)
    # Nota: os padrões vêm do utilizador já como regex válido.
    # Escrevemos como raw string r'...' no código gerado.
    for name, pattern in patterns.items():
        w(f"            ({name!r}, r'{pattern}'),")

    # Terminais inline (quoted strings) — gerar regex escapado
    inline_terminals = set()
    for rule in rules:
        for seq in rule.altlist.sequences:
            for sym in seq.symbols:
                if sym.get_is_terminal() and sym.get_value().startswith(("'", '"')):
                    inline_terminals.add(sym.get_value())

    for lit in sorted(inline_terminals):
        # Extrair o conteúdo entre aspas e escapar para regex
        inner = lit[1:-1]
        escaped = re.escape(inner)
        w(f"            ({lit!r}, r'{escaped}'),")

    w('        ]')
    w('        pos = 0')
    w('        line = 1')
    w('        while pos < len(self.source):')
    w('            # Ignorar espaços e tabs')
    w('            m = re.match(r"[ \\t]+", self.source[pos:])')
    w('            if m:')
    w('                pos += m.end()')
    w('                continue')
    w('            # Newlines')
    w('            m = re.match(r"\\n", self.source[pos:])')
    w('            if m:')
    w('                line += 1')
    w('                pos += 1')
    w('                continue')
    w('            # Tentar cada padrão de token')
    w('            matched = False')
    w('            for name, pattern in token_spec:')
    w('                m = re.match(pattern, self.source[pos:])')
    w('                if m:')
    w('                    self.tokens.append(Token(name, m.group(), line))')
    w('                    pos += m.end()')
    w('                    matched = True')
    w('                    break')
    w('            if not matched:')
    w('                raise SyntaxError(')
    w('                    f"Linha {line}: carácter inesperado {self.source[pos]!r}"')
    w('                )')
    w('        self.tokens.append(Token("$", "", line))')
    w('')

    # -----------------------------------------------------------------
    # Parser
    # -----------------------------------------------------------------
    w('# ' + '=' * 67)
    w('# Parser recursivo descendente')
    w('# ' + '=' * 67)
    w('')
    w('class Parser:')
    w('    def __init__(self, tokens):')
    w('        self.tokens = tokens')
    w('        self.pos = 0')
    w('')
    w('    def current(self):')
    w('        """Token atual (lookahead)."""')
    w('        return self.tokens[self.pos]')
    w('')
    w('    def match(self, expected_type):')
    w('        """Consome o token atual se for do tipo esperado."""')
    w('        tok = self.current()')
    w('        if tok.type == expected_type:')
    w('            self.pos += 1')
    w('            return TreeNode(expected_type, token_value=tok.value)')
    w('        else:')
    w('            raise SyntaxError(')
    w('                f"Linha {tok.line}: esperado {expected_type!r}, "')
    w('                f"encontrado {tok.type!r} ({tok.value!r})"')
    w('            )')
    w('')
    w('    def match_value(self, expected_value, label):')
    w('        """Consome o token atual se tiver o valor esperado (para terminais inline)."""')
    w('        tok = self.current()')
    w('        if tok.value == expected_value:')
    w('            self.pos += 1')
    w('            return TreeNode(label, token_value=tok.value)')
    w('        else:')
    w('            raise SyntaxError(')
    w('                f"Linha {tok.line}: esperado {expected_value!r}, "')
    w('                f"encontrado {tok.value!r}"')
    w('            )')
    w('')

    # -----------------------------------------------------------------
    # Gerar uma função parse_<NT> para cada não-terminal
    # -----------------------------------------------------------------
    for rule in rules:
        nt = rule.get_head_name()
        seqs = rule.altlist.sequences
        func_name = _safe_func_name(nt)

        w(f'    def parse_{func_name}(self):')
        w(f'        """Produção: {nt} -> {" | ".join(repr(s) for s in seqs)}"""')
        w(f'        tok = self.current()')

        # Computar FIRST de cada alternativa
        seq_firsts = []
        for seq in seqs:
            sf = first_of_seq(seq.symbols, first, nts)
            seq_firsts.append(sf)

        first_branch = True
        epsilon_idx = None

        for i, (seq, sf) in enumerate(zip(seqs, seq_firsts)):
            # Verificar se é a alternativa epsilon
            is_epsilon_alt = (
                len(seq.symbols) == 1 and seq.symbols[0].get_is_epsilon()
            ) or (not seq.symbols)

            if is_epsilon_alt or (sf == {'ε'}):
                epsilon_idx = i
                continue

            # Construir condição de lookahead
            conditions = []
            for terminal in sorted(sf - {'ε'}):
                conditions.append(_lookahead_condition(terminal))

            if not conditions:
                continue

            cond_str = ' or '.join(conditions)
            keyword = 'if' if first_branch else 'elif'
            first_branch = False

            w(f'        {keyword} {cond_str}:')
            w(f'            # {nt} -> {repr(seq)}')
            _gen_seq_code(w, seq, nt, nts)

        # Alternativa epsilon / anulável — usar FOLLOW
        if epsilon_idx is not None:
            seq = seqs[epsilon_idx]
            follow_terms = follow.get(nt, set())

            if first_branch:
                # Só existe a alternativa epsilon
                w(f'        # {nt} -> ε')
                w(f'        return TreeNode({nt!r}, children=[TreeNode("ε")])')
            else:
                # else: pode ser epsilon se o token está no FOLLOW
                w(f'        else:')
                w(f'            # {nt} -> ε (token atual deve estar no FOLLOW)')
                w(f'            return TreeNode({nt!r}, children=[TreeNode("ε")])')
        else:
            # Sem alternativa epsilon — erro se nenhum branch foi tomado
            if not first_branch:
                w(f'        else:')
                w(f'            raise SyntaxError(')
                w(f'                f"Linha {{tok.line}}: token inesperado {{tok.type!r}} "')
                w(f'                f"({{tok.value!r}}) ao expandir {nt}"')
                w(f'            )')

        w('')

    # -----------------------------------------------------------------
    # Função parse() principal
    # -----------------------------------------------------------------
    w(f'    def parse(self):')
    w(f'        """Ponto de entrada — parse do símbolo inicial."""')
    w(f'        tree = self.parse_{_safe_func_name(start)}()')
    w(f'        if self.current().type != "$":')
    w(f'            tok = self.current()')
    w(f'            raise SyntaxError(')
    w(f'                f"Linha {{tok.line}}: tokens extra após o fim do programa: "')
    w(f'                f"{{tok.type!r}} ({{tok.value!r}})"')
    w(f'            )')
    w(f'        return tree')
    w('')

    # -----------------------------------------------------------------
    # Main
    # -----------------------------------------------------------------
    w('')
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
    w('')
    w('    lex = Lexer(source)')
    w('    print("Tokens:", lex.tokens)')
    w('    print()')
    w('')
    w('    parser = Parser(lex.tokens)')
    w('    try:')
    w('        tree = parser.parse()')
    w('        print("Árvore de derivação:")')
    w('        tree.print_tree()')
    w('    except SyntaxError as e:')
    w('        print(f"Erro: {e}")')
    w('')
    w('')
    w('if __name__ == "__main__":')
    w('    main()')
    w('')

    return '\n'.join(lines)


# =====================================================================
# Funções auxiliares internas
# =====================================================================


def _safe_func_name(nt):
    """
    Converte o nome de um não-terminal num nome de função Python válido.
    Ex: Expr' -> Expr_prime, StmtList -> StmtList
    """
    name = nt.replace("'", "_prime")
    name = re.sub(r'[^A-Za-z0-9_]', '_', name)
    return name


def _lookahead_condition(terminal):
    """
    Gera a condição Python para verificar se o token atual corresponde
    ao terminal dado.

    Terminais nomeados (ID, NUMBER) → tok.type == 'ID'
    Terminais inline (';', '+')    → tok.value == ';'
    """
    if terminal.startswith(("'", '"')):
        inner = terminal[1:-1]
        return f'tok.value == {inner!r}'
    else:
        return f'tok.type == {terminal!r}'


def _gen_seq_code(w, seq, nt, nts):
    """
    Gera o código para processar uma sequência (alternativa) de símbolos.
    Cada símbolo gera ou um match (terminal) ou uma chamada recursiva (NT).
    """
    w(f'            children = []')

    for sym in seq.symbols:
        if sym.get_is_epsilon():
            w(f'            children.append(TreeNode("ε"))')
        elif sym.get_is_terminal():
            val = sym.get_value()
            if val.startswith(("'", '"')):
                inner = val[1:-1]
                w(f'            children.append(self.match_value({inner!r}, {val!r}))')
            else:
                w(f'            children.append(self.match({val!r}))')
        else:
            # Não-terminal — chamada recursiva
            func = _safe_func_name(sym.get_value())
            w(f'            children.append(self.parse_{func}())')

    w(f'            return TreeNode({nt!r}, children=children)')