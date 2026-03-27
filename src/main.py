"""
Grammar Playground — Pipeline principal

Demonstra todas as funcionalidades implementadas:
    1. Análise léxica e sintática → ASA (Árvore Sintática Abstrata)
    2. Validação semântica (erros e avisos)
    3. Conjuntos FIRST e FOLLOW
    4. Verificação LL(1) e deteção de conflitos
    5. Sugestões de correção (fatorização, eliminação de recursividade)
    6. Tabela de parsing LL(1)
    7. Geração dos parsers (recursivo descendente + dirigido por tabela)
    8. Geração do Visitor para geração de código
    9. Teste do visitor com frases de exemplo

Uso:
    python main.py                    # usa gramática de exemplo embutida
    python main.py grammar.txt        # lê gramática de um ficheiro
"""

import sys
import os
from gp_parser import parse_grammar, get_parse_errors, get_parse_warnings
from gp_analysis import *
from gp_parser_rd import generate_rd_parser
from gp_parser_td import TableParser, generate_table_parser
from gp_visitor import generate_visitor

YELLOW = "\033[93m"
RESET  = "\033[0m"

def warn(msg):
    print(f"{YELLOW}  ⚠  {msg}{RESET}")


EXAMPLE_GRAMMAR = """\
start: Program

Program    -> StmtList
StmtList   -> Stmt StmtListR
StmtListR  -> SEMI Stmt StmtListR | epsilon
Stmt       -> ID ASSIGN Expr
Expr       -> Term ExprR
ExprR      -> PLUS Term ExprR | epsilon
Term       -> ID | NUMBER

ID     = /[a-zA-Z_][a-zA-Z0-9_]*/
NUMBER = /[0-9]+/
PLUS   = /\\+/
SEMI   = /;/
ASSIGN = /:=/
"""

EXAMPLE_PHRASES = [
    "x := 5",
    "x := a + 3",
    "x := 1 ; y := x + 2 ; z := y + x + 1",
]


def sep(title):
    line = "=" * 64
    print(f"\n{line}")
    print(f" {title}")
    print(line)


def run_pipeline(source, test_phrases=None):

    sep("FASE 1 — Análise léxica, sintática e semântica (ASA)")

    grammar = parse_grammar(source)

    warnings = get_parse_warnings()
    if warnings:
        print()
        for w in warnings:
            warn(w)

    if grammar is None:
        print("\nAbortado: erros encontrados.")
        for e in get_parse_errors():
            print(f"  {e}")
        return

    print("\nÁrvore Sintática Abstrata:")
    grammar.print_tree()

    print(f"\nSímbolo inicial : {grammar.get_start()}")
    print(f"Não-terminais   : [{', '.join(sorted(grammar.get_nonterminals()))}]")
    print(f"Terminais       : [{', '.join(sorted(grammar.get_terminals()))}]")
    print(f"Padrões léxicos : {grammar.get_token_patterns()}")


    sep("FASE 2 — Conjuntos FIRST, FOLLOW e Lookahead")

    first = compute_first(grammar)
    follow = compute_follow(grammar, first)
    print_first_follow(first, follow)
    print_lookahead(grammar, first, follow)


    sep("FASE 3 — Verificação LL(1)")

    conflicts = check_ll1(grammar, first, follow)
    print_conflicts(conflicts)

    suggestions = suggest_fixes(grammar, conflicts)
    print_suggestions(suggestions)


    sep("FASE 4 — Tabela de parsing LL(1)")

    table = build_parse_table(grammar, first, follow)
    print_parse_table(table, grammar)

    if conflicts:
        print("\n⚠  A tabela pode conter células com múltiplas entradas (conflitos).")


    sep("FASE 5 — Geração dos parsers")

    if conflicts:
        print("⚠  A gramática tem conflitos — os parsers gerados podem não funcionar corretamente.")
        print("   Aplique as sugestões de correção antes de gerar os parsers.")
    else:
        # ── Parser Recursivo Descendente ─────────────────────────────
        rd_code = generate_rd_parser(grammar, first, follow)

        os.makedirs("generated_parsers", exist_ok=True)
        rd_file = "generated_parsers/rd.py"
        with open(rd_file, "w", encoding="utf-8") as f:
            f.write(rd_code)
        print(f"✓ Parser recursivo descendente gerado → {rd_file}")

        # ── Parser Dirigido por Tabela ────────────────────────────────
        td_code = generate_table_parser(grammar, first, follow)

        td_file = "generated_parsers/td.py"
        with open(td_file, "w", encoding="utf-8") as f:
            f.write(td_code)
        print(f"✓ Parser dirigido por tabela gerado   → {td_file}")

        # ── Visitor para geração de código ────────────────────────────
        sep("FASE 6 — Visitor para geração de código")

        visitor_code = generate_visitor(grammar)

        visitor_file = "generated_parsers/visitor.py"
        with open(visitor_file, "w", encoding="utf-8") as f:
            f.write(visitor_code)
        print(f"✓ Visitor gerado com sucesso          → {visitor_file}")

        nts = grammar.get_nonterminals()
        print(f"  Métodos visit_*: {len(nts)} ({', '.join(sorted(nts))})")

        # Mostrar o código gerado
        print(f"\n{'─' * 64}")
        print(f" Código do Visitor ({visitor_file})")
        print(f"{'─' * 64}\n")
        print(visitor_code)

        # ── Teste do Visitor com frases ───────────────────────────────
        if test_phrases:
            sep("FASE 7 — Teste do visitor")

            # Executar o visitor gerado
            vis_ns = {}
            exec(visitor_code, vis_ns)
            CodeGen = vis_ns['CodeGen']

            for phrase in test_phrases:
                print(f"\nFrase: {phrase!r}")
                try:
                    parser = TableParser(grammar, table, phrase)
                    tree = parser.parse()

                    visitor = CodeGen()
                    result = visitor.visit(tree)

                    print(f"  Árvore de derivação:")
                    tree.print_tree()
                    print(f"\n  Resultado do visitor: {result!r}")
                except SyntaxError as e:
                    print(f"  ✗ Erro: {e}")

    print()


if __name__ == '__main__':
    if len(sys.argv) > 1:
        filename = sys.argv[1]
        try:
            with open(filename, encoding='utf-8') as f:
                source = f.read()
            print(f"Gramática lida de '{filename}'.")
        except FileNotFoundError:
            print(f"Ficheiro '{filename}' não encontrado.")
            sys.exit(1)
        run_pipeline(source)
    else:
        print("A usar gramática de exemplo embutida.")
        run_pipeline(EXAMPLE_GRAMMAR, test_phrases=EXAMPLE_PHRASES)