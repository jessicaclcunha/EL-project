# label: Contar nós da árvore
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
        self.counts = {}
        self.total = 0

    def visit(self, node):
        self.total += 1
        label = node.label if node.lexema is None else f"T:{node.label}"
        self.counts[label] = self.counts.get(label, 0) + 1
        if node.lexema is not None:
            return node.lexema
        if node.label == "ε":
            return ""
        method = getattr(self, "visit_" + node.label, self.generic_visit)
        return method(node)

    def generic_visit(self, node):
        for child in node.children:
            self.visit(child)
        lines = [f"Total de nós: {self.total}", ""]
        for label, n in sorted(self.counts.items()):
            lines.append(f"  {label}: {n}")
        return "\n".join(lines)