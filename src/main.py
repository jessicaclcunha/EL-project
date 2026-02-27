"""
    python main.py                    # usa gramática de exemplo embutida
    python main.py grammar.txt        # lê gramática de um ficheiro
"""

import sys
from gp_parser   import parse_grammar
from gp_analysis import *


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

def run_pipeline(source):
    sep = "=" * 60

    print(f"\n{sep}")
    print(" FASE 1 — Análise léxica e sintática (ASA)")
    print(sep)

    grammar = parse_grammar(source)
    if grammar is None:
        print("Abortado: erros de parsing.")
        return

    grammar.print_tree()

    print(f"\nSímbolo inicial : {grammar.get_start()}")
    print(f"Não-terminais   : [{', '.join(sorted(grammar.get_nonterminals()))}]")
    print(f"Terminais       : [{', '.join(sorted(grammar.get_terminals()))}]")
    print(f"Padrões léxicos : {grammar.get_token_patterns()}")

    print(f"\n{sep}")
    print(" FASE 2 — Conjuntos FIRST e FOLLOW")
    print(sep)

    first  = compute_first(grammar)
    follow = compute_follow(grammar, first)
    print_first_follow(first, follow)

    print(f"\n{sep}")
    print(" FASE 3 — Verificação LL(1)")
    print(sep)

    conflicts = check_ll1(grammar, first, follow)
    print_conflicts(conflicts)

    suggestions = suggest_fixes(grammar, conflicts)
    print_suggestions(suggestions)

    print(f"\n{sep}")
    print(" FASE 4 — Tabela de parsing LL(1)")
    print(sep)

    table = build_parse_table(grammar, first, follow)
    print_parse_table(table, grammar)

    if conflicts:
        print("\n⚠  A tabela pode conter células com múltiplas entradas (conflitos).")


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
    else:
        print("A usar gramática de exemplo embutida.")
        source = EXAMPLE_GRAMMAR

    run_pipeline(source)