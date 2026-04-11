"""
Gerador de Visitor Pattern para a gramática.
"""

import re
from collections import Counter


def safe_name(nt):
    name = nt.replace("'", "_prime")
    return re.sub(r'[^A-Za-z0-9_]', '_', name)


def is_epsilon_seq(seq):
    """Verifica se uma sequência representa a alternativa epsilon."""
    return (
        not seq.symbols or
        (len(seq.symbols) == 1 and seq.symbols[0].get_is_epsilon())
    )


def _seq_repr(seq):
    if is_epsilon_seq(seq):
        return 'ε'
    return ' '.join(s.get_value() for s in seq.symbols)


def _make_var_names(symbols):
    """
    Atribui nomes de variável semânticos a cada símbolo de uma sequência.

    Regras:
      - Terminal declarado (ex: PLUS, ASSIGN) → nome em minúsculas (ex: plus, assign)
      - Terminal inline (ex: '(', ':=')       → conteúdo alfanumérico ou 'tok'
      - Não-terminal (ex: Expr, StmtListR)    → snake_case (ex: expr, stmt_list_r)
      - Colisões                              → sufixo numérico (expr1, expr2, …)

    Devolve lista de strings com um nome por símbolo.
    """
    raw = []
    for sym in symbols:
        val = sym.get_value()
        if sym.get_is_terminal():
            # Strings inline como '(' ou ':=' → nome genérico baseado no conteúdo
            if val.startswith(("'", '"')):
                inner = val[1:-1]
                clean = re.sub(r'[^A-Za-z0-9]', '', inner)
                base  = clean.lower() if clean else 'tok'
            else:
                base = val.lower()
        else:
            # Não-terminal: PascalCase / camelCase → snake_case
            s    = val.replace("'", "_prime")
            s    = re.sub(r'(?<=[a-z0-9])([A-Z])', r'_\1', s)
            base = s.lower()
        raw.append(base)

    # Resolver colisões com sufixo numérico
    counts = Counter(raw)
    seen   = Counter()
    result = []
    for name in raw:
        if counts[name] > 1:
            seen[name] += 1
            result.append(f'{name}{seen[name]}')
        else:
            result.append(name)
    return result


def _alt_detect_condition(seq):
    """
    Condição Python legível para detetar que esta alternativa foi expandida.
    Combina o label do primeiro filho com o número total de filhos.
    """
    if is_epsilon_seq(seq):
        return 'node.children[0].label == "ε"'
    first_sym = seq.symbols[0]
    n         = len(seq.symbols)
    label     = first_sym.get_value()
    # Para terminais inline, o label na árvore é o conteúdo sem aspas
    if label.startswith(("'", '"')):
        label = label[1:-1]
    return f'len(node.children) == {n} and node.children[0].label == "{label}"'


def _gen_bindings(symbols, var_names, indent):
    """
    Gera linhas de código que vinculam variáveis com nomes semânticos
    aos filhos corretos do nó.

      Terminais  → var = node.children[i].lexema      (valor do token)
      NTs        → var = self.visit(node.children[i]) (resultado recursivo)
    """
    lines = []
    pad = ' ' * indent
    for i, (sym, var) in enumerate(zip(symbols, var_names)):
        val = sym.get_value()
        if sym.get_is_terminal():
            lines.append(
                f'{pad}{var} = node.children[{i}].lexema'
                f'  # terminal {val}'
            )
        else:
            lines.append(
                f'{pad}{var} = self.visit(node.children[{i}])'
                f'  # {val}'
            )
    return lines


def generate_visitor(grammar):
    rules = grammar.get_rules()

    lines = []
    w = lines.append

    # ── Cabeçalho ─────────────────────────────────────────────────────
    w('"""')
    w('Visitor para geração de código — gerado pelo Grammar Playground.')
    w('')
    w('COMO USAR')
    w('─────────')
    w('Cada método visit_<NT>(self, node) já vincula os filhos a variáveis')
    w('com nomes semânticos. Basta substituir o "return ..." pelo resultado')
    w('pretendido.')
    w('')
    w('  Terminais  →  variável contém o lexema (string),  ex: plus = "+"')
    w('  NTs        →  variável contém o resultado de self.visit(...)')
    w('')
    w('Exemplo para  Expr -> Term ExprR :')
    w('    def visit_Expr(self, node):')
    w('        term, expr_r = self.bind(node, "term", "expr_r")')
    w('        return term + expr_r   # ← lógica de negócio')
    w('"""')
    w('')

    # ── Classe base Visitor ───────────────────────────────────────────
    w('class Visitor:')
    w('    """Classe base com dispatch automático e helper bind()."""')
    w('')
    w('    def visit(self, node):')
    w('        """Visita um nó: despacha para visit_<NT> ou generic_visit."""')
    w('        if node.lexema is not None:          # folha terminal')
    w('            return node.lexema')
    w('        if node.label == "\u03b5":                # nó epsilon')
    w('            return ""')
    w('        method = getattr(self, "visit_" + node.label, self.generic_visit)')
    w('        return method(node)')
    w('')
    w('    def generic_visit(self, node):')
    w('        """Fallback: concatena resultados dos filhos separados por espaço."""')
    w('        parts = []')
    w('        for child in node.children:')
    w('            r = self.visit(child)')
    w('            if r is not None and str(r).strip():')
    w('                parts.append(str(r))')
    w('        return " ".join(parts)')
    w('')
    w('    def bind(self, node, *names):')
    w('        """')
    w('        Vincula os filhos de *node* a variáveis com nomes semânticos.')
    w('')
    w('        Para cada filho i:')
    w('          • filho terminal  →  devolve node.children[i].lexema  (string)')
    w('          • filho NT        →  devolve self.visit(node.children[i])')
    w('          • filho ε         →  devolve ""')
    w('')
    w('        Uso:')
    w('            left, op, right = self.bind(node, "left", "op", "right")')
    w('        """')
    w('        if len(names) != len(node.children):')
    w('            raise ValueError(')
    w('                f"bind: {len(names)} nome(s) para {len(node.children)}"')
    w('                f" filho(s) em \'{node.label}\'"')
    w('            )')
    w('        result = []')
    w('        for child in node.children:')
    w('            if child.label == "\u03b5":')
    w('                result.append("")')
    w('            elif child.lexema is not None:')
    w('                result.append(child.lexema)')
    w('            else:')
    w('                result.append(self.visit(child))')
    w('        return result')
    w('')
    w('')

    # ── Classe CodeGen ────────────────────────────────────────────────
    w('class CodeGen(Visitor):')
    w('    """')
    w('    Visitor de geração de código.')
    w('')
    w('    Cada método já vincula os filhos às variáveis semânticas.')
    w('    Substitui o corpo do return pela lógica pretendida.')
    w('    """')
    w('')

    for rule in rules:
        nt     = rule.get_head_name()
        seqs   = rule.altlist.sequences
        func   = safe_name(nt)
        n_alts = len(seqs)

        # Separador visual e assinatura da regra
        w(f'    # {"─" * 58}')
        alts_summary = '  |  '.join(
            'ε' if is_epsilon_seq(s)
            else ' '.join(sym.get_value() for sym in s.symbols)
            for s in seqs
        )
        w(f'    # {nt}  →  {alts_summary}')
        w(f'    def visit_{func}(self, node):')

        if n_alts == 1:
            seq = seqs[0]
            if is_epsilon_seq(seq):
                w(f'        # Alternativa única: ε — sem filhos significativos.')
                w(f'        return ""')
            else:
                # Única alternativa: vinculações directas + dica com bind()
                var_names = _make_var_names(seq.symbols)
                # via bind()
                names_repr = ', '.join(f'"{v}"' for v in var_names)
                vars_repr  = ', '.join(var_names)
                w(f'        # Vincula os filhos a variáveis semânticas:')
                w(f'        {vars_repr} = self.bind(node, {names_repr})')
                w(f'')
                # Alternativa manual (mais explícita), comentada
                w(f'        # Equivalente explícito:')
                for line in _gen_bindings(seq.symbols, var_names, indent=8):
                    w(f'        #   {line.lstrip()}')
                w(f'')
                ret_hint = ' + '.join(var_names) if len(var_names) <= 4 \
                           else var_names[0]
                w(f'        # ↓ Substitui pelo resultado pretendido')
                w(f'        return self.generic_visit(node)  # ex: return {ret_hint}')

        else:
            # Múltiplas alternativas
            eps_idx = next(
                (i for i, s in enumerate(seqs) if is_epsilon_seq(s)), None
            )

            first_branch = True
            for i, seq in enumerate(seqs):
                if is_epsilon_seq(seq):
                    continue

                cond      = _alt_detect_condition(seq)
                kw        = 'if' if first_branch else 'elif'
                alt_label = _seq_repr(seq)
                first_branch = False

                w(f'        {kw} {cond}:')
                w(f'            # Alternativa: {nt} → {alt_label}')

                var_names  = _make_var_names(seq.symbols)
                names_repr = ', '.join(f'"{v}"' for v in var_names)
                vars_repr  = ', '.join(var_names)
                w(f'            {vars_repr} = self.bind(node, {names_repr})')

                ret_hint = ' + '.join(var_names) if len(var_names) <= 4 \
                           else var_names[0]
                w(f'            # ↓ Substitui pelo resultado pretendido')
                w(f'            return self.generic_visit(node)  # ex: return {ret_hint}')
                w(f'')

            if eps_idx is not None:
                kw = 'if' if first_branch else 'else'
                w(f'        {kw}:  # Alternativa: {nt} → ε')
                w(f'            return ""')
            elif not first_branch:
                w(f'        else:')
                w(f'            raise ValueError(')
                w(f'                f"visit_{func}: alternativa desconhecida '
                  f'(filhos={{[c.label for c in node.children]}})"')
                w(f'            )')

        w(f'')

    return '\n'.join(lines)