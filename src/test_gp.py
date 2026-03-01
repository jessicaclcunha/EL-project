"""
Testes para o Grammar Playground (GP)

Cobre:
    1. Lexer — tokenização correta de todos os tipos de tokens
    2. Parser — parsing de gramáticas válidas e deteção de erros
    3. Fusão de regras — regras do mesmo NT em linhas separadas
    4. AST — estrutura da árvore e métodos auxiliares
    5. FIRST / FOLLOW — conjuntos computados corretamente
    6. Conflitos LL(1) — deteção de FIRST/FIRST e FIRST/FOLLOW
    7. Tabela LL(1) — construção correta
    8. Sugestões — eliminação de recursividade e fatorização

Uso:
    python test_gp.py              # corre todos os testes
    python test_gp.py -v           # modo verbose
"""

import unittest
from gp_lexer import lexer, tokens
from gp_parser import parse_grammar, get_parse_errors
from gp_ast import (
    SpecNode, AxiomaNode, RuleListNode, RuleNode,
    AltListNode, SeqNode, SymbolNode,
    IdentifierNode, TerminalNameNode, StringNode, EpsilonNode,
    TokenSectionNode, TokenDeclNode, RegexNode,
)
from gp_analysis import (
    compute_first, compute_follow, first_of_seq,
    check_ll1, build_parse_table, suggest_fixes,
)


# =====================================================================
# Utilidades
# =====================================================================

def tokenize(source):
    """Tokeniza source e devolve lista de (tipo, valor)."""
    lexer.input(source)
    lexer.lineno = 1
    result = []
    while True:
        tok = lexer.token()
        if not tok:
            break
        result.append((tok.type, tok.value))
    return result


def parse(source):
    """Wrapper que faz parse e devolve o SpecNode."""
    return parse_grammar(source)


# =====================================================================
# 1. Testes do Lexer
# =====================================================================

class TestLexer(unittest.TestCase):

    def test_start_keyword(self):
        """'start' deve ser reconhecido como token START."""
        toks = tokenize("start")
        self.assertEqual(toks, [('START', 'start')])

    def test_epsilon_keyword(self):
        """'epsilon' deve ser reconhecido como EPSILON, não como NONTERM."""
        toks = tokenize("epsilon")
        self.assertEqual(toks, [('EPSILON', 'epsilon')])

    def test_epsilon_unicode(self):
        """'ε' deve ser reconhecido como EPSILON."""
        toks = tokenize("ε")
        self.assertEqual(toks, [('EPSILON', 'ε')])

    def test_nonterm_pascal(self):
        """PascalCase deve ser NONTERM."""
        toks = tokenize("Program")
        self.assertEqual(toks, [('NONTERM', 'Program')])

    def test_nonterm_single_letter(self):
        """Letra maiúscula isolada deve ser NONTERM (convenção de gramáticas)."""
        toks = tokenize("S")
        self.assertEqual(toks, [('NONTERM', 'S')])

    def test_nonterm_with_prime(self):
        """Não-terminal com ' deve ser NONTERM."""
        toks = tokenize("ExprR")
        self.assertEqual(toks, [('NONTERM', 'ExprR')])

    def test_terminal_name(self):
        """TUDO_MAIUSCULAS com 2+ chars deve ser TERMINAL_NAME."""
        toks = tokenize("ID NUMBER PLUS")
        types = [t[0] for t in toks]
        self.assertEqual(types, ['TERMINAL_NAME', 'TERMINAL_NAME', 'TERMINAL_NAME'])

    def test_arrow(self):
        """'->' e '→' devem ser ARROW."""
        toks = tokenize("->")
        self.assertEqual(toks[0][0], 'ARROW')
        toks2 = tokenize("→")
        self.assertEqual(toks2[0][0], 'ARROW')

    def test_pipe(self):
        """'|' deve ser PIPE."""
        toks = tokenize("|")
        self.assertEqual(toks, [('PIPE', '|')])

    def test_string_single_quotes(self):
        """String entre aspas simples deve ser STRING."""
        toks = tokenize("';'")
        self.assertEqual(toks, [('STRING', "';'")])

    def test_string_double_quotes(self):
        """String entre aspas duplas deve ser STRING."""
        toks = tokenize('"hello"')
        self.assertEqual(toks, [('STRING', '"hello"')])

    def test_regex(self):
        """Regex entre / / deve ser REGEX (sem as barras no valor)."""
        toks = tokenize("/[a-z]+/")
        self.assertEqual(toks, [('REGEX', '[a-z]+')])

    def test_colon(self):
        """':' deve ser COLON."""
        toks = tokenize(":")
        self.assertEqual(toks, [('COLON', ':')])

    def test_equals(self):
        """'=' deve ser EQUALS."""
        toks = tokenize("=")
        self.assertEqual(toks, [('EQUALS', '=')])

    def test_newlines(self):
        """Newlines devem ser NEWLINE."""
        toks = tokenize("\n\n")
        self.assertEqual(toks[0][0], 'NEWLINE')

    def test_comment_ignored(self):
        """Comentários (# ...) devem ser ignorados."""
        toks = tokenize("ID # isto é um comentário\nNUMBER")
        types = [t[0] for t in toks]
        self.assertNotIn('COMMENT', types)
        # Deve ter TERMINAL_NAME, NEWLINE, TERMINAL_NAME
        self.assertEqual(types, ['TERMINAL_NAME', 'NEWLINE', 'TERMINAL_NAME'])

    def test_spaces_ignored(self):
        """Espaços e tabs devem ser ignorados."""
        toks = tokenize("  ID  \t  NUMBER  ")
        types = [t[0] for t in toks]
        self.assertEqual(types, ['TERMINAL_NAME', 'TERMINAL_NAME'])

    def test_full_axiom_line(self):
        """Linha 'start: Program' deve dar START COLON NONTERM."""
        toks = tokenize("start: Program")
        types = [t[0] for t in toks]
        self.assertEqual(types, ['START', 'COLON', 'NONTERM'])

    def test_full_rule_line(self):
        """Linha 'Expr -> Term PLUS Expr' deve dar tokens corretos."""
        toks = tokenize("Expr -> Term PLUS Expr")
        expected_types = ['NONTERM', 'ARROW', 'NONTERM', 'TERMINAL_NAME', 'NONTERM']
        types = [t[0] for t in toks]
        self.assertEqual(types, expected_types)

    def test_full_token_decl_line(self):
        """Linha 'ID = /[a-z]+/' deve dar TERMINAL_NAME EQUALS REGEX."""
        toks = tokenize("ID = /[a-z]+/")
        types = [t[0] for t in toks]
        self.assertEqual(types, ['TERMINAL_NAME', 'EQUALS', 'REGEX'])

    def test_epsilon_in_rule(self):
        """'epsilon' dentro de uma regra deve ser EPSILON."""
        toks = tokenize("A -> B | epsilon")
        types = [t[0] for t in toks]
        self.assertEqual(types, ['NONTERM', 'ARROW', 'NONTERM', 'PIPE', 'EPSILON'])


# =====================================================================
# 2. Testes do Parser
# =====================================================================

class TestParser(unittest.TestCase):

    def test_minimal_grammar(self):
        """Gramática mínima com uma regra."""
        g = parse("start: S\nS -> ID\nID = /[a-z]+/\n")
        self.assertIsNotNone(g)
        self.assertIsInstance(g, SpecNode)
        self.assertEqual(g.get_start(), 'S')

    def test_grammar_with_epsilon(self):
        """Gramática com alternativa epsilon."""
        g = parse("start: A\nA -> B | epsilon\nB -> ID\nID = /[a-z]+/\n")
        self.assertIsNotNone(g)
        rules = g.get_rules()
        a_rule = next(r for r in rules if r.get_head_name() == 'A')
        self.assertEqual(len(a_rule.altlist.sequences), 2)

    def test_grammar_with_strings(self):
        """Gramática com terminais inline (quoted strings)."""
        g = parse("start: S\nS -> '(' S ')' | ID\nID = /[a-z]+/\n")
        self.assertIsNotNone(g)
        terminals = g.get_terminals()
        self.assertIn("'('", terminals)
        self.assertIn("')'", terminals)

    def test_multiple_rules(self):
        """Gramática com múltiplas regras."""
        g = parse("start: S\nS -> A B\nA -> ID\nB -> NUMBER\nID = /[a-z]+/\nNUMBER = /[0-9]+/\n")
        self.assertIsNotNone(g)
        self.assertEqual(len(g.get_rules()), 3)

    def test_last_rule_no_newline(self):
        """Última regra sem newline no fim do ficheiro."""
        g = parse("start: S\nS -> ID\nID = /x/")
        self.assertIsNotNone(g)

    def test_syntax_error_returns_none(self):
        """Erro sintático deve devolver None."""
        g = parse("start:\n")
        self.assertIsNone(g)

    def test_error_accumulation(self):
        """Erros devem ser acumulados em get_parse_errors()."""
        parse("start: S\nS -> |\n")
        errors = get_parse_errors()
        self.assertTrue(len(errors) > 0)

    def test_empty_token_section(self):
        """Gramática sem TokenSection deve funcionar."""
        g = parse("start: S\nS -> A\nA -> B\nB -> epsilon\n")
        self.assertIsNotNone(g)
        self.assertEqual(len(g.tokensection.decls), 0)

    def test_token_section(self):
        """TokenSection com declarações regex."""
        g = parse("start: S\nS -> ID\nID = /[a-z]+/\n")
        self.assertIsNotNone(g)
        patterns = g.get_token_patterns()
        self.assertIn('ID', patterns)
        self.assertEqual(patterns['ID'], '[a-z]+')


# =====================================================================
# 3. Testes de Fusão de Regras
# =====================================================================

class TestRuleMerging(unittest.TestCase):

    def test_merge_same_nt(self):
        """Regras do mesmo NT em linhas separadas devem ser fundidas."""
        g = parse("start: S\nS -> A\nS -> B\nA -> ID\nB -> NUMBER\nID = /x/\nNUMBER = /[0-9]+/\n")
        self.assertIsNotNone(g)
        s_rules = [r for r in g.get_rules() if r.get_head_name() == 'S']
        self.assertEqual(len(s_rules), 1, "Deve haver apenas 1 RuleNode para S")
        self.assertEqual(len(s_rules[0].altlist.sequences), 2, "S deve ter 2 alternativas")

    def test_merge_preserves_order(self):
        """A fusão deve preservar a ordem das alternativas."""
        g = parse("start: S\nS -> A\nS -> B\nS -> C\nA -> ID\nB -> ID\nC -> ID\nID = /x/\n")
        self.assertIsNotNone(g)
        s_rule = next(r for r in g.get_rules() if r.get_head_name() == 'S')
        alts = [repr(seq) for seq in s_rule.altlist.sequences]
        self.assertEqual(alts, ['A', 'B', 'C'])

    def test_no_merge_when_not_needed(self):
        """Se cada NT aparece uma vez, nada é alterado."""
        g = parse("start: S\nS -> A\nA -> ID\nID = /x/\n")
        self.assertIsNotNone(g)
        self.assertEqual(len(g.get_rules()), 2)

    def test_merge_with_inline_alternates(self):
        """Fusão deve funcionar com alternativas inline e separadas."""
        g = parse("start: S\nS -> A | B\nS -> C\nA -> ID\nB -> ID\nC -> ID\nID = /x/\n")
        self.assertIsNotNone(g)
        s_rule = next(r for r in g.get_rules() if r.get_head_name() == 'S')
        self.assertEqual(len(s_rule.altlist.sequences), 3, "S -> A | B + S -> C = 3 alternativas")


# =====================================================================
# 4. Testes da AST
# =====================================================================

class TestAST(unittest.TestCase):

    def test_get_start(self):
        g = parse("start: Program\nProgram -> ID\nID = /x/\n")
        self.assertEqual(g.get_start(), 'Program')

    def test_get_nonterminals(self):
        g = parse("start: S\nS -> A B\nA -> ID\nB -> NUMBER\nID = /x/\nNUMBER = /[0-9]+/\n")
        nts = g.get_nonterminals()
        self.assertEqual(nts, {'S', 'A', 'B'})

    def test_get_terminals_declared(self):
        g = parse("start: S\nS -> ID\nID = /x/\n")
        ts = g.get_terminals()
        self.assertIn('ID', ts)

    def test_get_terminals_inline(self):
        g = parse("start: S\nS -> '(' S ')'\n")
        ts = g.get_terminals()
        self.assertIn("'('", ts)
        self.assertIn("')'", ts)

    def test_get_token_patterns(self):
        g = parse("start: S\nS -> ID NUMBER\nID = /[a-z]+/\nNUMBER = /[0-9]+/\n")
        patterns = g.get_token_patterns()
        self.assertEqual(patterns['ID'], '[a-z]+')
        self.assertEqual(patterns['NUMBER'], '[0-9]+')

    def test_symbol_node_properties(self):
        """SymbolNode deve reportar corretamente se é terminal/epsilon."""
        sym_nt = SymbolNode(IdentifierNode('Expr'))
        self.assertFalse(sym_nt.get_is_terminal())
        self.assertFalse(sym_nt.get_is_epsilon())
        self.assertEqual(sym_nt.get_value(), 'Expr')

        sym_t = SymbolNode(TerminalNameNode('ID'))
        self.assertTrue(sym_t.get_is_terminal())
        self.assertEqual(sym_t.get_value(), 'ID')

        sym_eps = SymbolNode(EpsilonNode())
        self.assertTrue(sym_eps.get_is_epsilon())
        self.assertEqual(sym_eps.get_value(), 'ε')

        sym_str = SymbolNode(StringNode("'+'"))
        self.assertTrue(sym_str.get_is_terminal())


# =====================================================================
# 5. Testes FIRST / FOLLOW
# =====================================================================

class TestFirstFollow(unittest.TestCase):

    def _parse_and_compute(self, source):
        g = parse(source)
        self.assertIsNotNone(g, f"Parse falhou para: {source[:50]}...")
        first = compute_first(g)
        follow = compute_follow(g, first)
        return g, first, follow

    def test_first_simple(self):
        """FIRST de uma regra com um terminal."""
        _, first, _ = self._parse_and_compute(
            "start: S\nS -> ID\nID = /x/\n")
        self.assertEqual(first['S'], {'ID'})

    def test_first_with_epsilon(self):
        """FIRST de uma regra com alternativa epsilon."""
        _, first, _ = self._parse_and_compute(
            "start: A\nA -> ID | epsilon\nID = /x/\n")
        self.assertEqual(first['A'], {'ID', 'ε'})

    def test_first_propagation(self):
        """FIRST deve propagar-se através de não-terminais."""
        _, first, _ = self._parse_and_compute(
            "start: S\nS -> A\nA -> ID\nID = /x/\n")
        self.assertEqual(first['S'], {'ID'})

    def test_first_multiple_alts(self):
        """FIRST com múltiplas alternativas."""
        _, first, _ = self._parse_and_compute(
            "start: S\nS -> ID | NUMBER\nID = /[a-z]+/\nNUMBER = /[0-9]+/\n")
        self.assertEqual(first['S'], {'ID', 'NUMBER'})

    def test_first_nullable_chain(self):
        """FIRST quando um NT anulável precede outro símbolo."""
        _, first, _ = self._parse_and_compute(
            "start: S\nS -> A ID\nA -> epsilon\nID = /x/\n")
        self.assertIn('ID', first['S'])

    def test_follow_start_has_dollar(self):
        """FOLLOW do símbolo inicial deve conter $."""
        _, _, follow = self._parse_and_compute(
            "start: S\nS -> ID\nID = /x/\n")
        self.assertIn('$', follow['S'])

    def test_follow_propagation(self):
        """FOLLOW deve propagar-se de A para B quando A -> ... B."""
        _, _, follow = self._parse_and_compute(
            "start: S\nS -> A\nA -> ID\nID = /x/\n")
        # FOLLOW(A) deve conter $ (propagado de FOLLOW(S))
        self.assertIn('$', follow['A'])

    def test_follow_from_next_symbol(self):
        """FOLLOW(B) deve conter FIRST do que vem a seguir a B."""
        _, _, follow = self._parse_and_compute(
            "start: S\nS -> A PLUS B\nA -> ID\nB -> NUMBER\nID = /x/\nNUMBER = /[0-9]+/\nPLUS = /p/\n")
        # S -> A PLUS B  →  FOLLOW(A) deve conter PLUS
        self.assertIn('PLUS', follow['A'])

    def test_pascal_example(self):
        """Teste com o exemplo do enunciado (Pascal simplificado)."""
        g, first, follow = self._parse_and_compute("""\
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
PLUS   = /p/
SEMI   = /s/
ASSIGN = /a/
""")
        # FIRST checks
        self.assertEqual(first['Program'], {'ID'})
        self.assertEqual(first['Term'], {'ID', 'NUMBER'})
        self.assertIn('ε', first['ExprR'])
        self.assertIn('PLUS', first['ExprR'])
        self.assertIn('ε', first['StmtListR'])
        self.assertIn('SEMI', first['StmtListR'])

        # FOLLOW checks
        self.assertIn('$', follow['Program'])
        self.assertIn('SEMI', follow['Expr'])
        self.assertIn('$', follow['Expr'])
        self.assertIn('PLUS', follow['Term'])

        # Deve ser LL(1)
        conflicts = check_ll1(g, first, follow)
        self.assertEqual(len(conflicts), 0, "O exemplo Pascal deve ser LL(1)")


# =====================================================================
# 6. Testes de Conflitos LL(1)
# =====================================================================

class TestConflicts(unittest.TestCase):

    def _parse_and_check(self, source):
        g = parse(source)
        self.assertIsNotNone(g)
        first = compute_first(g)
        follow = compute_follow(g, first)
        return g, first, follow, check_ll1(g, first, follow)

    def test_no_conflict_ll1(self):
        """Gramática LL(1) válida não deve ter conflitos."""
        _, _, _, conflicts = self._parse_and_check(
            "start: S\nS -> ID | NUMBER\nID = /x/\nNUMBER = /[0-9]+/\n")
        self.assertEqual(len(conflicts), 0)

    def test_first_first_conflict(self):
        """Duas alternativas com o mesmo FIRST devem gerar FIRST/FIRST."""
        _, _, _, conflicts = self._parse_and_check(
            "start: S\nS -> ID NUMBER | ID PLUS\nID = /x/\nNUMBER = /n/\nPLUS = /p/\n")
        self.assertTrue(any(c['type'] == 'FIRST/FIRST' for c in conflicts))

    def test_left_recursion_conflict(self):
        """Recursividade à esquerda deve gerar conflito."""
        _, _, _, conflicts = self._parse_and_check(
            "start: E\nE -> E PLUS T | T\nT -> ID\nID = /x/\nPLUS = /p/\n")
        self.assertTrue(len(conflicts) > 0)
        self.assertTrue(any(c['nonterminal'] == 'E' for c in conflicts))

    def test_first_follow_conflict(self):
        """Conflito FIRST/FOLLOW com alternativa anulável."""
        _, _, _, conflicts = self._parse_and_check(
            "start: S\nS -> A ID\nA -> ID | epsilon\nID = /x/\n")
        ff_conflicts = [c for c in conflicts if c['type'] == 'FIRST/FOLLOW']
        self.assertTrue(len(ff_conflicts) > 0)

    def test_conflict_detected_across_merged_rules(self):
        """Conflitos devem ser detetados mesmo com regras em linhas separadas."""
        _, _, _, conflicts = self._parse_and_check(
            "start: S\nS -> ID\nS -> ID NUMBER\nID = /x/\nNUMBER = /n/\n")
        self.assertTrue(len(conflicts) > 0, "Conflito entre regras fundidas deve ser detetado")


# =====================================================================
# 7. Testes da Tabela LL(1)
# =====================================================================

class TestParseTable(unittest.TestCase):

    def test_simple_table(self):
        """Tabela LL(1) para gramática simples sem conflitos."""
        g = parse("start: S\nS -> ID | NUMBER\nID = /x/\nNUMBER = /[0-9]+/\n")
        first = compute_first(g)
        follow = compute_follow(g, first)
        table = build_parse_table(g, first, follow)

        # S com ID → deve ter uma entrada
        self.assertIn(('S', 'ID'), table)
        self.assertEqual(len(table[('S', 'ID')]), 1)

        # S com NUMBER → deve ter uma entrada
        self.assertIn(('S', 'NUMBER'), table)
        self.assertEqual(len(table[('S', 'NUMBER')]), 1)

    def test_epsilon_in_table(self):
        """Alternativa epsilon deve aparecer na tabela com tokens do FOLLOW."""
        g = parse("start: S\nS -> A ID\nA -> NUMBER | epsilon\nID = /x/\nNUMBER = /n/\n")
        first = compute_first(g)
        follow = compute_follow(g, first)
        table = build_parse_table(g, first, follow)

        # A com ID → deve usar a alternativa epsilon (ID está no FOLLOW(A))
        self.assertIn(('A', 'ID'), table)

    def test_conflict_multiple_entries(self):
        """Conflitos devem resultar em múltiplas entradas na mesma célula."""
        g = parse("start: S\nS -> ID NUMBER | ID PLUS\nID = /x/\nNUMBER = /n/\nPLUS = /p/\n")
        first = compute_first(g)
        follow = compute_follow(g, first)
        table = build_parse_table(g, first, follow)

        # S com ID → deve ter 2 entradas (conflito)
        self.assertIn(('S', 'ID'), table)
        self.assertGreater(len(table[('S', 'ID')]), 1)


# =====================================================================
# 8. Testes de Sugestões de Correção
# =====================================================================

class TestSuggestions(unittest.TestCase):

    def test_left_recursion_elimination(self):
        """Deve sugerir eliminação de recursividade à esquerda."""
        g = parse("start: E\nE -> E PLUS T | T\nT -> ID\nID = /x/\nPLUS = /p/\n")
        first = compute_first(g)
        follow = compute_follow(g, first)
        conflicts = check_ll1(g, first, follow)
        suggestions = suggest_fixes(g, conflicts)

        self.assertTrue(len(suggestions) > 0)
        s = suggestions[0]
        self.assertEqual(s['nonterminal'], 'E')
        self.assertIn('recursividade', s['technique'].lower())

    def test_left_factoring(self):
        """Deve sugerir fatorização à esquerda para prefixo comum."""
        g = parse("start: S\nS -> ID NUMBER | ID PLUS\nID = /x/\nNUMBER = /n/\nPLUS = /p/\n")
        first = compute_first(g)
        follow = compute_follow(g, first)
        conflicts = check_ll1(g, first, follow)
        suggestions = suggest_fixes(g, conflicts)

        self.assertTrue(len(suggestions) > 0)
        s = suggestions[0]
        self.assertEqual(s['nonterminal'], 'S')
        self.assertIn('fatorização', s['technique'].lower())

    def test_no_suggestions_for_ll1(self):
        """Gramática LL(1) não deve gerar sugestões."""
        g = parse("start: S\nS -> ID | NUMBER\nID = /x/\nNUMBER = /[0-9]+/\n")
        first = compute_first(g)
        follow = compute_follow(g, first)
        conflicts = check_ll1(g, first, follow)
        suggestions = suggest_fixes(g, conflicts)
        self.assertEqual(len(suggestions), 0)


# =====================================================================
# 9. Teste integrado — pipeline completo
# =====================================================================

class TestIntegration(unittest.TestCase):

    def test_full_pipeline_pascal(self):
        """Pipeline completo com o exemplo do enunciado."""
        source = """\
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
PLUS   = /p/
SEMI   = /s/
ASSIGN = /a/
"""
        # Parse
        g = parse(source)
        self.assertIsNotNone(g)

        # Estrutura
        self.assertEqual(g.get_start(), 'Program')
        self.assertEqual(len(g.get_rules()), 7)
        self.assertEqual(len(g.tokensection.decls), 5)

        # FIRST / FOLLOW
        first = compute_first(g)
        follow = compute_follow(g, first)

        # Sem conflitos
        conflicts = check_ll1(g, first, follow)
        self.assertEqual(len(conflicts), 0)

        # Tabela
        table = build_parse_table(g, first, follow)
        # Todas as células devem ter no máximo 1 entrada
        for key, entries in table.items():
            self.assertEqual(len(entries), 1,
                             f"Conflito na célula {key}: {entries}")

    def test_full_pipeline_with_conflicts(self):
        """Pipeline completo com gramática que tem conflitos."""
        source = """\
start: E

E -> E PLUS T | T
T -> ID | NUMBER

ID = /x/
NUMBER = /n/
PLUS = /p/
"""
        g = parse(source)
        self.assertIsNotNone(g)

        first = compute_first(g)
        follow = compute_follow(g, first)

        conflicts = check_ll1(g, first, follow)
        self.assertGreater(len(conflicts), 0)

        suggestions = suggest_fixes(g, conflicts)
        self.assertGreater(len(suggestions), 0)


if __name__ == '__main__':
    unittest.main()


# =====================================================================
# 10. Testes do Gerador de Parser Recursivo Descendente
# =====================================================================

class TestRDGenerator(unittest.TestCase):
    """Testes para gp_gen_rd.generate_rd_parser."""

    def _generate_and_exec(self, source):
        """Parse a gramática, gera o parser RD e executa o código gerado."""
        g = parse(source)
        self.assertIsNotNone(g, "Parse da gramática falhou")
        from gp_analysis import compute_first, compute_follow
        first = compute_first(g)
        follow = compute_follow(g, first)

        from gp_gen_rd import generate_rd_parser
        code = generate_rd_parser(g, first, follow)

        # Executar o código gerado num namespace isolado
        ns = {}
        exec(code, ns)
        return ns

    def _parse_phrase(self, ns, phrase):
        """Usa o parser gerado (no namespace) para analisar uma frase."""
        lex = ns['Lexer'](phrase)
        parser = ns['Parser'](lex.tokens)
        return parser.parse()

    # --- Testes de geração ---

    def test_generates_valid_python(self):
        """O código gerado deve ser Python válido (sem erros de sintaxe)."""
        ns = self._generate_and_exec(
            "start: S\nS -> ID\nID = /[a-z]+/\n")
        self.assertIn('Parser', ns)
        self.assertIn('Lexer', ns)
        self.assertIn('TreeNode', ns)

    def test_parser_has_method_per_nt(self):
        """O parser gerado deve ter um método parse_X para cada NT."""
        ns = self._generate_and_exec(
            "start: S\nS -> A\nA -> ID\nID = /[a-z]+/\n")
        parser_cls = ns['Parser']
        self.assertTrue(hasattr(parser_cls, 'parse_S'))
        self.assertTrue(hasattr(parser_cls, 'parse_A'))

    # --- Testes de parsing ---

    def test_simple_terminal(self):
        """Parsing de um terminal simples."""
        ns = self._generate_and_exec(
            "start: S\nS -> ID\nID = /[a-z]+/\n")
        tree = self._parse_phrase(ns, "hello")
        self.assertEqual(tree.label, 'S')
        self.assertEqual(len(tree.children), 1)
        self.assertEqual(tree.children[0].token_value, 'hello')

    def test_two_alternatives(self):
        """Parsing com duas alternativas disjuntas."""
        ns = self._generate_and_exec(
            "start: S\nS -> ID | NUMBER\nID = /[a-z]+/\nNUMBER = /[0-9]+/\n")
        tree1 = self._parse_phrase(ns, "abc")
        self.assertEqual(tree1.children[0].label, 'ID')

        tree2 = self._parse_phrase(ns, "42")
        self.assertEqual(tree2.children[0].label, 'NUMBER')

    def test_epsilon_alternative(self):
        """Parsing de alternativa epsilon."""
        ns = self._generate_and_exec(
            "start: S\nS -> ID A\nA -> NUMBER | epsilon\nID = /[a-z]+/\nNUMBER = /[0-9]+/\n")
        # Com NUMBER presente
        tree1 = self._parse_phrase(ns, "x 42")
        a_node = tree1.children[1]
        self.assertEqual(a_node.label, 'A')
        self.assertEqual(a_node.children[0].label, 'NUMBER')

        # Sem NUMBER (epsilon)
        tree2 = self._parse_phrase(ns, "x")
        a_node2 = tree2.children[1]
        self.assertEqual(a_node2.label, 'A')
        self.assertEqual(a_node2.children[0].label, 'ε')

    def test_recursive_rule(self):
        """Parsing de regra recursiva (não à esquerda)."""
        ns = self._generate_and_exec(
            "start: S\nS -> '(' S ')' | ID\nID = /[a-z]+/\n")
        tree = self._parse_phrase(ns, "((x))")
        self.assertEqual(tree.label, 'S')
        # Raiz: ( S )
        inner = tree.children[1]  # S interior
        self.assertEqual(inner.label, 'S')

    def test_sequence_of_symbols(self):
        """Parsing de sequência de múltiplos símbolos."""
        ns = self._generate_and_exec(
            "start: S\nS -> ID ASSIGN NUMBER\nID = /[a-z]+/\nASSIGN = /:=/\nNUMBER = /[0-9]+/\n")
        tree = self._parse_phrase(ns, "x := 5")
        self.assertEqual(len(tree.children), 3)
        self.assertEqual(tree.children[0].token_value, 'x')
        self.assertEqual(tree.children[1].token_value, ':=')
        self.assertEqual(tree.children[2].token_value, '5')

    def test_pascal_example_simple(self):
        """Parsing do exemplo Pascal: x := 5."""
        ns = self._generate_and_exec("""\
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
PLUS   = /[+]/
SEMI   = /;/
ASSIGN = /:=/
""")
        tree = self._parse_phrase(ns, "x := 5")
        self.assertEqual(tree.label, 'Program')

    def test_pascal_example_expression(self):
        """Parsing do exemplo Pascal: x := a + 3."""
        ns = self._generate_and_exec("""\
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
PLUS   = /[+]/
SEMI   = /;/
ASSIGN = /:=/
""")
        tree = self._parse_phrase(ns, "x := a + 3")
        self.assertEqual(tree.label, 'Program')

    def test_pascal_example_multi_stmt(self):
        """Parsing do exemplo Pascal: x := 1 ; y := x + 2."""
        ns = self._generate_and_exec("""\
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
PLUS   = /[+]/
SEMI   = /;/
ASSIGN = /:=/
""")
        tree = self._parse_phrase(ns, "x := 1 ; y := x + 2")
        self.assertEqual(tree.label, 'Program')

    def test_syntax_error_detected(self):
        """Erros na frase de input devem lançar SyntaxError."""
        ns = self._generate_and_exec(
            "start: S\nS -> ID ASSIGN NUMBER\nID = /[a-z]+/\nASSIGN = /:=/\nNUMBER = /[0-9]+/\n")
        with self.assertRaises(SyntaxError):
            self._parse_phrase(ns, "x := ")  # falta o NUMBER

    def test_lexer_error_detected(self):
        """Caracteres inválidos devem lançar SyntaxError no lexer."""
        ns = self._generate_and_exec(
            "start: S\nS -> ID\nID = /[a-z]+/\n")
        with self.assertRaises(SyntaxError):
            self._parse_phrase(ns, "@@@")

    def test_tree_structure(self):
        """A árvore de derivação deve ter a estrutura correta."""
        ns = self._generate_and_exec(
            "start: S\nS -> A B\nA -> ID\nB -> NUMBER\nID = /[a-z]+/\nNUMBER = /[0-9]+/\n")
        tree = self._parse_phrase(ns, "x 42")

        # S -> A B
        self.assertEqual(tree.label, 'S')
        self.assertEqual(len(tree.children), 2)

        # A -> ID
        a_node = tree.children[0]
        self.assertEqual(a_node.label, 'A')
        self.assertEqual(a_node.children[0].label, 'ID')
        self.assertEqual(a_node.children[0].token_value, 'x')

        # B -> NUMBER
        b_node = tree.children[1]
        self.assertEqual(b_node.label, 'B')
        self.assertEqual(b_node.children[0].label, 'NUMBER')
        self.assertEqual(b_node.children[0].token_value, '42')


# =====================================================================
# 11. Testes de Validação Semântica
# =====================================================================

class TestValidation(unittest.TestCase):

    def test_start_without_rule(self):
        """Símbolo inicial sem regra definida deve dar erro."""
        g = parse("start: X\nS -> ID\nID = /x/\n")
        self.assertIsNone(g)
        errors = get_parse_errors()
        self.assertTrue(any("X" in e and "regra" in e for e in errors))

    def test_undefined_nonterminal(self):
        """NT usado no corpo sem regra definida deve dar erro."""
        g = parse("start: S\nS -> A\n")
        self.assertIsNone(g)
        errors = get_parse_errors()
        self.assertTrue(any("A" in e for e in errors))

    def test_undeclared_terminal_warning(self):
        """Terminal sem declaração na TokenSection deve dar aviso (não erro)."""
        g = parse("start: S\nS -> ID\n")
        self.assertIsNotNone(g)  # deve funcionar, é só aviso
        from gp_parser import get_parse_warnings
        warnings = get_parse_warnings()
        self.assertTrue(any("ID" in w for w in warnings))

    def test_unused_nt_warning(self):
        """NT definido mas nunca referenciado deve dar aviso."""
        g = parse("start: S\nS -> ID\nA -> ID\nID = /x/\n")
        self.assertIsNotNone(g)
        from gp_parser import get_parse_warnings
        warnings = get_parse_warnings()
        self.assertTrue(any("A" in w for w in warnings))

    def test_valid_grammar_no_errors(self):
        """Gramática válida não deve produzir erros nem avisos."""
        g = parse("start: S\nS -> ID\nID = /x/\n")
        self.assertIsNotNone(g)
        self.assertEqual(len(get_parse_errors()), 0)
        from gp_parser import get_parse_warnings
        self.assertEqual(len(get_parse_warnings()), 0)

    def test_multiple_errors(self):
        """Múltiplos erros devem ser todos reportados."""
        g = parse("start: X\nS -> A\n")
        self.assertIsNone(g)
        errors = get_parse_errors()
        # Erros: X sem regra, A sem regra
        self.assertGreaterEqual(len(errors), 2)