import ast
from pathlib import Path

SRC = Path(__file__).parent.parent / "src"


def test_no_module_imports_the_backend_package():
    """The MCP server reaches the backend over HTTP only (ADR 0001)."""
    offenders = []
    for path in SRC.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            offenders += [f"{path.name}: {n}" for n in names if n.split(".")[0] == "saint_elmo_backend"]

    assert offenders == []
