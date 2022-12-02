import ast
from ..common.Utils import is_constant_ident, is_array_ident
from ..common.Errors import compile_error
from ..common.SymbolTable import SymbolTable
from .ProceduralInstructions import ProceduralInstructions
from .ConstantPropagator import ConstantPropagator


class TopLevelProgram(ProceduralInstructions):
    """We supports assignments and input/print calls"""

    def __init__(self, symbol_table: SymbolTable, entry_point: str) -> None:
        super().__init__(symbol_table)
        self._record_instruction('NOP1', label=entry_point)
        self.__constant_propagator = ConstantPropagator()

    def finalize(self):
        self._instructions.append((None, '.END'))
        return self._instructions

    def visit_Assign(self, node: ast.Assign):
        ident, target, subscript = super().visit_Assign(node)

        if is_constant_ident(ident):
            # This variable will be defined with .EQUATE, don't load and store
            self._variable_names.add(ident)
            return

        if is_array_ident(ident):
            if ident in self._variable_names:
                # Don't allow reassignment
                if subscript is None:
                    compile_error(node, "Cannot use array as integer type")
            else:
                self._variable_names.add(ident)
                return
        else:
            # Try to propagate constants, it may or may not be possible
            first_seen_now = ident not in self.__constant_propagator.seen_idents
            is_constexpr, _, _ = self.__constant_propagator.add_assign(ident, node.value)

            if first_seen_now and is_constexpr and self._scope_depth == 0:
                # Don't load and store if the value can be statically initialized
                self._variable_names.add(ident)
                return

        self._assign_store(node, ident, target, subscript)

    def _access_memory(self, node: ast.expr, instruction: str, label=None):
        super()._access_memory(node, instruction, label)
        if isinstance(node, ast.Constant):
            self._record_instruction(f'{instruction} {node.value},i', label)
        elif isinstance(node, (ast.Name, ast.Subscript)):
            if isinstance(node, ast.Subscript):
                addr_mode = 'x'
                self._access_memory(node.slice, 'LDWX')
                self._record_instruction('ASLX')
                assert isinstance(node.value, ast.Name)
                node = node.value
            else:
                addr_mode = 'i' if is_constant_ident(node.id) else 'd'

            assert self._ident_labels is not None
            ident_label = self._ident_labels[node.id]
            self._record_instruction(f'{instruction} {ident_label},{addr_mode}', label)
        else:
            compile_error(node, f"Cannot access memory of {node}")
