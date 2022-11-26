import ast
from ..common.Utils import is_constant_ident
from ..common.Errors import compile_error, ensure_assign
from ..common.SymbolTable import SymbolTable
from .ProceduralInstructions import ProceduralInstructions
from .ConstantPropagator import ConstantPropagator


class TopLevelProgram(ProceduralInstructions):
    """We supports assignments and input/print calls"""

    def __init__(self, output, symbol_table: SymbolTable, entry_point: str) -> None:
        super().__init__(output, symbol_table)
        self._record_instruction('NOP1', label=entry_point)
        self.__constant_propagator = ConstantPropagator()

    @property
    def instructions(self):
        self._instructions.append((None, '.END'))
        return self._instructions

    def visit_Assign(self, node: ast.Assign):
        # remembering the name of the target
        ensure_assign(node)
        assert isinstance(node.targets[0], ast.Name)
        ident = node.targets[0].id
        self._current_variable = node.targets[0]

        if is_constant_ident(ident):
            # This variable will be defined with .EQUATE, don't load and store
            return

        # Try to propagate constants, it may or may not be possible
        first_seen_now = ident not in self.__constant_propagator.seen_idents
        is_constexpr, _, _ = self.__constant_propagator.add_assign(ident, node.value)

        if first_seen_now and is_constexpr and self._scope_depth == 0:
            # Don't load and store if the value can be statically initialized
            return

        # visiting the left part, now knowing where to store the result
        self.visit(node.value)
        if self._should_save:
            self._access_memory(node.targets[0], 'STWA')
        else:
            self._should_save = True

        self._current_variable = None

    def _access_memory(self, node: ast.expr, instruction: str, label=None):
        if isinstance(node, ast.Constant):
            self._record_instruction(f'{instruction} {node.value},i', label)
        elif isinstance(node, ast.Name):
            addr_mode = 'i' if is_constant_ident(node.id) else 'd'
            assert self._ident_labels is not None
            ident_label = self._ident_labels[node.id]
            self._record_instruction(f'{instruction} {ident_label},{addr_mode}', label)
        else:
            compile_error(node, f"Cannot access memory of {node}")
