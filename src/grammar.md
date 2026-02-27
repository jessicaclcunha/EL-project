Spec          -> Axioma RuleList TokenSection

Axioma        -> "start" ":" NonTerm

RuleList      -> Rule RuleList
               | epsilon

Rule          -> NonTerm "->" AltList

AltList       -> Body AltList'
AltList'      -> "|" Body AltList'
               | epsilon

Body          -> Symbol SymbolList
               | epsilon

SymbolList    -> Symbol SymbolList
               | epsilon

Symbol        -> NonTerm
               | TERMINAL_NAME
               | STRING

TokenSection  -> TokenDecl TokenSection
               | epsilon

TokenDecl     -> TERMINAL_NAME "=" REGEX

// Casos especiais — definições léxicas
NonTerm       -> [A-Z][a-zA-Z0-9]*'*
TERMINAL_NAME -> [A-Z][A-Z0-9_]*
REGEX         -> "/" [^/]+ "/"
STRING        -> "'" [^']* "'" | '"' [^"]* '"'