Spec          -> Axioma Newlines RuleList TokenSection

Axioma        -> START COLON NONTERM

RuleList      -> Rule RuleList
               | ε

Rule          -> NONTERM ARROW AltList Newlines
               | NONTERM ARROW AltList

AltList       -> Body AltListR
AltListR      -> PIPE Body AltListR
               | ε

Body          -> Symbol SymbolList
               | EPSILON

SymbolList    -> Symbol SymbolList
               | ε

Symbol        -> NONTERM
               | TERMINAL_NAME

TokenSection  -> TokenDecl TokenSection
               | ε

TokenDecl     -> TERMINAL_NAME EQUALS REGEX Newlines
               | TERMINAL_NAME EQUALS REGEX

Newlines      -> NEWLINE
               | NEWLINE Newlines


# ===== DEFINIÇÕES LÉXICAS =====
#
# START          →  'start' (palavra reservada)
# EPSILON        →  'epsilon' | 'ε' (palavra reservada)
# NONTERM        →  [A-Z][a-zA-Z0-9_]*'*  (letra maiúscula isolada ou PascalCase)
#                   Nota: uma letra maiúscula isolada (S, A, B) é NONTERM.
# TERMINAL_NAME  →  [A-Z][A-Z0-9_]+  (tudo maiúsculas, 2+ caracteres)
# STRING         →  '[^']*' | "[^"]*"
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
#   3. [A-Z][A-Z0-9_]* com len >= 2   → TERMINAL_NAME
#   4. Tudo o resto (incluindo letra maiúscula isolada) → NONTERM
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