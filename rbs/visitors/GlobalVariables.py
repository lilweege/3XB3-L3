import ast
from ..common.Errors import ensure_assign


class GlobalVariableExtraction(ast.NodeVisitor):
    """We extract all the left hand side of the global (top-level) assignments"""

    def __init__(self) -> None:
        super().__init__()
        self.results: set[str] = set()

    def visit_Assign(self, node: ast.Assign):
        ensure_assign(node)
        assert isinstance(node.targets[0], ast.Name)
        self.results.add(node.targets[0].id)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """We do not visit function definitions, they are not global by definition"""
        pass
