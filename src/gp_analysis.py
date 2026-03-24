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


def longest_common_prefix_syms(sequences):
    """Devolve lista de valores (str) do prefixo comum mais longo entre as sequências."""
    if not sequences:
        return []
    min_len = min(len(seq) for seq in sequences)
    prefix = []
    for i in range(min_len):
        val = sequences[0][i]
        if all(seq[i] == val for seq in sequences):
            prefix.append(val)
        else:
            break
    return prefix


def left_factor_recursive(rule_name, alt_lists, prime_counter):
    """
    alt_lists: lista de listas de str (símbolos de cada alternativa).
    Devolve lista de strings "NT -> alt1 | alt2 | ..." prontas a inserir na gramática.
    Fatoriza recursivamente até não haver prefixo comum.
    """
    # Agrupar por primeiro símbolo
    groups = {}
    for syms in alt_lists:
        key = syms[0] if syms else 'ε'
        groups.setdefault(key, []).append(syms)

    new_rules = []
    main_alts = []

    for key, group in groups.items():
        if len(group) == 1:
            s = ' '.join(group[0]) if group[0] else 'ε'
            main_alts.append(s)
        else:
            prefix = longest_common_prefix_syms(group)
            if not prefix:
                for syms in group:
                    s = ' '.join(syms) if syms else 'ε'
                    main_alts.append(s)
                continue

            prime_counter[0] += 1
            prime_name = rule_name + "'" * prime_counter[0]

            prefix_str = ' '.join(prefix)
            main_alts.append(f"{prefix_str} {prime_name}")

            remainders = []
            for syms in group:
                rest = syms[len(prefix):]
                remainders.append(rest if rest else [])  # [] = ε

            # Verificar se os restos ainda têm conflito → fatorizar recursivamente
            # Agrupar restos por primeiro símbolo para detetar se há prefixo
            rem_groups = {}
            for r in remainders:
                k = r[0] if r else 'ε'
                rem_groups.setdefault(k, []).append(r)

            needs_more = any(len(v) > 1 for v in rem_groups.values())

            if needs_more:
                sub_rules = left_factor_recursive(prime_name, remainders, prime_counter)
                new_rules.extend(sub_rules)
            else:
                rem_strs = [' '.join(r) if r else 'ε' for r in remainders]
                new_rules.append(f"{prime_name} -> {' | '.join(rem_strs)}")

    new_rules.insert(0, f"{rule_name} -> {' | '.join(main_alts)}")
    return new_rules


def left_factor(rule_name, sequences):
    """
    Ponto de entrada para fatorização à esquerda.
    sequences: lista de SeqNode
    """
    # Converter SeqNode → lista de str
    alt_lists = []
    for seq in sequences:
        if not seq.symbols or (len(seq.symbols) == 1 and seq.symbols[0].get_is_epsilon()):
            alt_lists.append([])  # ε
        else:
            alt_lists.append([s.get_value() for s in seq.symbols])

    prime_counter = [0]
    return left_factor_recursive(rule_name, alt_lists, prime_counter)


def has_left_recursion(rule_name, sequences):
    return any(
        seq.symbols and seq.symbols[0].get_value() == rule_name
        for seq in sequences
    )


def has_any_direct_left_recursion(grammar):
    """Retorna True se qualquer regra tem recursividade à esquerda directa.
    """
    for rule in grammar.get_rules():
        if has_left_recursion(rule.get_head_name(), rule.altlist.sequences):
            return True
    return False


def eliminate_left_recursion(rule_name, sequences):
    """
    Elimina recursividade à esquerda directa.
    Devolve lista de regras em texto, ou None se não houver recursão.
    """
    recursive = []
    nonrecursive = []
    for seq in sequences:
        if seq.symbols and seq.symbols[0].get_value() == rule_name:
            recursive.append(seq)
        else:
            nonrecursive.append(seq)

    if not recursive:
        return None

    prime = f"{rule_name}'"
    base_alts = []
    for seq in nonrecursive:
        seq_str = _seq_to_str(seq.symbols)
        if seq_str == 'ε' or not seq.symbols:
            # β = ε  →  A -> A'  (não "ε A'")
            base_alts.append(prime)
        else:
            base_alts.append(f"{seq_str} {prime}")

    rec_alts = [
        f"{_seq_to_str(seq.symbols[1:])} {prime}" if seq.symbols[1:] else prime
        for seq in recursive
    ]
    rec_alts.append('ε')

    return [
        f"{rule_name} -> {' | '.join(base_alts)}",
        f"{prime} -> {' | '.join(rec_alts)}",
    ]


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
        original = f"{A} -> {' | '.join(_seq_to_str(s.symbols) for s in seqs)}"

        # Tentar eliminar recursividade à esquerda
        if has_left_recursion(A, seqs):
            result = eliminate_left_recursion(A, seqs)
            suggestions.append({
                'nonterminal': A,
                'type': c['type'],
                'technique': 'Eliminação de recursividade à esquerda',
                'aplicavel': True,
                'message': '',
                'new_rules': result,
            })
            continue

        # Tentar fatorização à esquerda (só faz sentido para FIRST/FIRST)
        if c['type'] == 'FIRST/FIRST':
            new_rules = left_factor(A, seqs)
            # Verificar se houve alteração real
            if len(new_rules) == 1 and new_rules[0] == original:
                suggestions.append({
                    'nonterminal': A,
                    'type': c['type'],
                    'technique': 'Sem correção automática possível',
                    'new_rules': ['⚠  A gramática pode ser intrinsecamente ambígua neste não-terminal.'],
                })
            else:
                suggestions.append({
                    'nonterminal': A,
                    'type': c['type'],
                    'technique': 'Fatorização à esquerda',
                    'aplicavel': True,
                    'message': '',
                    'new_rules': new_rules,
                })
            continue

        # FIRST/FOLLOW sem recursão à esquerda
        # Neste caso a fatorização não resolve — reportar sem correção automática
        suggestions.append({
            'nonterminal': A,
            'type': c['type'],
            'technique': 'Sem correção automática possível',
            'aplicavel': False,
            'message': (
                f'Conflito FIRST/FOLLOW em {A}: a gramática pode ser '
                f'intrinsecamente ambígua. Verifica se as alternativas '
                f'anuláveis e não-anuláveis partilham lookaheads.'
            ),
            'new_rules': [],
        })

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
        if s.get('aplicavel', True):
            print(f"  Regras novas :")
            for rule in s.get('new_rules', []):
                print(f"    {rule}")
        else:
            print(f"  ⚠  {s.get('message', 'Sem correção automática disponível.')}")
        print()
        

def check_llk(grammar, max_k=5):
    """
    Verifica se a gramática é LL(k) para k = 1, 2, ..., max_k.
    """
    # Primeiro verificamos LL(1) com a função existente
    first1 = compute_first(grammar)
    follow1 = compute_follow(grammar, first1)
    conflicts_1 = check_ll1(grammar, first1, follow1)

    if not conflicts_1:
        return 1, []   # já é LL(1)

    nts = grammar.get_nonterminals()

    if has_any_direct_left_recursion(grammar):
        return None, conflicts_1

    for k in range(2, max_k + 1):
        if is_llk(grammar, nts, k):
            return k, conflicts_1

    return None, conflicts_1   # não é LL(k) para nenhum k testado


def is_llk(grammar, nts, k):
    """
    Verifica se a gramática é LL(k) usando uma abordagem aproximada.
    """
    # Tokenizar cada alternativa e calcular prefixos de comprimento k
    for rule in grammar.get_rules():
        A = rule.get_head_name()
        seqs = rule.altlist.sequences

        if len(seqs) < 2:
            continue   # só uma alternativa → sem conflito possível

        # Para cada alternativa, calcular todas as strings de k tokens
        # que a podem iniciar (usando o lexer + lookahead sobre a gramática)
        alt_lookaheads = []
        for seq in seqs:
            lk = lookahead_k(seq.symbols, grammar, nts, k, set())
            alt_lookaheads.append(lk)

        # Verificar se há sobreposição entre qualquer par de alternativas
        for i in range(len(alt_lookaheads)):
            for j in range(i + 1, len(alt_lookaheads)):
                overlap = alt_lookaheads[i] & alt_lookaheads[j]
                if overlap:
                    return False   # conflito com k lookahead → não é LL(k)

    return True   # sem conflitos → é LL(k)


def lookahead_k(symbols, grammar, nts, k, visiting):
    """
    Calcula o conjunto de k-lookaheads para uma sequência de símbolos.
    """
    if k == 0 or not symbols:
        return {()}   # string vazia

    sym = symbols[0]
    rest = symbols[1:]

    if sym.get_is_epsilon():
        return {()}

    val = sym.get_value()

    if sym.get_is_terminal() or val not in nts:
        # terminal: prefixar com este token e continuar no resto
        rest_lk = lookahead_k(rest, grammar, nts, k - 1, visiting)
        result = set()
        for r in rest_lk:
            result.add((val,) + r)
        return result

    # não-terminal: evitar ciclos
    if val in visiting:
        return set()   # recursão detectada → retorna vazio (conservador)

    visiting = visiting | {val}

    # expandir todas as alternativas deste NT
    result = set()
    for rule in grammar.get_rules():
        if rule.get_head_name() != val:
            continue
        for seq in rule.altlist.sequences:
            # concatenar símbolos desta alternativa com o resto
            expanded = list(seq.symbols) + list(rest)
            lk = lookahead_k(expanded, grammar, nts, k, visiting)
            result |= lk

    return result