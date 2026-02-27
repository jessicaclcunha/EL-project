# ---------------------------------------------------------------------------
# Nós folha (tokens)
# ---------------------------------------------------------------------------

class IdentifierNode:
    """Nome de um não-terminal (PascalCase, pode ter ' no fim)."""
    def __init__(self, value):
        self.value = value
    def __repr__(self):
        return f'NONTERM: "{self.value}"'
    def __eq__(self, other):
        return isinstance(other, IdentifierNode) and self.value == other.value
    def print_tree(self, prefix="", is_last=True):
        c = "└── " if is_last else "├── "
        print(prefix + c + repr(self))


class TerminalNameNode:
    """Nome de um terminal declarado (só maiúsculas, ex: ID, NUMBER)."""
    def __init__(self, value):
        self.value = value
    def __repr__(self):
        return f'TERMINAL_NAME: "{self.value}"'
    def __eq__(self, other):
        return isinstance(other, TerminalNameNode) and self.value == other.value
    def print_tree(self, prefix="", is_last=True):
        c = "└── " if is_last else "├── "
        print(prefix + c + repr(self))


class StringNode:
    """Terminal inline entre aspas simples, ex: '+', ':='."""
    def __init__(self, value):
        self.value = value
    def __repr__(self):
        return f"STRING: {self.value}"
    def __eq__(self, other):
        return isinstance(other, StringNode) and self.value == other.value
    def print_tree(self, prefix="", is_last=True):
        c = "└── " if is_last else "├── "
        print(prefix + c + repr(self))


class RegexNode:
    """Padrão regex entre /.../ ."""
    def __init__(self, value):
        self.value = value
    def __repr__(self):
        return f'REGEX: "/{self.value}/"'
    def __eq__(self, other):
        return isinstance(other, RegexNode) and self.value == other.value
    def print_tree(self, prefix="", is_last=True):
        c = "└── " if is_last else "├── "
        print(prefix + c + repr(self))


class EpsilonNode:
    """Símbolo epsilon."""
    def __repr__(self):
        return 'EPSILON: "ε"'
    def __eq__(self, other):
        return isinstance(other, EpsilonNode)
    def print_tree(self, prefix="", is_last=True):
        c = "└── " if is_last else "├── "
        print(prefix + c + repr(self))


# ---------------------------------------------------------------------------
# Nós intermédios — secção Grammar
# ---------------------------------------------------------------------------

class SymbolNode:
    """Symbol → NonTerm | TERMINAL_NAME | 'quoted' | epsilon"""

    def __init__(self, child):
        self.child = child

    def __repr__(self):
        return f'SymbolNode({self.child})'

    def __eq__(self, other):
        return isinstance(other, SymbolNode) and self.child == other.child

    def print_tree(self, prefix="", is_last=True):
        c = "└── " if is_last else "├── "
        ext = "    " if is_last else "│   "
        print(prefix + c + "Symbol")
        self.child.print_tree(prefix + ext, is_last=True)

    def get_value(self):
        if isinstance(self.child, EpsilonNode):
            return 'ε'
        return self.child.value

    def get_is_terminal(self):
        return isinstance(self.child, (TerminalNameNode, StringNode))

    def get_is_epsilon(self):
        return isinstance(self.child, EpsilonNode)


class SeqNode:
    """Sequência de símbolos numa alternativa."""

    def __init__(self, symbols=None):
        self.symbols = symbols if symbols is not None else []

    def __repr__(self):
        return ' '.join(s.get_value() for s in self.symbols) if self.symbols else 'ε'

    def __eq__(self, other):
        return isinstance(other, SeqNode) and self.symbols == other.symbols

    def print_tree(self, prefix="", is_last=True):
        c = "└── " if is_last else "├── "
        ext = "    " if is_last else "│   "
        print(prefix + c + "Seq")
        if not self.symbols:
            EpsilonNode().print_tree(prefix + ext, is_last=True)
        else:
            for i, sym in enumerate(self.symbols):
                sym.print_tree(prefix + ext, is_last=(i == len(self.symbols) - 1))


class AltListNode:
    """Lista de alternativas separadas por |."""

    def __init__(self, sequences=None):
        self.sequences = sequences if sequences is not None else []

    def __repr__(self):
        return f'AltListNode({self.sequences})'

    def __eq__(self, other):
        return isinstance(other, AltListNode) and self.sequences == other.sequences

    def print_tree(self, prefix="", is_last=True):
        c = "└── " if is_last else "├── "
        ext = "    " if is_last else "│   "
        print(prefix + c + "AltList")
        items = []
        for i, seq in enumerate(self.sequences):
            items.append(seq)
            if i < len(self.sequences) - 1:
                items.append(None)
        for i, item in enumerate(items):
            last = (i == len(items) - 1)
            if item is None:
                pipe_c = "└── " if last else "├── "
                print(prefix + ext + pipe_c + "PIPE: '|'")
            else:
                item.print_tree(prefix + ext, is_last=last)


class RuleNode:
    """Rule → NonTerm -> AltList"""

    def __init__(self, head, altlist):
        self.head    = head       # IdentifierNode
        self.altlist = altlist    # AltListNode

    def __repr__(self):
        return f'RuleNode({self.head.value} -> {self.altlist})'

    def __eq__(self, other):
        return (isinstance(other, RuleNode) and
                self.head == other.head and
                self.altlist == other.altlist)

    def print_tree(self, prefix="", is_last=True):
        c = "└── " if is_last else "├── "
        ext = "    " if is_last else "│   "
        print(prefix + c + "Rule")
        self.head.print_tree(prefix + ext, is_last=False)
        print(prefix + ext + "├── ARROW: '->'")
        self.altlist.print_tree(prefix + ext, is_last=True)

    def get_head_name(self):
        return self.head.value

    def get_alternatives(self):
        return self.altlist.sequences


class RuleListNode:
    """Lista de regras da gramática."""

    def __init__(self, rules=None):
        self.rules = rules if rules is not None else []

    def __repr__(self):
        return f'RuleListNode({self.rules})'

    def __eq__(self, other):
        return isinstance(other, RuleListNode) and self.rules == other.rules

    def print_tree(self, prefix="", is_last=True):
        c = "└── " if is_last else "├── "
        ext = "    " if is_last else "│   "
        print(prefix + c + "RuleList")
        for i, rule in enumerate(self.rules):
            rule.print_tree(prefix + ext, is_last=(i == len(self.rules) - 1))


# ---------------------------------------------------------------------------
# Nós intermédios — secção TokenSection (opcional)
# ---------------------------------------------------------------------------

class TokenDeclNode:
    """TokenDecl → TERMINAL_NAME = /regex/"""

    def __init__(self, name, regex):
        self.name  = name   # TerminalNameNode
        self.regex = regex  # RegexNode

    def __repr__(self):
        return f'TokenDecl({self.name.value} : /{self.regex.value}/)'

    def __eq__(self, other):
        return (isinstance(other, TokenDeclNode) and
                self.name == other.name and
                self.regex == other.regex)

    def print_tree(self, prefix="", is_last=True):
        c = "└── " if is_last else "├── "
        ext = "    " if is_last else "│   "
        print(prefix + c + "TokenDecl")
        self.name.print_tree(prefix + ext, is_last=False)
        print(prefix + ext + "├── EQUALS: '='")
        self.regex.print_tree(prefix + ext, is_last=True)


class TokenSectionNode:
    """Secção de declaração de tokens (pode estar vazia)."""

    def __init__(self, decls=None):
        self.decls = decls if decls is not None else []

    def __repr__(self):
        return f'TokenSectionNode({self.decls})'

    def __eq__(self, other):
        return isinstance(other, TokenSectionNode) and self.decls == other.decls

    def print_tree(self, prefix="", is_last=True):
        c = "└── " if is_last else "├── "
        ext = "    " if is_last else "│   "
        print(prefix + c + "TokenSection")
        for i, decl in enumerate(self.decls):
            decl.print_tree(prefix + ext, is_last=(i == len(self.decls) - 1))


# ---------------------------------------------------------------------------
# Nó Axioma
# ---------------------------------------------------------------------------

class AxiomaNode:
    """Axioma → 'start' ':' NonTerm"""

    def __init__(self, nonterm):
        self.nonterm = nonterm  # IdentifierNode

    def __repr__(self):
        return f'AxiomaNode(start: {self.nonterm.value})'

    def __eq__(self, other):
        return isinstance(other, AxiomaNode) and self.nonterm == other.nonterm

    def print_tree(self, prefix="", is_last=True):
        c = "└── " if is_last else "├── "
        ext = "    " if is_last else "│   "
        print(prefix + c + "Axioma")
        print(prefix + ext + "├── KEYWORD: 'start'")
        print(prefix + ext + "├── COLON: ':'")
        self.nonterm.print_tree(prefix + ext, is_last=True)


# ---------------------------------------------------------------------------
# Nó raiz
# ---------------------------------------------------------------------------

class SpecNode:
    """
    Spec → Axioma RuleList TokenSection

    Raiz da ASA. O axioma é declarado explicitamente com 'start: NonTerm'.
    TokenSection pode estar vazia.
    """

    def __init__(self, axioma, rulelist, tokensection):
        self.axioma       = axioma        # AxiomaNode
        self.rulelist     = rulelist      # RuleListNode
        self.tokensection = tokensection  # TokenSectionNode

    def __repr__(self):
        return f'SpecNode(axioma={self.axioma}, rules={self.rulelist}, tokens={self.tokensection})'

    def __eq__(self, other):
        return (isinstance(other, SpecNode) and
                self.axioma == other.axioma and
                self.rulelist == other.rulelist and
                self.tokensection == other.tokensection)

    def print_tree(self):
        print("Spec")
        has_tokens = bool(self.tokensection.decls)
        self.axioma.print_tree(prefix="", is_last=False)
        self.rulelist.print_tree(prefix="", is_last=not has_tokens)
        if has_tokens:
            self.tokensection.print_tree(prefix="", is_last=True)

    def get_start(self):
        """O axioma é declarado explicitamente via 'start: NonTerm'."""
        return self.axioma.nonterm.value

    def get_rules(self):
        return self.rulelist.rules

    def get_nonterminals(self):
        return {r.get_head_name() for r in self.rulelist.rules}

    def get_terminals(self):
        """
        Terminais = nomes declarados na TokenSection
                  + quoted strings usadas inline nas produções.
        """
        declared = {d.name.value for d in self.tokensection.decls}
        inline = set()
        for rule in self.rulelist.rules:
            for seq in rule.altlist.sequences:
                for sym in seq.symbols:
                    if isinstance(sym.child, StringNode):
                        inline.add(sym.get_value())
                    elif isinstance(sym.child, TerminalNameNode):
                        inline.add(sym.get_value())
        return declared | inline

    def get_token_patterns(self):
        """Dicionário TERMINAL_NAME → padrão regex (só os declarados)."""
        return {d.name.value: d.regex.value for d in self.tokensection.decls}