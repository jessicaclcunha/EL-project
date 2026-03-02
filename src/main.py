"""
Grammar Playground — Pipeline principal

Demonstra todas as funcionalidades implementadas:
    1. Análise léxica e sintática → ASA (Árvore Sintática Abstrata)
    2. Validação semântica (erros e avisos)
    3. Conjuntos FIRST e FOLLOW
    4. Verificação LL(1) e deteção de conflitos
    5. Sugestões de correção (fatorização, eliminação de recursividade)
    6. Tabela de parsing LL(1)
    7. Geração de parser recursivo descendente
    8. Teste do parser gerado com frases de exemplo

Uso:
    python main.py                    # usa gramática de exemplo embutida
    python main.py grammar.txt        # lê gramática de um ficheiro
"""

import sys
from gp_parser import parse_grammar, get_parse_errors, get_parse_warnings
from gp_analysis import (
    compute_first, compute_follow,
    print_first_follow, print_lookahead,
    check_ll1, print_conflicts,
    suggest_fixes, print_suggestions,
    build_parse_table, print_parse_table,
)
from gp_gen_rd import generate_rd_parser


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
    # -----------------------------------------------------------------
    # FASE 1 — Análise léxica, sintática e validação semântica
    # -----------------------------------------------------------------
    sep("FASE 1 — Análise léxica, sintática e semântica (ASA)")

    grammar = parse_grammar(source)

    # Mostrar avisos (se houver)
    warnings = get_parse_warnings()
    if warnings:
        print()
        for w in warnings:
            print(f"  {w}")

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

    # -----------------------------------------------------------------
    # FASE 2 — Conjuntos FIRST e FOLLOW
    # -----------------------------------------------------------------
    sep("FASE 2 — Conjuntos FIRST e FOLLOW")

    first = compute_first(grammar)
    follow = compute_follow(grammar, first)
    print_first_follow(first, follow)

    # -----------------------------------------------------------------
    # FASE 2b — Conjuntos Lookahead por produção
    # -----------------------------------------------------------------
    sep("FASE 2b — Lookahead por produção")

    print_lookahead(grammar, first, follow)

    # -----------------------------------------------------------------
    # FASE 3 — Verificação LL(1)
    # -----------------------------------------------------------------
    sep("FASE 3 — Verificação LL(1)")

    conflicts = check_ll1(grammar, first, follow)
    print_conflicts(conflicts)

    suggestions = suggest_fixes(grammar, conflicts)
    print_suggestions(suggestions)

    # -----------------------------------------------------------------
    # FASE 4 — Tabela de parsing LL(1)
    # -----------------------------------------------------------------
    sep("FASE 4 — Tabela de parsing LL(1)")

    table = build_parse_table(grammar, first, follow)
    print_parse_table(table, grammar)

    if conflicts:
        print("\n⚠  A tabela pode conter células com múltiplas entradas (conflitos).")

    # -----------------------------------------------------------------
    # FASE 5 — Geração do parser recursivo descendente
    # -----------------------------------------------------------------
    sep("FASE 5 — Geração do parser recursivo descendente")

    if conflicts:
        print("⚠  A gramática tem conflitos — o parser gerado pode não funcionar corretamente.")
        print("   Aplique as sugestões de correção antes de gerar o parser.")
    else:
        code = generate_rd_parser(grammar, first, follow)

        output_file = "generated_parser.py"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(code)
        print(f"✓ Parser gerado com sucesso → {output_file}")

        # Contagem de funções geradas
        nts = grammar.get_nonterminals()
        print(f"  Funções parse_*: {len(nts)} ({', '.join(sorted(nts))})")

        # -----------------------------------------------------------------
        # FASE 6 — Teste do parser gerado com frases
        # -----------------------------------------------------------------
        if test_phrases:
            sep("FASE 6 — Teste do parser gerado")

            # Executar o código gerado
            ns = {}
            exec(code, ns)

            for phrase in test_phrases:
                print(f"\nFrase: {phrase!r}")
                try:
                    lex = ns['Lexer'](phrase)
                    print(f"Tokens: {lex.tokens[:-1]}")  # sem o $ final
                    parser = ns['Parser'](lex.tokens)
                    tree = parser.parse()
                    print("Árvore de derivação:")
                    tree.print_tree()
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