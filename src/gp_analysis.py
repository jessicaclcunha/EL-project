from gp_ast import GrammarNode, SeqNode, SymbolNode


def compute_first(grammar):
    nts = grammar.get_nonterminals()
    first = {nt: set() for nt in nts}

    changed = True
    while changed:
        changed = False
        for rule in grammar.get_rules():
            A = rule.get_head_name()
            for seq in rule.altlist.sequences:
                before = len(first[A])
                _first_of_seq(seq.symbols, first, nts, first[A])
                if len(first[A]) > before:
                    changed = True

    return first


def _first_of_seq(symbols, first_map, nts, result):
    if not symbols:
        result.add('ε')
        return True

    for sym in symbols:
        if sym.get_is_epsilon():
            result.add('ε')
            return True
        elif not sym.get_is_terminal() and sym.get_value() in nts:
            sym_first = first_map.get(sym.get_value(), set())
            result |= (sym_first - {'ε'})
            if 'ε' not in sym_first:
                return False
        else:
            result.add(sym.get_value())
            return False

    result.add('ε')
    return True


def first_of_seq(symbols, first_map, nts):
    result = set()
    _first_of_seq(symbols, first_map, nts, result)
    return result


def compute_follow(grammar, first):
    nts = grammar.get_nonterminals()
    follow = {nt: set() for nt in nts}
    follow[grammar.get_start()].add('$')

    changed = True
    while changed:
        changed = False
        for rule in grammar.get_rules():
            A = rule.get_head_name()
            for seq in rule.altlist.sequences:
                syms = seq.symbols
                for i, sym in enumerate(syms):
                    if sym.get_is_terminal() or sym.get_is_epsilon():
                        continue
                    if sym.get_value() not in nts:
                        continue

                    B = sym.get_value()
                    before = len(follow[B])
                    beta = syms[i + 1:]
                    beta_first = first_of_seq(beta, first, nts)

                    follow[B] |= (beta_first - {'ε'})

                    if 'ε' in beta_first or not beta:
                        follow[B] |= follow[A]

                    if len(follow[B]) > before:
                        changed = True

    return follow


def check_ll1(grammar, first, follow):
    nts = grammar.get_nonterminals()
    conflicts = []

    for rule in grammar.get_rules():
        A = rule.get_head_name()
        seqs = rule.altlist.sequences
        n = len(seqs)
        seq_firsts = [first_of_seq(seq.symbols, first, nts) for seq in seqs]

        for i in range(n):
            for j in range(i + 1, n):
                intersection = (seq_firsts[i] - {'ε'}) & (seq_firsts[j] - {'ε'})
                if intersection:
                    conflicts.append({
                        'type': 'FIRST/FIRST',
                        'nonterminal': A,
                        'alts': (repr(seqs[i]), repr(seqs[j])),
                        'symbols': intersection,
                    })

            if 'ε' in seq_firsts[i]:
                intersection = (seq_firsts[i] - {'ε'}) & follow[A]
                if intersection:
                    conflicts.append({
                        'type': 'FIRST/FOLLOW',
                        'nonterminal': A,
                        'alts': (repr(seqs[i]),),
                        'symbols': intersection,
                    })

    return conflicts


def build_parse_table(grammar, first, follow):
    nts = grammar.get_nonterminals()
    table = {}

    for rule in grammar.get_rules():
        A = rule.get_head_name()
        for seq in rule.altlist.sequences:
            seq_first = first_of_seq(seq.symbols, first, nts)

            for terminal in seq_first - {'ε'}:
                table.setdefault((A, terminal), []).append(seq)

            if 'ε' in seq_first:
                for terminal in follow[A]:
                    table.setdefault((A, terminal), []).append(seq)

    return table


def print_first_follow(first, follow):
    nts = sorted(first.keys())
    print(f"{'NT':<15} {'FIRST':<40} FOLLOW")
    print("─" * 78)
    for nt in nts:
        f  = ', '.join(sorted(first[nt]))
        fw = ', '.join(sorted(follow[nt]))
        print(f"{nt:<15} {{ {f:<38}}} {{ {fw} }}")


def print_conflicts(conflicts):
    if not conflicts:
        print("✓ A gramática É LL(1) — sem conflitos.")
        return

    print(f"✗ A gramática NÃO é LL(1) — {len(conflicts)} conflito(s) encontrado(s):\n")
    for i, c in enumerate(conflicts, 1):
        print(f"  [{i}] Conflito {c['type']} em  {c['nonterminal']}")
        for alt in c['alts']:
            print(f"       Produção: {c['nonterminal']} → {alt}")
        print(f"       Símbolos em conflito: {c['symbols']}")
        print()


def print_parse_table(table, grammar):
    nts   = sorted(grammar.get_nonterminals())
    terms = sorted(grammar.get_terminals() | {'$'})

    col_w = max(12, max(len(t) for t in terms) + 2)
    row_w = max(len(nt) for nt in nts) + 2

    header = f"{'':>{row_w}}" + ''.join(f"{t:^{col_w}}" for t in terms)
    print(header)
    print("─" * len(header))

    for nt in nts:
        row = f"{nt:>{row_w}}"
        for t in terms:
            cell = table.get((nt, t), [])
            if not cell:
                row += f"{'':^{col_w}}"
            elif len(cell) == 1:
                s = f"{nt}→{repr(cell[0])}"
                if len(s) > col_w - 1:
                    s = s[:col_w - 4] + '...'
                row += f"{s:^{col_w}}"
            else:
                row += f"{'[CONFLITO]':^{col_w}}"
        print(row)