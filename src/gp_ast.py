class IdentifierNode:
    """IDENTIFIER — nome de um não-terminal."""

    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return f'IDENTIFIER: "{self.value}"'

    def __eq__(self, other):
        if not isinstance(other, IdentifierNode):
            return False
        return self.value == other.value

    def print_tree(self, prefix="", is_last=True):
        c = "└── " if is_last else "├── "
        print(prefix + c + repr(self))


class QuotedStringNode:
    """QUOTED_STRING — terminal entre aspas simples."""

    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return f'QUOTED_STRING: "{self.value}"'

    def __eq__(self, other):
        if not isinstance(other, QuotedStringNode):
            return False
        return self.value == other.value

    def print_tree(self, prefix="", is_last=True):
        c = "└── " if is_last else "├── "
        print(prefix + c + repr(self))


class EpsilonNode:
    """EPSILON — símbolo ε."""

    def __repr__(self):
        return 'EPSILON: "ε"'

    def __eq__(self, other):
        return isinstance(other, EpsilonNode)

    def print_tree(self, prefix="", is_last=True):
        c = "└── " if is_last else "├── "
        print(prefix + c + repr(self))


class NewlineNode:
    """NEWLINE — uma ou mais quebras de linha."""

    def __repr__(self):
        return 'NEWLINE'

    def __eq__(self, other):
        return isinstance(other, NewlineNode)

    def print_tree(self, prefix="", is_last=True):
        c = "└── " if is_last else "├── "
        print(prefix + c + repr(self))


# ---------------------------------------------------------------------------
# Nós intermédios
# ---------------------------------------------------------------------------

class NonTermNode:
    """NonTerm → identifier"""

    def __init__(self, identifier):
        self.identifier = identifier

    def __repr__(self):
        return f'NonTermNode(identifier={self.identifier})'

    def __eq__(self, other):
        if not isinstance(other, NonTermNode):
            return False
        return self.identifier == other.identifier

    def print_tree(self, prefix="", is_last=True):
        c = "└── " if is_last else "├── "
        ext = "    " if is_last else "│   "
        print(prefix + c + "NonTerm")
        self.identifier.print_tree(prefix + ext, is_last=True)


class TermNode:
    """Term → quoted_string"""

    def __init__(self, quoted):
        self.quoted = quoted

    def __repr__(self):
        return f'TermNode(quoted={self.quoted})'

    def __eq__(self, other):
        if not isinstance(other, TermNode):
            return False
        return self.quoted == other.quoted

    def print_tree(self, prefix="", is_last=True):
        c = "└── " if is_last else "├── "
        ext = "    " if is_last else "│   "
        print(prefix + c + "Term")
        self.quoted.print_tree(prefix + ext, is_last=True)


class SymbolNode:
    """Symbol → NonTerm | Term | 'ε'"""

    def __init__(self, child):
        self.child = child

    def __repr__(self):
        return f'SymbolNode(child={self.child})'

    def __eq__(self, other):
        if not isinstance(other, SymbolNode):
            return False
        return self.child == other.child

    def print_tree(self, prefix="", is_last=True):
        c = "└── " if is_last else "├── "
        ext = "    " if is_last else "│   "
        print(prefix + c + "Symbol")
        self.child.print_tree(prefix + ext, is_last=True)

    def get_value(self):
        if isinstance(self.child, NonTermNode):
            return self.child.identifier.value
        elif isinstance(self.child, TermNode):
            return self.child.quoted.value
        else:
            return 'ε'

    def get_is_terminal(self):
        return not isinstance(self.child, NonTermNode)

    def get_is_epsilon(self):
        return isinstance(self.child, EpsilonNode)


class SeqNode:
    """Seq → Symbol Seq | ε"""

    def __init__(self, symbols=None):
        self.symbols = symbols if symbols is not None else []

    def __repr__(self):
        return f'SeqNode(symbols={self.symbols})'

    def __eq__(self, other):
        if not isinstance(other, SeqNode):
            return False
        return self.symbols == other.symbols

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
    """AltList → Seq '|' AltList | Seq"""

    def __init__(self, sequences=None):
        self.sequences = sequences if sequences is not None else []

    def __repr__(self):
        return f'AltListNode(sequences={self.sequences})'

    def __eq__(self, other):
        if not isinstance(other, AltListNode):
            return False
        return self.sequences == other.sequences

    def print_tree(self, prefix="", is_last=True):
        c = "└── " if is_last else "├── "
        ext = "    " if is_last else "│   "
        print(prefix + c + "AltList")

        # intercalar PIPE entre sequências
        items = []
        for i, seq in enumerate(self.sequences):
            items.append(seq)
            if i < len(self.sequences) - 1:
                items.append(None)  # PIPE

        for i, item in enumerate(items):
            last = (i == len(items) - 1)
            if item is None:
                pipe_c = "└── " if last else "├── "
                print(prefix + ext + pipe_c + "PIPE: '|'")
            else:
                item.print_tree(prefix + ext, is_last=last)


class RuleNode:
    """Rule → NonTerm '→' AltList Newline"""

    def __init__(self, head, altlist, newline=None):
        self.head    = head
        self.altlist = altlist
        self.newline = newline if newline is not None else NewlineNode()

    def __repr__(self):
        return f'RuleNode(head={self.head}, altlist={self.altlist})'

    def __eq__(self, other):
        if not isinstance(other, RuleNode):
            return False
        return self.head == other.head and self.altlist == other.altlist

    def print_tree(self, prefix="", is_last=True):
        c = "└── " if is_last else "├── "
        ext = "    " if is_last else "│   "
        print(prefix + c + "Rule")
        self.head.print_tree(prefix + ext, is_last=False)
        print(prefix + ext + "├── ARROW: '→'")
        self.altlist.print_tree(prefix + ext, is_last=False)
        self.newline.print_tree(prefix + ext, is_last=True)

    def get_head_name(self):
        return self.head.identifier.value

    def get_alternatives(self):
        return self.altlist.sequences


class RuleListNode:
    """RuleList → Rule RuleList | Rule"""

    def __init__(self, rules=None):
        self.rules = rules if rules is not None else []

    def __repr__(self):
        return f'RuleListNode(rules={self.rules})'

    def __eq__(self, other):
        if not isinstance(other, RuleListNode):
            return False
        return self.rules == other.rules

    def print_tree(self, prefix="", is_last=True):
        c = "└── " if is_last else "├── "
        ext = "    " if is_last else "│   "
        print(prefix + c + "RuleList")
        for i, rule in enumerate(self.rules):
            rule.print_tree(prefix + ext, is_last=(i == len(self.rules) - 1))


class GrammarNode:
    """Grammar → 'start:' NonTerm Newline RuleList"""

    def __init__(self, start_nonterm, rulelist):
        self.start_nonterm = start_nonterm
        self.rulelist      = rulelist

    def __repr__(self):
        return f'GrammarNode(start_nonterm={self.start_nonterm}, rulelist={self.rulelist})'

    def __eq__(self, other):
        if not isinstance(other, GrammarNode):
            return False
        return self.start_nonterm == other.start_nonterm and self.rulelist == other.rulelist

    def print_tree(self):
        print("Grammar")
        print("├── START_KW: 'start:'")
        self.start_nonterm.print_tree(prefix="", is_last=False)
        NewlineNode().print_tree(prefix="", is_last=False)
        self.rulelist.print_tree(prefix="", is_last=True)

    def get_start(self):
        return self.start_nonterm.identifier.value

    def get_rules(self):
        return self.rulelist.rules

    def get_nonterminals(self):
        return {r.get_head_name() for r in self.rulelist.rules}

    def get_terminals(self):
        nts = self.get_nonterminals()
        terminals = set()
        for rule in self.rulelist.rules:
            for seq in rule.altlist.sequences:
                for sym in seq.symbols:
                    if sym.get_is_terminal() and not sym.get_is_epsilon():
                        terminals.add(sym.get_value())
                    elif not sym.get_is_terminal() and sym.get_value() not in nts:
                        terminals.add(sym.get_value())
        return terminals