from gp_helpers import safe_iri, inline_token_name

NS = "http://rpcw.di.uminho.pt/2026/grammar-playground/"


def q(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _is_eps(seq) -> bool:
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

    # ── Cabeçalho ──────────────────────────────────────────────────────
    w("@prefix : <" + NS + "> .")
    w("@prefix owl: <http://www.w3.org/2002/07/owl#> .")
    w("@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .")
    w("@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .")
    w("@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .")
    w("@base <" + NS + "> .")
    w("")

    # ── Gramática ──────────────────────────────────────────────────────
    g = "g_" + safe_iri(grammar_name)
    w("### Gramática")
    w(f":{g} a owl:NamedIndividual , :Gramatica ;")
    w(f'    :nomeGramatica "{q(grammar_name)}" ;')
    w(f"    :eLL1 {'true' if is_ll1 else 'false'} ;")
    w(f"    :temStart :{g}_start ;")
    if nts:
        w("    :temNaoTerminal " + " , ".join(f":nt_{safe_iri(n)}" for n in nts) + " ;")
    if terms:
        w("    :temTerminal " + " , ".join(f":t_{safe_iri(t)}" for t in terms) + " ;")
    rule_ids = [f":prod_{safe_iri(r.get_head_name())}" for r in grammar.get_rules()]
    if rule_ids:
        w("    :temProducao " + " , ".join(rule_ids) + " ;")
    if conflicts:
        cids = [f":conf_{i+1}" for i in range(len(conflicts))]
        w("    :temConflito " + " , ".join(cids) + " ;")
    w(f"    :temParseTable :pt_{g} .")
    w("")

    # ── Start ──────────────────────────────────────────────────────────
    w(f":{g}_start a owl:NamedIndividual , :Start ;")
    w(f'    :nome "{q(start_nt)}" .')
    w("")

    # ── Não-terminais ──────────────────────────────────────────────────
    w("### Não-terminais")
    for nt in nts:
        nid = f":nt_{safe_iri(nt)}"
        w(f"{nid} a owl:NamedIndividual , :NaoTerminal ;")
        w(f'    :nome "{q(nt)}" ;')
        w(f"    :temFirst :first_{safe_iri(nt)} ;")
        w(f"    :temFollow :follow_{safe_iri(nt)} .")
    w("")

    # ── Terminais ──────────────────────────────────────────────────────
    w("### Terminais")
    for t in terms:
        tid      = f":t_{safe_iri(t)}"
        regex    = patterns.get(t)
        is_inline = len(t) >= 2 and t[0] in ("'", '"') and t[-1] == t[0]
        display  = t[1:-1] if is_inline else t
        w(f"{tid} a owl:NamedIndividual , :Terminal ;")
        w(f'    :nome "{q(display)}"' + (" ;" if regex else " ."))
        if regex:
            w(f'    :regex "{q(regex)}" .')
    w("")

    # ── FIRST sets ─────────────────────────────────────────────────────
    w("### Conjuntos FIRST")
    for nt in nts:
        fid     = f":first_{safe_iri(nt)}"
        members = sorted(first.get(nt, set()))
        w(f"{fid} a owl:NamedIndividual , :FirstSet")
        if members:
            refs = [":epsilon" if m == "ε" else f":t_{safe_iri(m)}" for m in members]
            w("    ; :firstContem " + " , ".join(refs))
        w("    .")
    w("")

    # ── FOLLOW sets ────────────────────────────────────────────────────
    w("### Conjuntos FOLLOW")
    for nt in nts:
        fid     = f":follow_{safe_iri(nt)}"
        members = sorted(follow.get(nt, set()))
        w(f"{fid} a owl:NamedIndividual , :FollowSet")
        if members:
            refs = [":eof" if m == "$" else f":t_{safe_iri(m)}" for m in members]
            w("    ; :followContem " + " , ".join(refs))
        w("    .")
    w("")

    # ── Produções, alternativas, símbolos posicionados ─────────────────
    w("### Produções")
    nts_set     = set(nts)
    alt_uri_map = {}

    for rule in grammar.get_rules():
        nt   = rule.get_head_name()
        pid  = f":prod_{safe_iri(nt)}"
        seqs = rule.altlist.sequences

        alt_ids = []
        for i, seq in enumerate(seqs, start=1):
            aid = f":alt_{safe_iri(nt)}_{i}"
            alt_uri_map[id(seq)] = aid
            alt_ids.append(aid)

        w(f"{pid} a owl:NamedIndividual , :Producao ;")
        w(f"    :temCabeca :nt_{safe_iri(nt)} ;")
        w("    :temAlternativa " + " , ".join(alt_ids) + " .")
        w("")

        for i, seq in enumerate(seqs, start=1):
            aid    = f":alt_{safe_iri(nt)}_{i}"
            is_eps = _is_eps(seq)
            w(f"{aid} a owl:NamedIndividual , :Alternativa ;")
            w(f"    :eNulo {'true' if is_eps else 'false'}")

            if not is_eps:
                refs = []
                for sym in seq.symbols:
                    v = sym.get_value()
                    if sym.get_is_epsilon():
                        refs.append(":epsilon")
                    elif v in nts_set:
                        refs.append(f":nt_{safe_iri(v)}")
                    else:
                        refs.append(f":t_{safe_iri(v)}")
                if refs:
                    w("    ; :contemSimbolo " + " , ".join(refs))

                pos_ids = [f":snp_{safe_iri(nt)}_{i}_{k}" for k in range(len(seq.symbols))]
                w("    ; :naPosicao " + " , ".join(pos_ids))

            w("    .")

            if not is_eps:
                for k, sym in enumerate(seq.symbols):
                    snp = f":snp_{safe_iri(nt)}_{i}_{k}"
                    v   = sym.get_value()
                    if sym.get_is_epsilon():
                        ref = ":epsilon"
                    elif v in nts_set:
                        ref = f":nt_{safe_iri(v)}"
                    else:
                        ref = f":t_{safe_iri(v)}"
                    w(f"{snp} a owl:NamedIndividual , :SimboloNaPosicao ;")
                    w(f'    :posicao "{k}"^^xsd:nonNegativeInteger ;')
                    w(f"    :posicaoSimbolo {ref} .")
            w("")

    # ── ParseTable + Lookaheads ────────────────────────────────────────
    if table:
        w("### Parse Table")
        pt     = f":pt_{g}"
        la_ids = []
        idx    = 0
        for seqs in table.values():
            for _ in seqs:
                idx += 1
                la_ids.append(f":la_{idx}")

        w(f"{pt} a owl:NamedIndividual , :ParseTable")
        if la_ids:
            w("    ; :temEntrada " + " , ".join(la_ids))
        w("    .")
        w("")

        idx = 0
        for (nt, t), seqs in table.items():
            for seq in seqs:
                idx  += 1
                lid   = f":la_{idx}"
                aid   = alt_uri_map.get(id(seq))
                t_ref = ":eof" if t == "$" else f":t_{safe_iri(t)}"
                w(f"{lid} a owl:NamedIndividual , :Lookahead ;")
                w(f"    :entradaNT :nt_{safe_iri(nt)} ;")
                w(f"    :entradaT {t_ref} ;")
                w(f"    :entradaAlternativa {aid} ." if aid else "    .")
        w("")

    # ── Conflitos ──────────────────────────────────────────────────────
    if conflicts:
        w("### Conflitos LL(1)")
        for i, c in enumerate(conflicts, start=1):
            cid   = f":conf_{i}"
            ctype = c.get('type', '')
            cls   = "FirstFirst" if "FIRST/FIRST" in ctype else "FirstFollow"
            nt    = c.get('nonterminal', '')

            w(f"{cid} a owl:NamedIndividual , :{cls} ;")
            w(f'    :tipoConflito "{q(ctype)}" ;')
            w(f"    :conflitoEm :nt_{safe_iri(nt)}")

            syms = sorted(c.get('symbols', []))
            if syms:
                refs = []
                for s in syms:
                    if s == "$":
                        refs.append(":eof")
                    elif s == "ε":
                        refs.append(":epsilon")
                    else:
                        refs.append(f":t_{safe_iri(s)}")
                w("    ; :conflitoSimbolos " + " , ".join(refs))
            w("    .")
        w("")

    # Indivíduo $ (fim de input)
    w(":eof a owl:NamedIndividual , :Terminal ;")
    w('    :nome "$" .')
    w("")

    return "\n".join(L)