from gp_ast import SpecNode, SeqNode, SymbolNode


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
                    if 'ε' in beta_first:
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

        # 1. Conflito FIRST/FIRST: duas alternativas com terminais em comum
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

        # 2. Conflito FIRST/FOLLOW: alternativa anulável cujo FOLLOW
        #    interseta com o FIRST de outra alternativa
        for i in range(n):
            if 'ε' in seq_firsts[i]:
                all_other_firsts = set()
                for j in range(n):
                    if j != i:
                        all_other_firsts |= (seq_firsts[j] - {'ε'})
                intersection = follow[A] & all_other_firsts
                if intersection:
                    conflicts.append({
                        'type': 'FIRST/FOLLOW',
                        'nonterminal': A,
                        'alts': (repr(seqs[i]),),
                        'symbols': intersection,
                    })

        # 3. Múltiplas alternativas anuláveis: se mais de uma alternativa
        #    pode derivar ε, há conflito para todos os tokens do FOLLOW
        nullable_indices = [i for i in range(n) if 'ε' in seq_firsts[i]]
        if len(nullable_indices) > 1 and follow[A]:
            conflicts.append({
                'type': 'FIRST/FOLLOW',
                'nonterminal': A,
                'alts': tuple(repr(seqs[i]) for i in nullable_indices),
                'symbols': follow[A].copy(),
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
                cell = table.setdefault((A, terminal), [])
                if not any(s is seq for s in cell):
                    cell.append(seq)
            if 'ε' in seq_first:
                for terminal in follow[A]:
                    cell = table.setdefault((A, terminal), [])
                    if not any(s is seq for s in cell):
                        cell.append(seq)
    return table


def print_first_follow(first, follow):
    nts = sorted(first.keys())
    if not nts:
        return

    w_nt = max([len(nt) for nt in nts] + [2]) + 4
    w_f  = max([len(', '.join(sorted(first[nt]))) for nt in nts] + [10] ) + 4

    header = f"{'NT':<{w_nt}} {'FIRST':<{w_f + 8}} FOLLOW"
    print(header)
    
    print("─" * (len(header) + 30))
    for nt in nts:
        f  = ', '.join(sorted(first[nt]))
        fw = ', '.join(sorted(follow[nt]))
        print(f"{nt:<{w_nt}} {{ {f:<{w_f}} }} {{ {fw} }}")
    print()


def print_conflicts(conflicts):
    if not conflicts:
        print("✓ A gramática É LL(1) — sem conflitos.")
        return
    print(f"✗ A gramática NÃO é LL(1) — {len(conflicts)} conflito(s) encontrado(s):\n")
    for i, c in enumerate(conflicts, 1):
        print(f"  [{i}] Conflito {c['type']} em  {c['nonterminal']}")
        for alt in c['alts']:
            print(f"       Produção: {c['nonterminal']} → {alt}")
        print(f"       Símbolos em conflito: {{ {', '.join(sorted(c['symbols']))} }}")
        print()


def print_lookahead(grammar, first, follow):
    """Mostra o lookahead calculado para cada alternativa de cada NT."""
    nts = grammar.get_nonterminals()
    print(f"{'NT':<15} {'Produção':<35} {'Lookahead'}")
    print("─" * 78)
    for rule in grammar.get_rules():
        A = rule.get_head_name()
        for seq in rule.altlist.sequences:
            sf = first_of_seq(seq.symbols, first, nts)
            prod_str = f"{A} → {repr(seq)}"

            # Lookahead efetivo: FIRST da alternativa (sem ε), mais FOLLOW se anulável
            lookahead = sf - {'ε'}
            if 'ε' in sf:
                lookahead |= follow[A]

            la_str = ', '.join(sorted(lookahead))
            nullable_mark = '  (anulável → usa FOLLOW)' if 'ε' in sf else ''
            print(f"{A:<15} {prod_str:<35} {{ {la_str} }}{nullable_mark}")


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


def _seq_to_str(symbols):
    return ' '.join(s.get_value() for s in symbols) if symbols else 'ε'

def _get_first_symbol(seq):
    if seq.symbols:
        return seq.symbols[0].get_value()
    return None

def left_factor(rule_name, sequences):
    groups = {}
    for seq in sequences:
        first_sym = _get_first_symbol(seq)
        key = first_sym if first_sym else 'ε'
        groups.setdefault(key, []).append(seq)
    new_rules = []
    single = []
    factored = []
    prime_counter = [0]
    def next_prime():
        prime_counter[0] += 1
        return rule_name + ("'" * prime_counter[0])
    for key, seqs in groups.items():
        if len(seqs) == 1:
            single.append(_seq_to_str(seqs[0].symbols))
        else:
            prefix = _longest_common_prefix(seqs)
            prefix_str = ' '.join(s.get_value() for s in prefix)
            remainders = []
            for seq in seqs:
                rest = seq.symbols[len(prefix):]
                remainders.append(_seq_to_str(rest) if rest else 'ε')
            prime_name = next_prime()
            factored.append((prefix_str, prime_name, remainders))
    main_alts = single[:]
    for prefix_str, prime_name, _ in factored:
        main_alts.append(f"{prefix_str} {prime_name}")
    new_rules.append(f"{rule_name} -> {' | '.join(main_alts)}")
    for _, prime_name, remainders in factored:
        new_rules.append(f"{prime_name} -> {' | '.join(remainders)}")
    return new_rules

def _longest_common_prefix(sequences):
    if not sequences:
        return []
    min_len = min(len(seq.symbols) for seq in sequences)
    prefix = []
    for i in range(min_len):
        val = sequences[0].symbols[i].get_value()
        if all(seq.symbols[i].get_value() == val for seq in sequences):
            prefix.append(sequences[0].symbols[i])
        else:
            break
    return prefix

def eliminate_left_recursion(rule_name, sequences):
    prime = f"{rule_name}'"
    recursive = []
    nonrecursive = []
    for seq in sequences:
        if seq.symbols and seq.symbols[0].get_value() == rule_name:
            recursive.append(seq)
        else:
            nonrecursive.append(seq)
    if not recursive:
        return None
    new_rules = []
    base_alts = [f"{_seq_to_str(seq.symbols)} {prime}" for seq in nonrecursive]
    new_rules.append(f"{rule_name} -> {' | '.join(base_alts)}")
    rec_alts = [f"{_seq_to_str(seq.symbols[1:])} {prime}" for seq in recursive]
    rec_alts.append('ε')
    new_rules.append(f"{prime} -> {' | '.join(rec_alts)}")
    return new_rules

def suggest_fixes(grammar, conflicts):
    if not conflicts:
        return []
    suggestions = []
    seen = set()
    for c in conflicts:
        A = c['nonterminal']
        if A in seen:
            continue
        seen.add(A)
        rule = next(r for r in grammar.get_rules() if r.get_head_name() == A)
        seqs = rule.altlist.sequences
        if c['type'] == 'FIRST/FIRST':
            result = eliminate_left_recursion(A, seqs)
            if result:
                suggestions.append({'nonterminal': A, 'type': 'FIRST/FIRST', 'technique': 'Eliminação de recursividade à esquerda', 'new_rules': result})
            else:
                new_rules = left_factor(A, seqs)
                original = f"{A} -> {' | '.join(_seq_to_str(s.symbols) for s in seqs)}"
                if len(new_rules) == 1 and new_rules[0] == original:
                    suggestions.append({'nonterminal': A, 'type': 'FIRST/FIRST', 'technique': 'Sem correção automática possível', 'new_rules': ['⚠  A gramática pode ser intrinsecamente ambígua neste não-terminal.']})
                else:
                    suggestions.append({'nonterminal': A, 'type': 'FIRST/FIRST', 'technique': 'Fatorização à esquerda', 'new_rules': new_rules})
        elif c['type'] == 'FIRST/FOLLOW':
            result = eliminate_left_recursion(A, seqs)
            if result:
                suggestions.append({'nonterminal': A, 'type': 'FIRST/FOLLOW', 'technique': 'Eliminação de recursividade à esquerda', 'new_rules': result})
            else:
                new_rules = left_factor(A, seqs)
                original = f"{A} -> {' | '.join(_seq_to_str(s.symbols) for s in seqs)}"
                if len(new_rules) == 1 and new_rules[0] == original:
                    suggestions.append({'nonterminal': A, 'type': 'FIRST/FOLLOW', 'technique': 'Sem correção automática possível', 'new_rules': ['⚠  Conflito FIRST/FOLLOW sem prefixo comum — a gramática pode ser intrinsecamente ambígua.']})
                else:
                    suggestions.append({'nonterminal': A, 'type': 'FIRST/FOLLOW', 'technique': 'Fatorização à esquerda (prefixo anulável)', 'new_rules': new_rules})
    return suggestions

def print_suggestions(suggestions):
    if not suggestions:
        return
    print(f"\n{'─' * 60}")
    print(" SUGESTÕES DE CORREÇÃO")
    print(f"{'─' * 60}\n")
    for s in suggestions:
        print(f"  Não-terminal : {s['nonterminal']}")
        print(f"  Conflito     : {s['type']}")
        print(f"  Técnica      : {s['technique']}")
        print(f"  Regras novas :")
        for rule in s['new_rules']:
            print(f"    {rule}")
        print()