# label: Filesystem
"""
Comandos: dir, file, write, cd, up
Sandbox: ./fs_output/
"""
import os

BASE = os.path.abspath("fs_output")

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
        os.makedirs(BASE, exist_ok=True)
        self.cwd = BASE
        self.log = []

    def _safe_path(self, name):
        full = os.path.abspath(os.path.join(self.cwd, name))
        if not full.startswith(BASE):
            raise PermissionError(f"caminho fora da sandbox: {name}")
        return full

    def _rel(self, path):
        return os.path.relpath(path, BASE) or "."

    def visit_Program(self, node):
        for child in node.children:
            self.visit(child)
        return "\n".join(self.log) if self.log else "(sem operações)"

    def visit_CmdList(self, node):
        if node.children and node.children[0].label != "ε":
            for child in node.children:
                self.visit(child)
        return ""

    def visit_Cmd(self, node):
        kw = node.children[0].lexema
        if kw == "dir":
            name = node.children[1].lexema
            path = self._safe_path(name)
            os.makedirs(path, exist_ok=True)
            self.log.append(f"📁 criou pasta {self._rel(path)}/")
        elif kw == "file":
            name = node.children[1].lexema
            path = self._safe_path(name)
            open(path, "a").close()
            self.log.append(f"📄 criou ficheiro {self._rel(path)}")
        elif kw == "write":
            name = node.children[1].lexema
            text = node.children[2].lexema[1:-1]
            path = self._safe_path(name)
            with open(path, "w") as f:
                f.write(text)
            self.log.append(f"✏️  escreveu em {self._rel(path)}: {text!r}")
        elif kw == "cd":
            name = node.children[1].lexema
            path = self._safe_path(name)
            if not os.path.isdir(path):
                raise FileNotFoundError(f"pasta não existe: {name}")
            self.cwd = path
            self.log.append(f"→ entrou em {self._rel(path)}/")
        elif kw == "up":
            if self.cwd == BASE:
                raise PermissionError("já estás na raiz da sandbox")
            self.cwd = os.path.dirname(self.cwd)
            self.log.append(f"← voltou a {self._rel(self.cwd)}/")
        return ""