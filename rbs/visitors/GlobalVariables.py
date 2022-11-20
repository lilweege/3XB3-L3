import ast
from ..common.Errors import compile_error, ensure_assign
from ..common.Types import VariableIdentifier, InitKind
from ..common.Utils import is_constant_ident, next_name_generator
from .ConstantPropagator import ConstantPropagator
from .SymbolGenerator import SymbolGenerator


class GlobalVariableExtraction(ast.NodeVisitor):
    """We extract all the left hand side of the global (top-level) assignments"""

    def __init__(self) -> None:
        super().__init__()
        self.results: set[VariableIdentifier] = set()
        self.__constant_propagator = ConstantPropagator()
        self.__ident_label_generator = SymbolGenerator(next_name_generator(8))

    def visit_Assign(self, node: ast.Assign):
        ensure_assign(node)
        assert isinstance(node.targets[0], ast.Name)
        ident = node.targets[0].id
        ident_label = self.__ident_label_generator.lookup_or_create(node.targets[0].id)

        first_seen_now = ident not in self.__constant_propagator.seen_idents
        is_constexpr, _, const_val = self.__constant_propagator.add_assign(ident, node.value)

        if is_constant_ident(ident):
            if not first_seen_now:
                compile_error(node, f"Cannot reassign to constant \"{ident_label}\"")
            if not is_constexpr:
                compile_error(node, f"Constant {ident_label} did not have compile-time expression")
            self.results.add((ident_label, InitKind.EQUATE, const_val))
        elif first_seen_now:
            if is_constexpr:
                self.results.add((ident_label, InitKind.WORD, const_val))
            else:
                self.results.add((ident_label, InitKind.BLOCK, None))

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """We do not visit function definitions, they are not global by definition"""
        pass
