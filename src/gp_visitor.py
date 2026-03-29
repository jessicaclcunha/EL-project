"""
Gerador de Visitor Pattern para a gramática.
"""

import re


def safe_name(nt):
    """Converte nome do NT em nome Python válido."""
    name = nt.replace("'", "_prime")
    return re.sub(r'[^A-Za-z0-9_]', '_', name)


def is_epsilon_seq(seq):
    """Verifica se uma sequência representa a alternativa epsilon."""
    return (
        not seq.symbols or
        (len(seq.symbols) == 1 and seq.symbols[0].get_is_epsilon())
    )


def generate_visitor(grammar):
    """
    Gera código Python de um Visitor para a gramática dada.
    """
    rules = grammar.get_rules()
    start = grammar.get_start()

    lines = []
    w = lines.append

    w('"""')
    w('Visitor para geração de código — gerado pelo Grammar Playground.')
    w('"""')
    w('')
    w('class Visitor:')
    w('    """Classe base — despacha visit_<label>(node) automaticamente."""')
    w('')
    w('    def visit(self, node):')
    w('        """Ponto de entrada: visita um nó da árvore."""')
    w('        if node.lexema is not None:')
    w('            return node.lexema')
    w('        if node.label == "ε":')
    w('            return ""')
    w('        method = getattr(self, "visit_" + node.label, self.generic_visit)')
    w('        return method(node)')
    w('')
    w('    def generic_visit(self, node):')
    w('        """Visita por omissão: concatena resultados dos filhos."""')
    w('        parts = []')
    w('        for child in node.children:')
    w('            r = self.visit(child)')
    w('            if r is not None and str(r) != "":')
    w('                parts.append(str(r))')
    w('        return " ".join(parts)')
    w('')
    w('')
    w('class CodeGen(Visitor):')
    w('    """')
    w('    Visitor de geração de código.')
    w('')
    w('    Personaliza cada método visit_<NT> abaixo.')
    w('    Por omissão, cada um delega para generic_visit.')
    w('    """')
    w('')

    for rule in rules:
        nt = rule.get_head_name()
        seqs = rule.altlist.sequences
        func = safe_name(nt)

        w(f'    def visit_{func}(self, node):')

        for seq in seqs:
            if is_epsilon_seq(seq):
                w(f'        # {nt} → ε')
            else:
                rhs = ' '.join(s.get_value() for s in seq.symbols)
                w(f'        # {nt} → {rhs}')

        w(f'        return self.generic_visit(node)')
        w('')

    return '\n'.join(lines)