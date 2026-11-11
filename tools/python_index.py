"""File: Emits actual Python AST declaration/argument/assignment locations for the source index.

main parses one repository-owned source path. No supplied code executes; see docs/code-index.md.
"""

import ast
import json
import sys
from pathlib import Path


def main():
    """Return deterministic physical declaration/parameter/variable lines without importing code."""
    tree = ast.parse(Path(sys.argv[1]).read_text(encoding="utf-8"))
    symbols = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            symbols.append(
                {
                    "line": node.lineno,
                    "kind": "class" if isinstance(node, ast.ClassDef) else "function",
                    "name": node.name,
                }
            )
        elif isinstance(node, ast.arg):
            symbols.append({"line": node.lineno, "kind": "parameter", "name": node.arg})
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            symbols.append({"line": node.lineno, "kind": "variable", "name": node.id})
    symbols.sort(key=lambda item: (item["line"], item["kind"], item["name"]))
    print(json.dumps(symbols))


if __name__ == "__main__":
    main()
