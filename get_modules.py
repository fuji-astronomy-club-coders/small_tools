import ast
import pathlib

modules = set()

for py in pathlib.Path(".").rglob("*.py"):
    tree = ast.parse(py.read_text(encoding="UTF-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                modules.add(n.name.split('.')[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                modules.add(node.module.split('.')[0])

print(modules)
