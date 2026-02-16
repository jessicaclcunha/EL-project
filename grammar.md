## 1. Gramática

```ebnf
Program → StatementList

StatementList → Statement StatementList'
StatementList' → Statement StatementList' 
              | ε

Statement → VarDecl
         | ExprStmt
         | BlockStmt
         | IfStmt
         | ReturnStmt
         | FunctionDecl
         | WhileStmt

VarDecl → VarKind ID VarInit ';'

VarKind → 'let' 
       | 'const' 
       | 'var'

VarInit → '=' Expr 
       | ε

Expr → AssignmentExpr

AssignmentExpr → LogicalOrExpr AssignOp'

AssignOp' → '=' AssignmentExpr 
         | ε

LogicalOrExpr → LogicalAndExpr LogicalOrExpr'

LogicalOrExpr' → '||' LogicalAndExpr LogicalOrExpr' 
              | ε

LogicalAndExpr → EqualityExpr LogicalAndExpr'

LogicalAndExpr' → '&&' EqualityExpr LogicalAndExpr' 
               | ε

EqualityExpr → RelationalExpr EqualityExpr'

EqualityExpr' → EqualityOp RelationalExpr EqualityExpr' 
             | ε

EqualityOp → '==' 
          | '===' 
          | '!=' 
          | '!=='

RelationalExpr → AdditiveExpr RelationalExpr'

RelationalExpr' → RelationalOp AdditiveExpr RelationalExpr' 
               | ε

RelationalOp → '<' 
            | '>' 
            | '<=' 
            | '>='

AdditiveExpr → MultiplicativeExpr AdditiveExpr'

AdditiveExpr' → '+' MultiplicativeExpr AdditiveExpr'
             | '-' MultiplicativeExpr AdditiveExpr'
             | ε

MultiplicativeExpr → UnaryExpr MultiplicativeExpr'

MultiplicativeExpr' → '*' UnaryExpr MultiplicativeExpr'
                   | '/' UnaryExpr MultiplicativeExpr'
                   | '%' UnaryExpr MultiplicativeExpr'
                   | ε

UnaryExpr → '!' UnaryExpr
         | '-' UnaryExpr
         | PrimaryExpr

PrimaryExpr → ID
           | NUMBER
           | STRING
           | 'true'
           | 'false'
           | 'null'
           | '(' Expr ')'

FunctionDecl → 'function' ID '(' ParamList ')' BlockStmt

ParamList → ID MoreParams 
         | ε

MoreParams → ',' ID MoreParams 
          | ε

IfStmt → 'if' '(' Expr ')' Statement ElseClause

ElseClause → 'else' Statement 
          | ε

WhileStmt → 'while' '(' Expr ')' Statement

BlockStmt → '{' StatementList '}'

ReturnStmt → 'return' Expr ';'

ExprStmt → Expr ';'

ID: [a-zA-Z_][a-zA-Z0-9_]*
NUMBER: [0-9]+ | [0-9]+\.[0-9]+
STRING: "[^"]*" | '[^']*'
```

---

## 2. Símbolos da Gramática

### 2.1 Não-Terminais (N)

```
N = {
  Program,           // Símbolo inicial
  StatementList,     // Lista de statements
  StatementList',    // Lista de statements (continuação)
  Statement,         // Statement genérico
  VarDecl,          // Declaração de variável
  VarKind,          // Tipo de variável (let/const/var)
  VarInit,          // Inicialização de variável
  Expr,             // Expressão
  AssignmentExpr,   // Expressão de atribuição
  AssignOp',        // Operador de atribuição (continuação)
  LogicalOrExpr,    // Expressão OR lógico
  LogicalOrExpr',   // OR lógico (continuação)
  LogicalAndExpr,   // Expressão AND lógico
  LogicalAndExpr',  // AND lógico (continuação)
  EqualityExpr,     // Expressão de igualdade
  EqualityExpr',    // Igualdade (continuação)
  EqualityOp,       // Operador de igualdade
  RelationalExpr,   // Expressão relacional
  RelationalExpr',  // Relacional (continuação)
  RelationalOp,     // Operador relacional
  AdditiveExpr,     // Expressão aditiva
  AdditiveExpr',    // Aditiva (continuação)
  MultiplicativeExpr,   // Expressão multiplicativa
  MultiplicativeExpr',  // Multiplicativa (continuação)
  UnaryExpr,        // Expressão unária
  PrimaryExpr,      // Expressão primária
  FunctionDecl,     // Declaração de função
  ParamList,        // Lista de parâmetros
  MoreParams,       // Mais parâmetros
  IfStmt,           // Statement if
  ElseClause,       // Cláusula else
  WhileStmt,        // Statement while
  BlockStmt,        // Bloco de statements
  ReturnStmt,       // Statement return
  ExprStmt          // Statement de expressão
}

Total: 34 não-terminais
```

### 2.2 Terminais (T)

#### 2.2.1 Keywords (Palavras Reservadas)

```
KEYWORDS = {
  'let',      // Declaração de variável (block-scoped)
  'const',    // Declaração de constante
  'var',      // Declaração de variável (function-scoped)
  'if',       // Condicional if
  'else',     // Condicional else
  'return',   // Return statement
  'while',    // Loop while
  'function', // Declaração de função
  'true',     // Literal booleano verdadeiro
  'false',    // Literal booleano falso
  'null'      // Literal null
}
```

#### 2.2.2 Operators (Operadores)

```
OPERATORS = {
  // Atribuição
  '=',        // Atribuição simples
  
  // Igualdade
  '==',       // Igualdade (com coerção)
  '===',      // Igualdade estrita (sem coerção)
  '!=',       // Diferente (com coerção)
  '!==',      // Diferente estrito (sem coerção)
  
  // Relacionais
  '<',        // Menor que
  '>',        // Maior que
  '<=',       // Menor ou igual
  '>=',       // Maior ou igual
  
  // Lógicos
  '&&',       // AND lógico
  '||',       // OR lógico
  '!',        // NOT lógico
  
  // Aritméticos
  '+',        // Adição
  '-',        // Subtração / Negação unária
  '*',        // Multiplicação
  '/',        // Divisão
  '%'         // Módulo
}
```

#### 2.2.3 Delimiters (Delimitadores)

```
DELIMITERS = {
  '(',        // Parêntesis esquerdo
  ')',        // Parêntesis direito
  '{',        // Chave esquerda
  '}',        // Chave direita
  ';',        // Ponto e vírgula
  ','         // Vírgula
}
```

#### 2.2.4 Literals (Literais - Tokens Especiais)

```
LITERALS = {
  ID,         // Identificador: [a-zA-Z_][a-zA-Z0-9_]*
  NUMBER,     // Número: [0-9]+ | [0-9]+\.[0-9]+
  STRING      // String: "..." | '...'
}
```

#### 2.2.5 Special (Especiais)

```
SPECIAL = {
  '$',        // Marcador de fim de entrada (EOF)
  'ε'         // Epsilon (string vazia)
}
```

### 2.3 Resumo dos Terminais

```
T = KEYWORDS ∪ OPERATORS ∪ DELIMITERS ∪ LITERALS ∪ SPECIAL

T = {
  // Keywords (11)
  'let', 'const', 'var', 'if', 'else', 'return', 'while', 'function',
  'true', 'false', 'null',
  
  // Operators (18)
  '=', '==', '===', '!=', '!==', '<', '>', '<=', '>=',
  '&&', '||', '!', '+', '-', '*', '/', '%',
  
  // Delimiters (6)
  '(', ')', '{', '}', ';', ',',
  
  // Literals (3)
  ID, NUMBER, STRING,
  
  // Special (2)
  '$', 'ε'
}

Total: 40 terminais
```

## 3. First e Follow

| Não-Terminal | FIRST | Anulável | FOLLOW |
|--------------|-------|----------|--------|
| **Program** | {let, const, var, !, -, ID, NUMBER, STRING, true, false, null, (, {, if, return, function, while} | não | {$} |
| **StatementList** | {let, const, var, !, -, ID, NUMBER, STRING, true, false, null, (, {, if, return, function, while} | não | {}, $} |
| **StatementList'** | {let, const, var, !, -, ID, NUMBER, STRING, true, false, null, (, {, if, return, function, while} | sim | {}, $} |
| **Statement** | {let, const, var, !, -, ID, NUMBER, STRING, true, false, null, (, {, if, return, function, while} | não | {let, const, var, !, -, ID, NUMBER, STRING, true, false, null, (, {, if, return, function, while, }, $, else} |
| **VarDecl** | {let, const, var} | não | {let, const, var, !, -, ID, NUMBER, STRING, true, false, null, (, {, if, return, function, while, }, $, else} |
| **VarKind** | {let, const, var} | não | {ID} |
| **VarInit** | {=} | sim | {;} |
| **Expr** | {!, -, ID, NUMBER, STRING, true, false, null, (} | não | {;, ), ,} |
| **AssignmentExpr** | {!, -, ID, NUMBER, STRING, true, false, null, (} | não | {;, ), ,} |
| **AssignOp'** | {=} | sim | {;, ), ,} |
| **LogicalOrExpr** | {!, -, ID, NUMBER, STRING, true, false, null, (} | não | {=, ;, ), ,} |
| **LogicalOrExpr'** | {\|\|} | sim | {=, ;, ), ,} |
| **LogicalAndExpr** | {!, -, ID, NUMBER, STRING, true, false, null, (} | não | {\|\|, =, ;, ), ,} |
| **LogicalAndExpr'** | {&&} | sim | {\|\|, =, ;, ), ,} |
| **EqualityExpr** | {!, -, ID, NUMBER, STRING, true, false, null, (} | não | {&&, \|\|, =, ;, ), ,} |
| **EqualityExpr'** | {==, ===, !=, !==} | sim | {&&, \|\|, =, ;, ), ,} |
| **EqualityOp** | {==, ===, !=, !==} | não | {!, -, ID, NUMBER, STRING, true, false, null, (} |
| **RelationalExpr** | {!, -, ID, NUMBER, STRING, true, false, null, (} | não | {==, ===, !=, !==, &&, \|\|, =, ;, ), ,} |
| **RelationalExpr'** | {<, >, <=, >=} | sim | {==, ===, !=, !==, &&, \|\|, =, ;, ), ,} |
| **RelationalOp** | {<, >, <=, >=} | não | {!, -, ID, NUMBER, STRING, true, false, null, (} |
| **AdditiveExpr** | {!, -, ID, NUMBER, STRING, true, false, null, (} | não | {<, >, <=, >=, ==, ===, !=, !==, &&, \|\|, =, ;, ), ,} |
| **AdditiveExpr'** | {+, -} | sim | {<, >, <=, >=, ==, ===, !=, !==, &&, \|\|, =, ;, ), ,} |
| **MultiplicativeExpr** | {!, -, ID, NUMBER, STRING, true, false, null, (} | não | {+, -, <, >, <=, >=, ==, ===, !=, !==, &&, \|\|, =, ;, ), ,} |
| **MultiplicativeExpr'** | {*, /, %} | sim | {+, -, <, >, <=, >=, ==, ===, !=, !==, &&, \|\|, =, ;, ), ,} |
| **UnaryExpr** | {!, -, ID, NUMBER, STRING, true, false, null, (} | não | {*, /, %, +, -, <, >, <=, >=, ==, ===, !=, !==, &&, \|\|, =, ;, ), ,} |
| **PrimaryExpr** | {ID, NUMBER, STRING, true, false, null, (} | não | {*, /, %, +, -, <, >, <=, >=, ==, ===, !=, !==, &&, \|\|, =, ;, ), ,} |
| **FunctionDecl** | {function} | não | {let, const, var, !, -, ID, NUMBER, STRING, true, false, null, (, {, if, return, function, while, }, $, else} |
| **ParamList** | {ID} | sim | {)} |
| **MoreParams** | {,} | sim | {)} |
| **IfStmt** | {if} | não | {let, const, var, !, -, ID, NUMBER, STRING, true, false, null, (, {, if, return, function, while, }, $, else} |
| **ElseClause** | {else} | sim | {let, const, var, !, -, ID, NUMBER, STRING, true, false, null, (, {, if, return, function, while, }, $, else} |
| **WhileStmt** | {while} | não | {let, const, var, !, -, ID, NUMBER, STRING, true, false, null, (, {, if, return, function, while, }, $, else} |
| **BlockStmt** | {{} | não | {let, const, var, !, -, ID, NUMBER, STRING, true, false, null, (, {, if, return, function, while, }, $, else} |
| **ReturnStmt** | {return} | não | {let, const, var, !, -, ID, NUMBER, STRING, true, false, null, (, {, if, return, function, while, }, $, else} |
| **ExprStmt** | {!, -, ID, NUMBER, STRING, true, false, null, (} | não | {let, const, var, !, -, ID, NUMBER, STRING, true, false, null, (, {, if, return, function, while, }, $, else} |

---

# Tabela de Parsing LL(1)

| Não-Terminal | let | const | var | if | else | return | while | function | true | false | null | = | == | === | != | !== | < | > | <= | >= | && | \|\| | ! | + | - | * | / | % | ( | ) | { | } | ; | , | ID | NUMBER | STRING | $ |
|--------------|-----|-------|-----|----|----|--------|-------|----------|------|-------|------|---|----|----|----|----|---|---|----|----|----|----|---|---|---|---|---|---|---|---|---|---|---|---|-------|--------|--------|---|
| **Program** | 1 | 1 | 1 | 1 | | 1 | 1 | 1 | 1 | 1 | 1 | | | | | | | | | | | | 1 | | 1 | | | | 1 | | 1 | | | | 1 | 1 | 1 | |
| **StatementList** | 2 | 2 | 2 | 2 | | 2 | 2 | 2 | 2 | 2 | 2 | | | | | | | | | | | | 2 | | 2 | | | | 2 | | 2 | | | | 2 | 2 | 2 | |
| **StatementList'** | 3 | 3 | 3 | 3 | | 3 | 3 | 3 | 3 | 3 | 3 | | | | | | | | | | | | 3 | | 3 | | | | 3 | | 3 | 4 | | | 3 | 3 | 3 | 4 |
| **Statement** | 5 | 5 | 5 | 8 | | 9 | 11 | 10 | 6 | 6 | 6 | | | | | | | | | | | | 6 | | 6 | | | | 6 | | 7 | | | | 6 | 6 | 6 | |
| **VarDecl** | 12 | 12 | 12 | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | |
| **VarKind** | 13 | 14 | 15 | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | |
| **VarInit** | | | | | | | | | | | | 16 | | | | | | | | | | | | | | | | | | | | | 17 | | | | | |
| **Expr** | | | | | | | | | 18 | 18 | 18 | | | | | | | | | | | | 18 | | 18 | | | | 18 | | | | | | 18 | 18 | 18 | |
| **AssignmentExpr** | | | | | | | | | 19 | 19 | 19 | | | | | | | | | | | | 19 | | 19 | | | | 19 | | | | | | 19 | 19 | 19 | |
| **AssignOp'** | | | | | | | | | | | | 20 | | | | | | | | | | | | | | | | | | 21 | | | 21 | 21 | | | | |
| **LogicalOrExpr** | | | | | | | | | 22 | 22 | 22 | | | | | | | | | | | | 22 | | 22 | | | | 22 | | | | | | 22 | 22 | 22 | |
| **LogicalOrExpr'** | | | | | | | | | | | | 24 | | | | | | | | | | 23 | | | | | | | | 24 | | | 24 | 24 | | | | |
| **LogicalAndExpr** | | | | | | | | | 25 | 25 | 25 | | | | | | | | | | | | 25 | | 25 | | | | 25 | | | | | | 25 | 25 | 25 | |
| **LogicalAndExpr'** | | | | | | | | | | | | 27 | | | | | | | | | 26 | 27 | | | | | | | | 27 | | | 27 | 27 | | | | |
| **EqualityExpr** | | | | | | | | | 28 | 28 | 28 | | | | | | | | | | | | 28 | | 28 | | | | 28 | | | | | | 28 | 28 | 28 | |
| **EqualityExpr'** | | | | | | | | | | | | 31 | 29 | 29 | 29 | 29 | | | | | 31 | 31 | | | | | | | | 31 | | | 31 | 31 | | | | |
| **EqualityOp** | | | | | | | | | | | | | 32 | 33 | 34 | 35 | | | | | | | | | | | | | | | | | | | | | | |
| **RelationalExpr** | | | | | | | | | 36 | 36 | 36 | | | | | | | | | | | | 36 | | 36 | | | | 36 | | | | | | 36 | 36 | 36 | |
| **RelationalExpr'** | | | | | | | | | | | | 41 | 41 | 41 | 41 | 41 | 37 | 37 | 37 | 37 | 41 | 41 | | | | | | | | 41 | | | 41 | 41 | | | | |
| **RelationalOp** | | | | | | | | | | | | | | | | | 38 | 39 | 40 | 40 | | | | | | | | | | | | | | | | | | |
| **AdditiveExpr** | | | | | | | | | 42 | 42 | 42 | | | | | | | | | | | | 42 | | 42 | | | | 42 | | | | | | 42 | 42 | 42 | |
| **AdditiveExpr'** | | | | | | | | | | | | 46 | 46 | 46 | 46 | 46 | 43 | 43 | 43 | 43 | 46 | 46 | | 44 | 45 | | | | | 46 | | | 46 | 46 | | | | |
| **MultiplicativeExpr** | | | | | | | | | 47 | 47 | 47 | | | | | | | | | | | | 47 | | 47 | | | | 47 | | | | | | 47 | 47 | 47 | |
| **MultiplicativeExpr'** | | | | | | | | | | | | 51 | 51 | 51 | 51 | 51 | 51 | 51 | 51 | 51 | 51 | 51 | | 51 | 51 | 48 | 49 | 50 | | 51 | | | 51 | 51 | | | | |
| **UnaryExpr** | | | | | | | | | 54 | 54 | 54 | | | | | | | | | | | | 52 | | 53 | | | | 54 | | | | | | 54 | 54 | 54 | |
| **PrimaryExpr** | | | | | | | | | 55 | 56 | 57 | | | | | | | | | | | | | | | | | | 58 | | | | | | 59 | 60 | 61 | |
| **FunctionDecl** | | | | | | | | 62 | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | |
| **ParamList** | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | 64 | | | | | 63 | | | |
| **MoreParams** | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | 65 | | | | 66 | | | | |
| **IfStmt** | | | | 67 | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | |
| **ElseClause** | 69 | 69 | 69 | 69 | 68 | 69 | 69 | 69 | 69 | 69 | 69 | | | | | | | | | | | | 69 | | 69 | | | | 69 | | 69 | 69 | | | 69 | 69 | 69 | 69 |
| **WhileStmt** | | | | | | | 70 | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | |
| **BlockStmt** | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | 71 | | | | | | | |
| **ReturnStmt** | | | | | | 72 | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | |
| **ExprStmt** | | | | | | | | | 73 | 73 | 73 | | | | | | | | | | | | 73 | | 73 | | | | 73 | | | | | | 73 | 73 | 73 | |
