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


def _seq_repr(seq):
    """Representação textual de uma sequência de símbolos."""
    if is_epsilon_seq(seq):
        return 'ε'
    return ' '.join(s.get_value() for s in seq.symbols)


def _alt_index_comment(seqs):
    """
    Gera comentários descritivos para cada alternativa, com índices dos filhos.
    Exemplo:
        # Alt 0 — Term ExprR  →  node.children[0]=Term, node.children[1]=ExprR
        # Alt 1 — ε           →  node.children[0].label == 'ε'
    """
    lines = []
    for i, seq in enumerate(seqs):
        if is_epsilon_seq(seq):
            lines.append(f'        # Alt {i} — ε  →  node.children[0].label == "ε"')
        else:
            syms = seq.symbols
            children_desc = ', '.join(
                f'node.children[{j}]={s.get_value()}'
                for j, s in enumerate(syms)
            )
            lines.append(
                f'        # Alt {i} — {_seq_repr(seq)}'
                f'  →  {children_desc}'
            )
    return lines


def _detect_condition(seq, i):
    """
    Gera a condição Python para detetar que a alternativa i foi escolhida.
    Usa o label do primeiro filho e/ou o número total de filhos.
    """
    if is_epsilon_seq(seq):
        return 'node.children[0].label == "ε"'
    first_sym = seq.symbols[0]
    n = len(seq.symbols)
    label = first_sym.get_value()
    return f'len(node.children) == {n} and node.children[0].label == "{label}"'


def generate_visitor(grammar):
    """
    Gera código Python de um Visitor para a gramática dada.

    O esqueleto gerado inclui:
      - Classe base Visitor com dispatch automático
      - Classe CodeGen com um método visit_<NT> por não-terminal
      - Comentários mostrando as alternativas e como aceder a node.children
      - Exemplos de como detetar qual alternativa foi usada
    """
    rules = grammar.get_rules()
    start = grammar.get_start()

    lines = []
    w = lines.append

    # ── Cabeçalho ────────────────────────────────────────────────────────
    w('"""')
    w('Visitor para geração de código — gerado pelo Grammar Playground.')
    w('')
    w('Como usar:')
    w('  1. Cada método visit_<NT>(self, node) recebe um TreeNode.')
    w('  2. node.label     — nome do NT ou tipo do terminal')
    w('  3. node.lexema    — valor do token (só em folhas terminais, ex: "42", "+=")')
    w('  4. node.children  — lista de TreeNode filhos')
    w('  5. self.visit(child) — visita recursiva de um filho')
    w('  6. Por omissão cada método delega em generic_visit, que concatena os filhos.')
    w('"""')
    w('')

    # ── Classe base Visitor ───────────────────────────────────────────────
    w('class Visitor:')
    w('    """Classe base — despacha visit_<label>(node) automaticamente."""')
    w('')
    w('    def visit(self, node):')
    w('        """Ponto de entrada: visita um nó da árvore."""')
    w('        # Folha terminal — devolve o lexema directamente')
    w('        if node.lexema is not None:')
    w('            return node.lexema')
    w('        # Nó épsilon')
    w('        if node.label == "ε":')
    w('            return ""')
    w('        # Despacha para o método específico (ou generic_visit)')
    w('        method = getattr(self, "visit_" + node.label, self.generic_visit)')
    w('        return method(node)')
    w('')
    w('    def generic_visit(self, node):')
    w('        """Visita por omissão: concatena resultados dos filhos com espaço."""')
    w('        parts = []')
    w('        for child in node.children:')
    w('            r = self.visit(child)')
    w('            if r is not None and str(r).strip() != "":')
    w('                parts.append(str(r))')
    w('        return " ".join(parts)')
    w('')
    w('')

    # ── Classe CodeGen ────────────────────────────────────────────────────
    w('class CodeGen(Visitor):')
    w('    """')
    w('    Visitor de geração de código — personalize os métodos abaixo.')
    w('')
    w('    Cada método recebe um TreeNode com:')
    w('      node.label      — nome do NT (ex: "Expr", "Term")')
    w('      node.children   — lista de filhos (TreeNode)')
    w('      node.lexema     — None para NTs; valor do token para terminais')
    w('')
    w('    Para visitar um filho: self.visit(node.children[i])')
    w('    Para obter o lexema de um terminal filho: node.children[i].lexema')
    w('    """')
    w('')

    for rule in rules:
        nt = rule.get_head_name()
        seqs = rule.altlist.sequences
        func = safe_name(nt)
        n_alts = len(seqs)

        w(f'    def visit_{func}(self, node):')

        # Comentários com alternativas e índices dos filhos
        w(f'        # {nt} tem {n_alts} alternativa(s):')
        for comment in _alt_index_comment(seqs):
            w(comment)

        # Se há mais de uma alternativa, gerar bloco if/elif de exemplo
        if n_alts > 1:
            w('        #')
            w('        # Exemplo de como detetar a alternativa escolhida:')

            # Encontrar a alternativa epsilon, se existir
            eps_idx = next(
                (i for i, s in enumerate(seqs) if is_epsilon_seq(s)), None
            )

            first_branch = True
            for i, seq in enumerate(seqs):
                if is_epsilon_seq(seq):
                    continue  # tratada no else/elif final
                cond = _detect_condition(seq, i)
                kw = '#   if' if first_branch else '#   elif'
                first_branch = False
                w(f'        {kw} {cond}:')
                # Gerar acesso a cada filho como comentário
                for j, sym in enumerate(seq.symbols):
                    if sym.get_is_terminal():
                        w(f'        #       tok_{j} = node.children[{j}].lexema  # terminal {sym.get_value()}')
                    else:
                        w(f'        #       val_{j} = self.visit(node.children[{j}])  # {sym.get_value()}')
                w(f'        #       pass  # substitui por: return ...')

            if eps_idx is not None:
                kw = '#   if' if first_branch else '#   else'
                w(f'        {kw}:  # alternativa ε')
                w(f'        #       return ""')
            elif not first_branch:
                w(f'        #   else:')
                w(f'        #       raise ValueError(f"Alternativa desconhecida em {nt}: {{node.children}}")')

        elif n_alts == 1 and not is_epsilon_seq(seqs[0]):
            # Só uma alternativa, não-epsilon: mostrar acesso directo
            seq = seqs[0]
            w('        #')
            w('        # Acesso directo aos filhos:')
            for j, sym in enumerate(seq.symbols):
                if sym.get_is_terminal():
                    w(f'        #   tok_{j} = node.children[{j}].lexema  # terminal {sym.get_value()}')
                else:
                    w(f'        #   val_{j} = self.visit(node.children[{j}])  # {sym.get_value()}')

        w('        return self.generic_visit(node)')
        w('')

    return '\n'.join(lines)