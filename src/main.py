import sys
from gp_parser import parse_grammar, get_parse_errors, get_parse_warnings
from gp_analysis import *
from gp_parser_rd import generate_rd_parser
from gp_parser_td import TableParser, generate_table_parser
import os

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


        # ── Teste do Parser Dirigido por Tabela ───────────────────────
        # if test_phrases:
        #     sep("FASE 7 — Teste do parser dirigido por tabela")
        #     ns_td = {}
        #     exec(td_code, ns_td)
        #     for phrase in test_phrases:
        #         print(f"\nFrase: {phrase!r}")
        #         try:
        #             lex = ns_td['Lexer'](phrase)
        #             p = ns_td['Parser'](lex.tokens)
        #             tree = p.parse()
        #             print("Passos do parsing (stack):")
        #             p.print_steps()
        #             print("\nÁrvore de derivação:")
        #             tree.print_tree()
        #         except SyntaxError as e:
        #             print(f"  ✗ Erro: {e}")

        # # ── Comparação RD vs Tabela ───────────────────────────────────
        # if test_phrases:
        #     sep("FASE 8 — Comparação RD vs Tabela")
        #     ns_rd2 = {}; exec(rd_code, ns_rd2)
        #     ns_td2 = {}; exec(td_code, ns_td2)

        #     all_ok = True
        #     for phrase in test_phrases:
        #         try:
        #             # RD
        #             rd_lex = ns_rd2['Lexer'](phrase)
        #             rd_p   = ns_rd2['Parser'](rd_lex.tokens)
        #             rd_p.parse()

        #             # Tabela
        #             td_lex = ns_td2['Lexer'](phrase)
        #             td_p   = ns_td2['Parser'](td_lex.tokens)
        #             td_p.parse()

        #             print(f"  ✓  {phrase!r}  — ambos aceitam")
        #         except SyntaxError as e:
        #             print(f"  ✗  {phrase!r}  — {e}")
        #             all_ok = False

            # if all_ok:
            #     print("\n✓ Ambos os parsers produzem resultados consistentes.")

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