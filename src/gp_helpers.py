"""
Utilitários partilhados entre app.py e outros módulos.

Inclui:
  - Normalização de terminais
  - Construção de padrões léxicos
  - Serialização de conflitos / sugestões / tabela LL(1) para JSON
  - Cálculo de lookahead por produção
  - Reconstrução da gramática após aplicar sugestões
  - Hash canónico da gramática
"""

import re
import hashlib

from gp_analysis import first_of_seq



def strip_quotes(t: str) -> str:
    """'[' → '[',  \"x\" → 'x',  ID → 'ID'  (remove aspas de terminais inline)."""
    if len(t) >= 2 and t[0] in ("'", '"') and t[-1] == t[0]:
        return t[1:-1]
    return t


def build_patterns(grammar) -> dict:
    """
    Devolve {tipo_sem_aspas: regex} para todos os terminais.
    Terminais declarados + terminais inline como '[' (sem aspas como chave).
    """
    patterns = dict(grammar.get_token_patterns())
    for t in grammar.get_terminals():
        if t.startswith(("'", '"')):
            inner = t[1:-1]
            if inner not in patterns:
                patterns[inner] = re.escape(inner)
    return patterns



def is_epsilon_seq(seq) -> bool:
    return not seq.symbols or (
        len(seq.symbols) == 1 and seq.symbols[0].get_is_epsilon()
    )


def seq_repr(seq) -> str:
    return 'ε' if is_epsilon_seq(seq) else ' '.join(s.get_value() for s in seq.symbols)



def compute_lookahead_table(grammar, first, follow) -> list[dict]:
    nts = grammar.get_nonterminals()
    result = []
    for rule in grammar.get_rules():
        nt = rule.get_head_name()
        for seq in rule.altlist.sequences:
            sf       = first_of_seq(seq.symbols, first, nts)
            nullable = 'ε' in sf
            la       = (sf - {'ε'}) | (follow.get(nt, set()) if nullable else set())
            result.append({
                'nt':         nt,
                'production': f'{nt} → {seq_repr(seq)}',
                'lookahead':  sorted(la),
                'nullable':   nullable,
            })
    return result


def ser_conflicts(conflicts) -> list[dict]:
    return [
        {
            'type':        c['type'],
            'nonterminal': c['nonterminal'],
            'message':     c.get('message', ''),
        }
        for c in conflicts
    ]


def ser_suggestions(suggestions) -> list[dict]:
    return [
        {
            'nonterminal': s['nonterminal'],
            'technique':   s['technique'],
            'aplicavel':   s.get('aplicavel', True),
            'message':     s.get('message', ''),
            'new_rules':   s['new_rules'],
        }
        for s in suggestions
    ]


def ser_table(table, grammar) -> dict:
    nts       = sorted(grammar.get_nonterminals())
    terminals = sorted({t for (_, t) in table})
    rows = []
    for nt in nts:
        cells = {}
        for t in terminals:
            seqs = table.get((nt, t), [])
            if not seqs:
                continue
            seq = seqs[0]
            rhs = seq_repr(seq)
            cells[t] = f'{nt} → {rhs}' + (' ⚠' if len(seqs) > 1 else '')
        rows.append({'nt': nt, 'cells': cells})
    return {'terminals': terminals, 'rows': rows}



def grammar_hash(src: str) -> str:
    """SHA-256 da gramática com whitespace normalizado."""
    normalised = re.sub(r'\s+', ' ', src.strip())
    return hashlib.sha256(normalised.encode()).hexdigest()



def rebuild_grammar(src: str, replacements: dict) -> str:
    """
    Substitui as regras de cada NT presente em `replacements`
    pelas novas strings, preservando a secção de tokens.
    """
    lines    = src.splitlines()
    TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*\s*=\s*/")
    RULE_RE  = re.compile(r"^([A-Za-z][A-Za-z0-9_']*)\s*(->|→)")

    rule_lines, token_lines, in_tokens = [], [], False
    for line in lines:
        if not in_tokens and TOKEN_RE.match(line.strip()):
            in_tokens = True
        (token_lines if in_tokens else rule_lines).append(line)

    blocks, i = [], 0
    while i < len(rule_lines):
        line = rule_lines[i]
        m    = RULE_RE.match(line.strip())
        if m:
            nt, block_lines = m.group(1), [line]
            i += 1
            while i < len(rule_lines):
                nxt = rule_lines[i].strip()
                if nxt.startswith('|') or (rule_lines[i] and rule_lines[i][0] in (' ', '\t')):
                    block_lines.append(rule_lines[i]); i += 1
                else:
                    break
            blocks.append((nt, block_lines))
        else:
            blocks.append((None, [line])); i += 1

    pending, out_rules = dict(replacements), []
    for nt, block_lines in blocks:
        if nt is not None and nt in pending:
            out_rules.extend(pending.pop(nt))
            for new_nt in [k for k in list(pending) if k.startswith(nt)]:
                out_rules.extend(pending.pop(new_nt))
        else:
            out_rules.extend(block_lines)

    for rules in pending.values():
        out_rules.extend(rules)

    if token_lines:
        if out_rules and out_rules[-1].strip():
            out_rules.append('')
        out_rules.extend(token_lines)

    return '\n'.join(out_rules)