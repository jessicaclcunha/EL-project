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


## Definições léxicas

| Token | Padrão | Exemplos |
|-------|--------|---------|
| `START` | palavra reservada | `start` |
| `EPSILON` | palavra reservada | `epsilon`, `ε` |
| `NON_TERMINAL` | letra maiúscula + letras/dígitos/underscore | `S`, `Expr`, `StmtList` |
| `TERMINAL` | 2+ letras maiúsculas/dígitos/underscore | `ID`, `NUMBER`, `PLUS` |
| `TERMINAL` | string entre aspas simples ou duplas | `'('`, `':='`, `"hello"` |
| `REGEX` | padrão entre barras | `/[a-z]+/`, `/[0-9]+/` |
| `ARROW` | seta | `->`, `→` |
| `PIPE` | barra vertical | `\|` |
| `EQUALS` | igual | `=` |
| `COLON` | dois pontos | `:` |
| `NEWLINE` | newline | `\n` |

Ignorados: espaços, tabs, comentários (`#` até fim da linha).

## Precedência de classificação

Quando o lexer encontra um identificador, classifica-o por esta ordem:

1. `start` → **START**
2. `epsilon` → **EPSILON**
3. Tudo maiúsculas com 2+ caracteres → **TERMINAL** (ex: `ID`, `NUMBER`)
4. Tudo o resto, incluindo letra maiúscula isolada → **NON_TERMINAL** (ex: `S`, `Expr`)