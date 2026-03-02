Spec          -> Axioma Newlines RuleList TokenSection

Axioma        -> START COLON NON_TERMINAL

RuleList      -> Rule RuleList
               | ε

Rule          -> NON_TERMINAL ARROW AltList Newlines
               | NON_TERMINAL ARROW AltList

AltList       -> Body AltListR
AltListR      -> PIPE Body AltListR
               | ε

Body          -> Symbol SymbolList
               | EPSILON

SymbolList    -> Symbol SymbolList
               | ε

Symbol        -> NON_TERMINAL
               | TERMINAL

TokenSection  -> TokenDecl TokenSection
               | ε

TokenDecl     -> TERMINAL EQUALS REGEX Newlines
               | TERMINAL EQUALS REGEX

Newlines      -> NEWLINE
               | NEWLINE Newlines


# ===== DEFINIÇÕES LÉXICAS =====
#
# START          →  'start' (palavra reservada)
# EPSILON        →  'epsilon' | 'ε' (palavra reservada)
# NON_TERMINAL   →  [A-Z][a-zA-Z0-9_]*'*  (letra maiúscula isolada ou PascalCase)
#                   Nota: uma letra maiúscula isolada (S, A, B) é NON_TERMINAL.
# TERMINAL  →  [A-Z][A-Z0-9_]+  (tudo maiúsculas, 2+ caracteres)
# REGEX          →  /[^/]+/
# ARROW          →  '->' | '→'
# PIPE           →  '|'
# EQUALS         →  '='
# COLON          →  ':'
# NEWLINE        →  '\n'+
#
# Ignorados: espaços, tabs, comentários (# até fim da linha)
#
# ===== PRECEDÊNCIA DE CLASSIFICAÇÃO =====
#
# O identificador genérico [A-Za-z][A-Za-z0-9_]*'* é testado e depois
# classificado por ordem:
#   1. 'start'                         → START
#   2. 'epsilon'                       → EPSILON
#   3. [A-Z][A-Z0-9_]* com len >= 2   → TERMINAL
#   4. Tudo o resto (incluindo letra maiúscula isolada) → NON_TERMINAL
#
# ===== EXEMPLO DE INPUT VÁLIDO =====
#
# start: Program
#
# Program    -> StmtList
# StmtList   -> Stmt StmtListR
# StmtListR  -> SEMI Stmt StmtListR | epsilon
# Stmt       -> ID ASSIGN Expr
# Expr       -> Term ExprR
# ExprR      -> PLUS Term ExprR | epsilon
# Term       -> ID | NUMBER
#
# ID     = /[a-zA-Z_][a-zA-Z0-9_]*/
# NUMBER = /[0-9]+/
# PLUS   = /\+/
# SEMI   = /;/
# ASSIGN = /:=/