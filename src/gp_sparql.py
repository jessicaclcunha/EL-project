from __future__ import annotations

NS = "http://rpcw.di.uminho.pt/2026/grammar-playground/"

PREFIXES = f"""\
PREFIX :    <{NS}>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs:<http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
"""

# ── Catálogo de queries ────────────────────────────────────────────────

QUERY_CATALOGUE: dict[str, dict] = {

    "conflitos": {
        "label": "Conflitos LL(1)",
        "description": "Lista todos os conflitos detectados, com tipo e símbolos em conflito.",
        "sparql": PREFIXES + """
SELECT ?conf ?tipo ?nt ?ntNome ?simbolo ?simNome
WHERE {
  ?conf a ?clsConflito .
  ?clsConflito rdfs:subClassOf* :Conflito .
  ?conf :tipoConflito ?tipo ;
        :conflitoEm   ?nt .
  ?nt   :nome         ?ntNome .
  OPTIONAL {
    ?conf :conflitoSimbolos ?simbolo .
    ?simbolo :nome ?simNome .
  }
}
ORDER BY ?ntNome ?tipo
""",
        "columns": ["tipo", "ntNome", "simNome"],
        "column_labels": ["Tipo", "NT", "Símbolo em conflito"],
    },

    "conflitos_celulas": {
        "label": "Células com conflito na tabela",
        "description": (
            "Células (NT, Terminal) onde existem duas ou mais entradas na tabela LL(1) "
            "— indicador directo de conflito."
        ),
        "sparql": PREFIXES + """
SELECT ?ntNome ?tNome (COUNT(?la) AS ?entradas)
WHERE {
  ?pt a :ParseTable ;
      :temEntrada ?la .
  ?la :entradaNT ?nt ;
      :entradaT  ?t .
  ?nt :nome ?ntNome .
  ?t  :nome ?tNome .
}
GROUP BY ?nt ?ntNome ?t ?tNome
HAVING (COUNT(?la) > 1)
ORDER BY ?ntNome ?tNome
""",
        "columns": ["ntNome", "tNome", "entradas"],
        "column_labels": ["NT", "Terminal", "Nº entradas"],
    },

    "first_follow": {
        "label": "Conjuntos FIRST e FOLLOW",
        "description": "Para cada NT, lista os terminais nos conjuntos FIRST e FOLLOW.",
        "sparql": PREFIXES + """
SELECT ?ntNome ?fSim ?fwSim
WHERE {
  ?nt a :NaoTerminal ; :nome ?ntNome .
  {
    ?nt :temFirst ?fs .
    ?fs :firstContem ?fsim .
    ?fsim :nome ?fSim .
    BIND("" AS ?fwSim)
  }
  UNION
  {
    ?nt :temFollow ?fw .
    ?fw :followContem ?fwsim .
    ?fwsim :nome ?fwSim .
    BIND("" AS ?fSim)
  }
}
ORDER BY ?ntNome ?fSim ?fwSim
""",
        "columns": ["ntNome", "fSim", "fwSim"],
        "column_labels": ["NT", "FIRST", "FOLLOW"],
        "post_process": "group_first_follow",
    },

    "anulaveis": {
        "label": "Alternativas anuláveis",
        "description": "Todas as alternativas que podem derivar ε.",
        "sparql": PREFIXES + """
SELECT ?ntNome ?altLookahead
WHERE {
  ?prod a :Producao ;
        :temCabeca     ?nt ;
        :temAlternativa ?alt .
  ?nt  :nome ?ntNome .
  ?alt :eNulo true ;
       :lookahead ?altLookahead .
}
ORDER BY ?ntNome
""",
        "columns": ["ntNome", "altLookahead"],
        "column_labels": ["NT", "Lookahead"],
    },

    "lookaheads": {
        "label": "Lookahead por alternativa",
        "description": "Conjunto lookahead efectivo de cada alternativa de cada produção.",
        "sparql": PREFIXES + """
SELECT ?ntNome ?altLookahead ?eNulo
WHERE {
  ?prod a :Producao ;
        :temCabeca     ?nt ;
        :temAlternativa ?alt .
  ?nt  :nome ?ntNome .
  ?alt :lookahead ?altLookahead ;
       :eNulo ?eNulo .
}
ORDER BY ?ntNome
""",
        "columns": ["ntNome", "altLookahead", "eNulo"],
        "column_labels": ["NT", "Lookahead", "Anulável"],
    },

    "producoes": {
        "label": "Produções e símbolos",
        "description": "Lista todas as produções com os símbolos de cada alternativa (por posição).",
        "sparql": PREFIXES + """
SELECT ?ntNome ?posicao ?simNome
WHERE {
  ?prod a :Producao ;
        :temCabeca     ?nt ;
        :temAlternativa ?alt .
  ?nt  :nome ?ntNome .
  ?alt :naPosicao ?snp .
  ?snp :posicao      ?posicao ;
       :posicaoSimbolo ?sim .
  ?sim :nome ?simNome .
}
ORDER BY ?ntNome ?posicao
""",
        "columns": ["ntNome", "posicao", "simNome"],
        "column_labels": ["NT", "Posição", "Símbolo"],
    },

    "terminais_regex": {
        "label": "Terminais com padrão regex",
        "description": "Todos os terminais declarados na TokenSection com o respectivo padrão.",
        "sparql": PREFIXES + """
SELECT ?nome ?regex
WHERE {
  ?t a :Terminal ;
     :nome  ?nome ;
     :regex ?regex .
}
ORDER BY ?nome
""",
        "columns": ["nome", "regex"],
        "column_labels": ["Terminal", "Padrão regex"],
    },

    "nts_sem_follow": {
        "label": "NTs potencialmente inalcançáveis",
        "description": (
            "NTs cujo conjunto FOLLOW está vazio (excepto o axioma) — "
            "possível indício de NT inalcançável."
        ),
        "sparql": PREFIXES + """
SELECT ?ntNome
WHERE {
  ?nt a :NaoTerminal ; :nome ?ntNome .
  ?nt :temFollow ?fw .
  FILTER NOT EXISTS { ?fw :followContem ?x }
  # excluir o axioma (que pode ter FOLLOW vazio se a gramática for trivial)
  FILTER NOT EXISTS { ?nt a :Start }
}
ORDER BY ?ntNome
""",
        "columns": ["ntNome"],
        "column_labels": ["NT"],
    },

    "estrutura_visitor": {
        "label": "Estrutura sugerida do Visitor",
        "description": (
            "Para cada NT, lista as alternativas e os respectivos lookaheads — "
            "base para gerar o esqueleto dos métodos visit_NT."
        ),
        "sparql": PREFIXES + """
SELECT ?ntNome ?altLookahead ?eNulo ?posicao ?simNome
WHERE {
  ?prod a :Producao ;
        :temCabeca     ?nt ;
        :temAlternativa ?alt .
  ?nt  :nome ?ntNome .
  ?alt :lookahead ?altLookahead ;
       :eNulo ?eNulo .
  OPTIONAL {
    ?alt :naPosicao ?snp .
    ?snp :posicao ?posicao ;
         :posicaoSimbolo ?sim .
    ?sim :nome ?simNome .
  }
}
ORDER BY ?ntNome ?eNulo ?posicao
""",
        "columns": ["ntNome", "altLookahead", "eNulo", "posicao", "simNome"],
        "column_labels": ["NT", "Lookahead", "Anulável", "Pos", "Símbolo"],
        "post_process": "group_visitor",
    },
}


# ── Motor de execução ──────────────────────────────────────────────────

def run_query(turtle_src: str, sparql: str) -> list[dict]:
    """
    Executa uma query SPARQL SELECT sobre o Turtle dado.
    Devolve lista de dicts {variável: valor_str}.
    """
    from rdflib import Graph

    g = Graph()
    g.parse(data=turtle_src, format="turtle")

    results = []
    for row in g.query(sparql):
        record = {}
        for var in row.labels:
            val = row[var]
            record[str(var)] = str(val) if val is not None else ""
        results.append(record)
    return results


def _post_group_first_follow(rows: list[dict]) -> list[dict]:
    """Agrupa os resultados da query first_follow por NT."""
    from collections import defaultdict
    data: dict[str, dict] = {}
    order: list[str] = []
    for row in rows:
        nt = row["ntNome"]
        if nt not in data:
            data[nt] = {"ntNome": nt, "first": set(), "follow": set()}
            order.append(nt)
        if row.get("fSim"):
            data[nt]["first"].add(row["fSim"])
        if row.get("fwSim"):
            data[nt]["follow"].add(row["fwSim"])
    return [
        {
            "ntNome": nt,
            "first":  ", ".join(sorted(data[nt]["first"])),
            "follow": ", ".join(sorted(data[nt]["follow"])),
        }
        for nt in order
    ]


def _post_group_visitor(rows: list[dict]) -> list[dict]:
    """Agrupa os resultados da query estrutura_visitor por NT+lookahead."""
    seen: dict[tuple, dict] = {}
    order: list[tuple] = []
    for row in rows:
        key = (row["ntNome"], row["altLookahead"], row["eNulo"])
        if key not in seen:
            seen[key] = {
                "ntNome":      row["ntNome"],
                "altLookahead": row["altLookahead"],
                "eNulo":       row["eNulo"],
                "simbolos":    [],
            }
            order.append(key)
        if row.get("simNome") and row.get("posicao") is not None:
            try:
                pos = int(row["posicao"])
            except (ValueError, TypeError):
                pos = 9999
            seen[key]["simbolos"].append((pos, row["simNome"]))
    result = []
    for key in order:
        d = seen[key]
        syms = " ".join(s for _, s in sorted(d["simbolos"]))
        result.append({
            "ntNome":       d["ntNome"],
            "simbolos":     syms,
            "altLookahead": d["altLookahead"],
            "eNulo":        d["eNulo"],
        })
    return result


_POST_PROCESSORS = {
    "group_first_follow": _post_group_first_follow,
    "group_visitor":      _post_group_visitor,
}


def run_catalogue_query(turtle_src: str, key: str) -> dict:
    """
    Corre uma query do catálogo e devolve:
      { ok, label, description, columns, column_labels, rows }
    """
    if key not in QUERY_CATALOGUE:
        return {"ok": False, "error": f"Query '{key}' não existe no catálogo."}

    q = QUERY_CATALOGUE[key]
    try:
        rows = run_query(turtle_src, q["sparql"])
        pp   = q.get("post_process")
        if pp and pp in _POST_PROCESSORS:
            rows = _POST_PROCESSORS[pp](rows)
        else:
            ordered = []
            for row in rows:
                ordered.append({col: row.get(col, "") for col in q["columns"]})
            rows = ordered
        # column_labels for post-processed queries may differ
        cols = q.get("columns_out", q["columns"])
        col_labels = q.get("column_labels_out", q["column_labels"])
        if pp == "group_first_follow":
            cols       = ["ntNome", "first", "follow"]
            col_labels = ["NT", "FIRST", "FOLLOW"]
        elif pp == "group_visitor":
            cols       = ["ntNome", "simbolos", "altLookahead", "eNulo"]
            col_labels = ["NT", "Símbolos", "Lookahead", "Anulável"]
        return {
            "ok":            True,
            "label":         q["label"],
            "description":   q["description"],
            "columns":       cols,
            "column_labels": col_labels,
            "rows":          rows,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def run_custom_query(turtle_src: str, sparql: str) -> dict:
    """
    Executa uma query SPARQL ad-hoc sobre o Turtle.
    Devolve { ok, columns, rows } ou { ok: False, error }.
    """
    try:
        rows = run_query(turtle_src, sparql)
        cols = list(rows[0].keys()) if rows else []
        return {"ok": True, "columns": cols, "rows": rows}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_catalogue_info() -> list[dict]:
    """Devolve metadados do catálogo (sem o SPARQL) para a UI."""
    return [
        {
            "key":         key,
            "label":       q["label"],
            "description": q["description"],
        }
        for key, q in QUERY_CATALOGUE.items()
    ]