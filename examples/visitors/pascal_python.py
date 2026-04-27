# label: Pascal → Python
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
    def visit_Program(self, node):
        return self.visit(node.children[0])

    def visit_StmtList(self, node):
        stmt = self.visit(node.children[0])
        rest = self.visit(node.children[1])
        return stmt + ("\n" + rest if rest else "")

    def visit_StmtListR(self, node):
        if node.children[0].label == "ε":
            return ""
        stmt = self.visit(node.children[1])
        rest = self.visit(node.children[2])
        return stmt + ("\n" + rest if rest else "")

    def visit_Stmt(self, node):
        var  = node.children[0].lexema
        expr = self.visit(node.children[2])
        return f"{var} = {expr}"

    def visit_Expr(self, node):
        return self.generic_visit(node)

    def visit_ExprR(self, node):
        if node.children[0].label == "ε":
            return ""
        return self.generic_visit(node)

    def visit_Term(self, node):
        return node.children[0].lexema