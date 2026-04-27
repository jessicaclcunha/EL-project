# label: Avaliador de expressões
class Visitor:
    def visit(self, node):
        if node.lexema is not None:
            return node.lexema
        if node.label == "ε":
            return ""
        method = getattr(self, "visit_" + node.label, self.generic_visit)
        return method(node)
    def generic_visit(self, node):
        parts = []
        for child in node.children:
            r = self.visit(child)
            if r is not None and str(r).strip() != "":
                parts.append(str(r))
        return " ".join(parts)

class CodeGen(Visitor):
    def __init__(self):
        self.env = {}
        self.log = []

    def visit_Program(self, node):
        self.visit(node.children[0])
        return "\n".join(self.log)

    def visit_StmtList(self, node):
        self.visit(node.children[0])
        self.visit(node.children[1])

    def visit_StmtListR(self, node):
        if node.children[0].label == "ε":
            return
        self.visit(node.children[1])
        self.visit(node.children[2])

    def visit_Stmt(self, node):
        var  = node.children[0].lexema
        val  = self.visit(node.children[2])
        self.env[var] = val
        self.log.append(f"{var} = {val}")

    def visit_Expr(self, node):
        val  = self.visit(node.children[0])
        rest = self.visit(node.children[1])
        return val if rest is None else val + rest

    def visit_ExprR(self, node):
        if node.children[0].label == "ε":
            return None
        term = self.visit(node.children[1])
        rest = self.visit(node.children[2])
        total = term
        if rest is not None:
            total = total + rest
        return total

    def visit_Term(self, node):
        tok = node.children[0].lexema
        try:
            return int(tok)
        except ValueError:
            return self.env.get(tok, 0)