import ast
from ..common.Errors import compile_error, ensure_assign
from ..common.Types import VariableIdentifier, InitKind
from ..common.Utils import is_constant_ident, next_name_generator
from ..common.SymbolTable import SymbolTable
from .ConstantPropagator import ConstantPropagator


class GlobalVariableExtraction(ast.NodeVisitor):
    """We extract all the left hand side of the global (top-level) assignments"""

    def __init__(self) -> None:
        super().__init__()
        self.__results: list[VariableIdentifier] = list()
        self.__constant_propagator = ConstantPropagator()
        self.__ident_label_generator = SymbolTable(next_name_generator(8))

    def visit(self, node: ast.AST):
        # Do not visit anything that is within a function, only consider globals
        if not isinstance(node, ast.FunctionDef):
            return super().visit(node)

    def visit_Assign(self, node: ast.Assign):
        ensure_assign(node)
        assert isinstance(node.targets[0], ast.Name)
        ident = node.targets[0].id
        self.__ident_label_generator.lookup_or_create(ident)

        first_seen_now = ident not in self.__constant_propagator.seen_idents
        is_constexpr, _, const_val = self.__constant_propagator.add_assign(ident, node.value)

        if is_constant_ident(ident):
            if not first_seen_now:
                compile_error(node, f"Cannot reassign to constant \"{ident}\"")
            if not is_constexpr:
                compile_error(node, f"Constant {ident} did not have compile-time expression")
            self.__results.append((ident, InitKind.EQUATE, const_val))
        elif first_seen_now:
            if is_constexpr:
                self.__results.append((ident, InitKind.WORD, const_val))
            else:
                self.__results.append((ident, InitKind.BLOCK, None))

    @property
    def results(self): return self.__results

    @property
    def symbol_table(self): return self.__ident_label_generator
