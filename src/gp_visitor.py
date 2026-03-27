"""
Gerador de Visitor Pattern para a gramática.

Dado um SpecNode, gera código Python com:
  - Classe Visitor base (despacho automático visit_<NT>)
  - Classe CodeGen com um método visit_<NT> por não-terminal
  - Comentários detalhados com produções e mapeamento de filhos

O utilizador personaliza os métodos visit_<NT> para gerar código.

Uso:
    from gp_visitor import generate_visitor
    code = generate_visitor(grammar)
"""

import re


def _safe_name(nt):
    """Converte nome do NT em nome Python válido: Expr' → Expr_prime."""
    name = nt.replace("'", "_prime")
    return re.sub(r'[^A-Za-z0-9_]', '_', name)


def generate_visitor(grammar):
    """
    Gera código Python de um Visitor para a gramática dada.

    Parâmetros:
        grammar : SpecNode — gramática parseada

    Devolve:
        str — código Python com Visitor base + CodeGen
    """
    rules = grammar.get_rules()
    start = grammar.get_start()

    lines = []
    w = lines.append

    # ── Cabeçalho ─────────────────────────────────────────────────
    w('"""')
    w('Visitor para geração de código — gerado pelo Grammar Playground.')
    w('')
    w('Estrutura da árvore (TreeNode):')
    w('    node.label    — nome do NT ou tipo do terminal')
    w('    node.children — lista de filhos (TreeNode)')
    w('    node.lexema   — valor do token (só em folhas terminais)')
    w('')
    w('Personaliza os métodos visit_<NT> da classe CodeGen')
    w('para implementar a tradução desejada.')
    w('"""')
    w('')
    w('')

    # ── Classe Visitor base ───────────────────────────────────────
    w('class Visitor:')
    w('    """Classe base — despacha visit_<label>(node) automaticamente."""')
    w('')
    w('    def visit(self, node):')
    w('        """Ponto de entrada: visita um nó da árvore."""')
    w('        # Terminais (folhas) — devolver o lexema')
    w('        if node.lexema is not None:')
    w('            return node.lexema')
    w('        # Epsilon — devolver string vazia')
    w('        if node.label == "ε":')
    w('            return ""')
    w('        # Não-terminal — despachar para visit_<NT>')
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

    # ── Classe CodeGen ────────────────────────────────────────────
    w('class CodeGen(Visitor):')
    w('    """')
    w('    Visitor de geração de código.')
    w('')
    w('    Personaliza cada método visit_<NT> abaixo.')
    w('    Por omissão, cada um delega para generic_visit')
    w('    (que concatena os resultados dos filhos).')
    w('    """')
    w('')

    for rule in rules:
        nt = rule.get_head_name()
        seqs = rule.altlist.sequences
        func = _safe_name(nt)

        w(f'    def visit_{func}(self, node):')

        # Listar as produções como comentários
        for seq in seqs:
            is_eps = _is_epsilon_seq(seq)
            if is_eps:
                w(f'        # {nt} → ε')
            else:
                rhs = ' '.join(s.get_value() for s in seq.symbols)
                w(f'        # {nt} → {rhs}')

        # Gerar corpo dependendo da estrutura
        has_eps = any(_is_epsilon_seq(s) for s in seqs)
        non_eps = [s for s in seqs if not _is_epsilon_seq(s)]

        if len(seqs) == 1 and _is_epsilon_seq(seqs[0]):
            # Só epsilon
            w(f'        return ""')

        elif len(seqs) == 1:
            # Uma única produção — mostrar mapeamento dos filhos
            seq = seqs[0]
            w(f'        #')
            for i, sym in enumerate(seq.symbols):
                val = sym.get_value()
                if sym.get_is_terminal():
                    w(f'        # children[{i}] → {val}  (terminal → node.children[{i}].lexema)')
                else:
                    w(f'        # children[{i}] → {val}  (não-terminal)')
            w(f'        return self.generic_visit(node)')

        elif has_eps:
            # Alternativas com epsilon — verificar primeiro
            w(f'        #')
            w(f'        # Verificar se foi a alternativa ε:')
            w(f'        if node.children[0].label == "ε":')
            w(f'            return ""')

            if len(non_eps) == 1:
                # Uma alternativa + epsilon
                seq = non_eps[0]
                w(f'        #')
                for i, sym in enumerate(seq.symbols):
                    val = sym.get_value()
                    if sym.get_is_terminal():
                        w(f'        # children[{i}] → {val}  (terminal)')
                    else:
                        w(f'        # children[{i}] → {val}  (não-terminal)')
            w(f'        return self.generic_visit(node)')

        else:
            # Múltiplas alternativas sem epsilon
            w(f'        #')
            w(f'        # Múltiplas alternativas — inspecionar children[0].label')
            w(f'        # para determinar qual produção foi usada.')
            w(f'        return self.generic_visit(node)')

        w('')

    # ── Exemplo de uso ────────────────────────────────────────────
    w('')
    w('# ── Exemplo de uso ──────────────────────────────────────────')
    w('#')
    w('#   visitor = CodeGen()')
    w('#   resultado = visitor.visit(arvore)   # arvore = TreeNode')
    w('#   print(resultado)')
    w('')

    return '\n'.join(lines)


def _is_epsilon_seq(seq):
    """Verifica se uma sequência representa a alternativa epsilon."""
    return (
        not seq.symbols or
        (len(seq.symbols) == 1 and seq.symbols[0].get_is_epsilon())
    )