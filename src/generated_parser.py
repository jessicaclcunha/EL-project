"""
Parser recursivo descendente — gerado automaticamente pelo Grammar Playground.

Gramática:
    Program -> StmtList
    StmtList -> Stmt StmtListR
    StmtListR -> SEMI Stmt StmtListR | ε
    Stmt -> ID ASSIGN Expr
    Expr -> Term ExprR
    ExprR -> PLUS Term ExprR | ε
    Term -> ID | NUMBER

Símbolo inicial: Program
"""

import re
import sys

# ===================================================================
# Árvore de derivação
# ===================================================================

class TreeNode:
    """Nó da árvore de derivação."""

    def __init__(self, label, children=None, token_value=None):
        self.label = label             # nome do NT ou terminal
        self.children = children or [] # filhos (TreeNode)
        self.token_value = token_value # valor do token (só para folhas)

    def is_leaf(self):
        return not self.children

    def print_tree(self, prefix="", is_last=True):
        connector = "└── " if is_last else "├── "
        if self.token_value is not None:
            display = f"{self.label}: {self.token_value!r}"
        else:
            display = self.label
        print(prefix + connector + display)
        extension = "    " if is_last else "│   "
        for i, child in enumerate(self.children):
            child.print_tree(prefix + extension, is_last=(i == len(self.children) - 1))

# ===================================================================
# Lexer
# ===================================================================

class Token:
    def __init__(self, type_, value, line):
        self.type = type_
        self.value = value
        self.line = line

    def __repr__(self):
        return f"Token({self.type!r}, {self.value!r})"


class Lexer:
    def __init__(self, source):
        self.source = source
        self.tokens = []
        self._tokenize()

    def _tokenize(self):
        token_spec = [
            ('ID', r'[a-zA-Z_][a-zA-Z0-9_]*'),
            ('NUMBER', r'[0-9]+'),
            ('PLUS', r'\+'),
            ('SEMI', r';'),
            ('ASSIGN', r':='),
        ]
        pos = 0
        line = 1
        while pos < len(self.source):
            # Ignorar espaços e tabs
            m = re.match(r"[ \t]+", self.source[pos:])
            if m:
                pos += m.end()
                continue
            # Newlines
            m = re.match(r"\n", self.source[pos:])
            if m:
                line += 1
                pos += 1
                continue
            # Tentar cada padrão de token
            matched = False
            for name, pattern in token_spec:
                m = re.match(pattern, self.source[pos:])
                if m:
                    self.tokens.append(Token(name, m.group(), line))
                    pos += m.end()
                    matched = True
                    break
            if not matched:
                raise SyntaxError(
                    f"Linha {line}: carácter inesperado {self.source[pos]!r}"
                )
        self.tokens.append(Token("$", "", line))

# ===================================================================
# Parser recursivo descendente
# ===================================================================

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def current(self):
        """Token atual (lookahead)."""
        return self.tokens[self.pos]

    def match(self, expected_type):
        """Consome o token atual se for do tipo esperado."""
        tok = self.current()
        if tok.type == expected_type:
            self.pos += 1
            return TreeNode(expected_type, token_value=tok.value)
        else:
            raise SyntaxError(
                f"Linha {tok.line}: esperado {expected_type!r}, "
                f"encontrado {tok.type!r} ({tok.value!r})"
            )

    def match_value(self, expected_value, label):
        """Consome o token atual se tiver o valor esperado (para terminais inline)."""
        tok = self.current()
        if tok.value == expected_value:
            self.pos += 1
            return TreeNode(label, token_value=tok.value)
        else:
            raise SyntaxError(
                f"Linha {tok.line}: esperado {expected_value!r}, "
                f"encontrado {tok.value!r}"
            )

    def parse_Program(self):
        """Produção: Program -> StmtList"""
        tok = self.current()
        if tok.type == 'ID':
            # Program -> StmtList  [lookahead: {ID}]
            children = []
            children.append(self.parse_StmtList())
            return TreeNode('Program', children=children)
        else:
            raise SyntaxError(
                f"Linha {tok.line}: token inesperado {tok.type!r} "
                f"({tok.value!r}) ao expandir Program"
            )

    def parse_StmtList(self):
        """Produção: StmtList -> Stmt StmtListR"""
        tok = self.current()
        if tok.type == 'ID':
            # StmtList -> Stmt StmtListR  [lookahead: {ID}]
            children = []
            children.append(self.parse_Stmt())
            children.append(self.parse_StmtListR())
            return TreeNode('StmtList', children=children)
        else:
            raise SyntaxError(
                f"Linha {tok.line}: token inesperado {tok.type!r} "
                f"({tok.value!r}) ao expandir StmtList"
            )

    def parse_StmtListR(self):
        """Produção: StmtListR -> SEMI Stmt StmtListR | ε"""
        tok = self.current()
        if tok.type == 'SEMI':
            # StmtListR -> SEMI Stmt StmtListR  [lookahead: {SEMI}]
            children = []
            children.append(self.match('SEMI'))
            children.append(self.parse_Stmt())
            children.append(self.parse_StmtListR())
            return TreeNode('StmtListR', children=children)
        else:
            # StmtListR -> ε  [lookahead ∉ FIRST → FOLLOW(StmtListR): {$}]
            return TreeNode('StmtListR', children=[TreeNode("ε")])

    def parse_Stmt(self):
        """Produção: Stmt -> ID ASSIGN Expr"""
        tok = self.current()
        if tok.type == 'ID':
            # Stmt -> ID ASSIGN Expr  [lookahead: {ID}]
            children = []
            children.append(self.match('ID'))
            children.append(self.match('ASSIGN'))
            children.append(self.parse_Expr())
            return TreeNode('Stmt', children=children)
        else:
            raise SyntaxError(
                f"Linha {tok.line}: token inesperado {tok.type!r} "
                f"({tok.value!r}) ao expandir Stmt"
            )

    def parse_Expr(self):
        """Produção: Expr -> Term ExprR"""
        tok = self.current()
        if tok.type == 'ID' or tok.type == 'NUMBER':
            # Expr -> Term ExprR  [lookahead: {ID, NUMBER}]
            children = []
            children.append(self.parse_Term())
            children.append(self.parse_ExprR())
            return TreeNode('Expr', children=children)
        else:
            raise SyntaxError(
                f"Linha {tok.line}: token inesperado {tok.type!r} "
                f"({tok.value!r}) ao expandir Expr"
            )

    def parse_ExprR(self):
        """Produção: ExprR -> PLUS Term ExprR | ε"""
        tok = self.current()
        if tok.type == 'PLUS':
            # ExprR -> PLUS Term ExprR  [lookahead: {PLUS}]
            children = []
            children.append(self.match('PLUS'))
            children.append(self.parse_Term())
            children.append(self.parse_ExprR())
            return TreeNode('ExprR', children=children)
        else:
            # ExprR -> ε  [lookahead ∉ FIRST → FOLLOW(ExprR): {$, SEMI}]
            return TreeNode('ExprR', children=[TreeNode("ε")])

    def parse_Term(self):
        """Produção: Term -> ID | NUMBER"""
        tok = self.current()
        if tok.type == 'ID':
            # Term -> ID  [lookahead: {ID}]
            children = []
            children.append(self.match('ID'))
            return TreeNode('Term', children=children)
        elif tok.type == 'NUMBER':
            # Term -> NUMBER  [lookahead: {NUMBER}]
            children = []
            children.append(self.match('NUMBER'))
            return TreeNode('Term', children=children)
        else:
            raise SyntaxError(
                f"Linha {tok.line}: token inesperado {tok.type!r} "
                f"({tok.value!r}) ao expandir Term"
            )

    def parse(self):
        """Ponto de entrada — parse do símbolo inicial."""
        tree = self.parse_Program()
        if self.current().type != "$":
            tok = self.current()
            raise SyntaxError(
                f"Linha {tok.line}: tokens extra após o fim do programa: "
                f"{tok.type!r} ({tok.value!r})"
            )
        return tree


# ===================================================================
# Main
# ===================================================================

def main():
    if len(sys.argv) > 1:
        with open(sys.argv[1], encoding="utf-8") as f:
            source = f.read()
    else:
        source = input("Frase a analisar: ")

    lex = Lexer(source)
    print("Tokens:", lex.tokens)
    print()

    parser = Parser(lex.tokens)
    try:
        tree = parser.parse()
        print("Árvore de derivação:")
        tree.print_tree()
    except SyntaxError as e:
        print(f"Erro: {e}")


if __name__ == "__main__":
    main()
