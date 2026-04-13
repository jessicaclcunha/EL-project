"""
Povoamento da ontologia OWL/RDF do Grammar Playground.

Recebe um SpecNode (gramática parseada) + FIRST/FOLLOW + tabela LL(1) +
conflitos, e produz um documento Turtle com indivíduos para todas as
classes definidas em ontology/grammar-playground.ttl:
    Gramatica, NaoTerminal, Terminal, Start, Epsilon,
    Producao, Alternativa, SimboloNaPosicao,
    FirstSet, FollowSet,
    Conflito (FirstFirst | FirstFollow),
    Lookahead, ParseTable.

Uso:
    from gp_ontology import generate_ontology
    ttl = generate_ontology(grammar, first, follow, table, conflicts,
                            grammar_name="MinhaGramatica")
"""

import re

NS = "http://rpcw.di.uminho.pt/2026/grammar-playground/"


def _safe(name):
    """Normaliza um nome para usar como local-name num IRI."""
    s = re.sub(r"[^A-Za-z0-9_]", "_", name)
    if s and s[0].isdigit():
        s = "_" + s
    return s or "_"


def _q(s):
    """Escapa string para literal Turtle (entre aspas duplas)."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _is_eps(seq):
    return not seq.symbols or (
        len(seq.symbols) == 1 and seq.symbols[0].get_is_epsilon()
    )


def generate_ontology(grammar, first, follow, table=None, conflicts=None,
                      grammar_name="GramaticaUtilizador"):
    """Gera Turtle com instâncias da ontologia para esta gramática."""
    conflicts = conflicts or []
    nts       = sorted(grammar.get_nonterminals())
    terms     = sorted(grammar.get_terminals())
    patterns  = grammar.get_token_patterns()
    start_nt  = grammar.get_start()
    is_ll1    = len(conflicts) == 0

    L = []
    w = L.append

    # ── Cabeçalho ─────────────────────────────────────────────
    w("@prefix : <" + NS + "> .")
    w("@prefix owl: <http://www.w3.org/2002/07/owl#> .")
    w("@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .")
    w("@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .")
    w("@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .")
    w("@base <" + NS + "> .")
    w("")

    # ── Gramática ─────────────────────────────────────────────
    g = "g_" + _safe(grammar_name)
    w(f"### Gramática")
    w(f":{g} a owl:NamedIndividual , :Gramatica ;")
    w(f'    :nomeGramatica "{_q(grammar_name)}" ;')
    w(f"    :eLL1 {'true' if is_ll1 else 'false'} ;")
    w(f"    :temStart :{g}_start ;")
    if nts:
        w(f"    :temNaoTerminal " + " , ".join(f":nt_{_safe(n)}" for n in nts) + " ;")
    if terms:
        w(f"    :temTerminal " + " , ".join(f":t_{_safe(t)}" for t in terms) + " ;")
    rule_ids = [f":prod_{_safe(r.get_head_name())}" for r in grammar.get_rules()]
    if rule_ids:
        w(f"    :temProducao " + " , ".join(rule_ids) + " ;")
    if conflicts:
        cids = [f":conf_{i+1}" for i in range(len(conflicts))]
        w(f"    :temConflito " + " , ".join(cids) + " ;")
    w(f"    :temParseTable :pt_{g} .")
    w("")

    # ── Start (subclasse de NaoTerminal) ─────────────────────
    w(f":{g}_start a owl:NamedIndividual , :Start ;")
    w(f'    :nome "{_q(start_nt)}" .')
    w("")

    # ── Não-terminais ─────────────────────────────────────────
    w("### Não-terminais")
    for nt in nts:
        nid = f":nt_{_safe(nt)}"
        w(f"{nid} a owl:NamedIndividual , :NaoTerminal ;")
        w(f'    :nome "{_q(nt)}" ;')
        w(f"    :temFirst :first_{_safe(nt)} ;")
        w(f"    :temFollow :follow_{_safe(nt)} .")
    w("")

    # ── Terminais ─────────────────────────────────────────────
    w("### Terminais")
    for t in terms:
        tid = f":t_{_safe(t)}"
        regex = patterns.get(t)
        w(f"{tid} a owl:NamedIndividual , :Terminal ;")
        w(f'    :nome "{_q(t)}"' + (" ;" if regex else " ."))
        if regex:
            w(f'    :regex "{_q(regex)}" .')
    w("")

    # ── FIRST sets ────────────────────────────────────────────
    w("### Conjuntos FIRST")
    for nt in nts:
        fid = f":first_{_safe(nt)}"
        members = sorted(first.get(nt, set()))
        w(f"{fid} a owl:NamedIndividual , :FirstSet")
        if members:
            refs = []
            for m in members:
                if m == "ε":
                    refs.append(":epsilon")
                elif m in terms:
                    refs.append(f":t_{_safe(m)}")
                else:
                    refs.append(f":t_{_safe(m)}")
            w(f"    ; :firstContem " + " , ".join(refs))
        w("    .")
    w("")

    # ── FOLLOW sets ───────────────────────────────────────────
    w("### Conjuntos FOLLOW")
    for nt in nts:
        fid = f":follow_{_safe(nt)}"
        members = sorted(follow.get(nt, set()))
        w(f"{fid} a owl:NamedIndividual , :FollowSet")
        if members:
            refs = []
            for m in members:
                if m == "$":
                    refs.append(":eof")
                elif m in terms:
                    refs.append(f":t_{_safe(m)}")
                else:
                    refs.append(f":t_{_safe(m)}")
            w(f"    ; :followContem " + " , ".join(refs))
        w("    .")
    w("")

    # ── Produções, alternativas, símbolos posicionados ───────
    w("### Produções")
    nts_set = set(nts)
    alt_uri_map = {}   # id(seq) -> URI da alternativa

    for rule in grammar.get_rules():
        nt = rule.get_head_name()
        pid = f":prod_{_safe(nt)}"
        seqs = rule.altlist.sequences

        alt_ids = []
        for i, seq in enumerate(seqs, start=1):
            aid = f":alt_{_safe(nt)}_{i}"
            alt_uri_map[id(seq)] = aid
            alt_ids.append(aid)

        w(f"{pid} a owl:NamedIndividual , :Producao ;")
        w(f"    :temCabeca :nt_{_safe(nt)} ;")
        w(f"    :temAlternativa " + " , ".join(alt_ids) + " .")
        w("")

        for i, seq in enumerate(seqs, start=1):
            aid = f":alt_{_safe(nt)}_{i}"
            is_eps = _is_eps(seq)
            w(f"{aid} a owl:NamedIndividual , :Alternativa ;")
            w(f"    :eNulo {'true' if is_eps else 'false'}")

            # Símbolos contidos (sem posição)
            if not is_eps:
                refs = []
                for sym in seq.symbols:
                    v = sym.get_value()
                    if sym.get_is_epsilon():
                        refs.append(":epsilon")
                    elif v in nts_set:
                        refs.append(f":nt_{_safe(v)}")
                    else:
                        refs.append(f":t_{_safe(v)}")
                if refs:
                    w(f"    ; :contemSimbolo " + " , ".join(refs))

            # SimboloNaPosicao (preserva ordem)
            if not is_eps:
                pos_ids = []
                for k, sym in enumerate(seq.symbols):
                    snp = f":snp_{_safe(nt)}_{i}_{k}"
                    pos_ids.append(snp)
                if pos_ids:
                    w(f"    ; :naPosicao " + " , ".join(pos_ids))
            w("    .")

            # Definir cada SimboloNaPosicao
            if not is_eps:
                for k, sym in enumerate(seq.symbols):
                    snp = f":snp_{_safe(nt)}_{i}_{k}"
                    v = sym.get_value()
                    if sym.get_is_epsilon():
                        ref = ":epsilon"
                    elif v in nts_set:
                        ref = f":nt_{_safe(v)}"
                    else:
                        ref = f":t_{_safe(v)}"
                    w(f"{snp} a owl:NamedIndividual , :SimboloNaPosicao ;")
                    w(f'    :posicao "{k}"^^xsd:nonNegativeInteger ;')
                    w(f"    :posicaoSimbolo {ref} .")
            w("")

    # ── ParseTable + Lookaheads ───────────────────────────────
    if table:
        w("### Parse Table")
        pt = f":pt_{g}"
        la_ids = []
        idx = 0
        for (nt, t), seqs in table.items():
            for seq in seqs:
                idx += 1
                la_ids.append(f":la_{idx}")

        w(f"{pt} a owl:NamedIndividual , :ParseTable")
        if la_ids:
            w(f"    ; :temEntrada " + " , ".join(la_ids))
        w("    .")
        w("")

        idx = 0
        for (nt, t), seqs in table.items():
            for seq in seqs:
                idx += 1
                lid = f":la_{idx}"
                aid = alt_uri_map.get(id(seq))
                t_ref = ":eof" if t == "$" else f":t_{_safe(t)}"
                w(f"{lid} a owl:NamedIndividual , :Lookahead ;")
                w(f"    :entradaNT :nt_{_safe(nt)} ;")
                w(f"    :entradaT {t_ref} ;")
                if aid:
                    w(f"    :entradaAlternativa {aid} .")
                else:
                    w("    .")
        w("")

    # ── Conflitos ─────────────────────────────────────────────
    if conflicts:
        w("### Conflitos LL(1)")
        for i, c in enumerate(conflicts, start=1):
            cid = f":conf_{i}"
            ctype = c.get('type', '')
            cls = "FirstFirst" if "FIRST/FIRST" in ctype else "FirstFollow"
            nt = c.get('nonterminal', '')

            w(f"{cid} a owl:NamedIndividual , :{cls} ;")
            w(f'    :tipoConflito "{_q(ctype)}" ;')
            w(f"    :conflitoEm :nt_{_safe(nt)}")

            syms = sorted(c.get('symbols', []))
            if syms:
                refs = []
                for s in syms:
                    if s == "$":
                        refs.append(":eof")
                    elif s == "ε":
                        refs.append(":epsilon")
                    else:
                        refs.append(f":t_{_safe(s)}")
                w(f"    ; :conflitoSimbolos " + " , ".join(refs))
            w("    .")
        w("")

    # Indivíduo $ (fim de input)
    w(":eof a owl:NamedIndividual , :Terminal ;")
    w('    :nome "$" .')
    w("")

    return "\n".join(L)