import ast
from ..common.Errors import compile_error, ensure_assign, ensure_array
from ..common.SymbolTable import SymbolTable
from ..common.Utils import is_constant_ident, is_array_ident, assign_from_augassign
from ..common.Types import CallFrame, LocalVariable
# from .ConstantPropagator import ConstantPropagator
from .ProceduralInstructions import ProceduralInstructions
from collections import defaultdict


class FunctionDefinition(ProceduralInstructions):

    def __init__(self,
                 global_symbols: SymbolTable,
                 function_labels: SymbolTable) -> None:
        super().__init__(global_symbols, function_labels)
        self.__current_func: str | None = None
        self.__function_returned = False
        self.__local_variables: dict[str, CallFrame] = defaultdict(CallFrame)
        self.__global_variables = global_symbols
        self.__global_names = set(self.__global_variables)
        self.__function_labels = function_labels

    def visit(self, node: ast.AST):
        # Do not visit anything that is not a function or within a function
        if isinstance(node, (ast.Module, ast.FunctionDef)) or self.__current_func is not None:
            return super().visit(node)

    def __allocate_var(self, ident: str, size: int = 1):
        key = f'{self.__current_func}{ident}'
        if key in self.__function_labels:
            return
        label = self.__function_labels.lookup_or_create(key)
        assert self.__current_func is not None

        var_defn: LocalVariable = (label, self.__stack_space, size)
        self.__local_variables[self.__current_func].locals[ident] = var_defn
        self.__stack_space += 2 * size
        self.__local_variables[self.__current_func].stack_space = self.__stack_space

    def __try_allocate_vars(self, node: ast.AST):
        assert self.__current_func is not None
        if isinstance(node, ast.While):
            for stmt in node.body:
                self.__try_allocate_vars(stmt)
            return
        elif isinstance(node, ast.If):
            for stmt in node.body + node.orelse:
                self.__try_allocate_vars(stmt)
            return
        elif isinstance(node, (ast.AugAssign, ast.Assign)):
            if isinstance(node, ast.AugAssign):
                node = assign_from_augassign(node)
            assert isinstance(node, ast.Assign)
            ensure_assign(node)
            target = node.targets[0]
            if isinstance(target, ast.Name):
                arr_size = 1 if not is_array_ident(target.id) else ensure_array(node.value)
                self.__allocate_var(target.id, arr_size)
                return
            elif isinstance(target, ast.Subscript):
                return
            node = target
        elif isinstance(node, (ast.Return, ast.Call, ast.Expr)):
            return

        if not isinstance(node, self.supported_nodes):
            compile_error(node, f'Unsupported AST node kind "{type(node).__name__}"')
        else:
            assert False, "Unreachable"

    def visit_Return(self, node: ast.Return):
        # Store return values in A if applicable
        if node.value is not None:
            self._access_memory(node.value, 'LDWA')
        self._record_instruction(f'ADDSP {self.__stack_space},i ; pop {self.__locals}')
        self._record_instruction('RET')
        self.__function_returned = True

    def visit_FunctionDef(self, node: ast.FunctionDef):
        super().visit_FunctionDef(node)

        self.__stack_space = 0
        self.__current_func = node.name
        self.__function_returned = False
        self._variable_names = self.__global_names.copy()
        # self.__constant_propagator = ConstantPropagator()
        func_label = self.__function_labels.lookup_or_create(self.__current_func)

        for arg in node.args.args:
            # Assume parameters are all ints, since we disallow arrays as arguments
            if arg.arg in self.__local_variables[self.__current_func].locals:
                compile_error(arg, "Multiple parameters with same name")
            self.__allocate_var(arg.arg)
            self._variable_names.add(arg.arg)

        for stmt in node.body:
            self.__try_allocate_vars(stmt)

        # Prepare stack (and extract names for printing tag information)
        self._record_instruction(f"; Function {self.__current_func}")
        locals = (self.__function_labels[self.__current_func+s]
                  for s in self.__local_variables[self.__current_func].locals)
        self.__locals = f'{" ".join("#"+name for name in locals)}'
        instruction = f'SUBSP {self.__stack_space},i ; push {self.__locals}'
        self._record_instruction(instruction, label=func_label)

        # Emit body
        for stmt in node.body:
            self.visit(stmt)

        # Clean up stack and return (if didn't explicitly return)
        if not self.__function_returned:
            self._record_instruction(f'ADDSP {self.__stack_space},i ; pop {self.__locals}')
            self._record_instruction('RET')

        self.__current_func = None

    def visit_Assign(self, node: ast.Assign):
        ident, target, subscript = super().visit_Assign(node)

        # TODO: Propagte constants
        if is_array_ident(ident):
            if ident in self._variable_names:
                # Don't allow reassignment
                if subscript is None:
                    compile_error(node, "Cannot use array as integer type")
            else:
                self._variable_names.add(ident)
                return

        self._assign_store(node, ident, target, subscript)

    def _access_memory(self, node: ast.expr, instruction: str, label=None):
        super()._access_memory(node, instruction, label)
        if self.__current_func is None:
            return
        if isinstance(node, ast.Constant):
            self._record_instruction(f'{instruction} {node.value},i', label)
        elif isinstance(node, (ast.Name, ast.Subscript)):
            curr_func = self.__local_variables[self.__current_func].locals

            if isinstance(node, ast.Name):
                ident = node.id
            else:
                assert isinstance(node.value, ast.Name)
                ident = node.value.id

            if ident in curr_func:
                # Local variable
                if isinstance(node, ast.Subscript):
                    addr_mode = 'sx'
                    self._access_memory(node.slice, 'LDWX')
                    self._record_instruction('ASLX')
                else:
                    addr_mode = 's'

                ident_label, _, _ = curr_func[ident]

            elif ident in self.__global_variables:
                # Global variable
                if isinstance(node, ast.Subscript):
                    addr_mode = 'x'
                    self._access_memory(node.slice, 'LDWX')
                    self._record_instruction('ASLX')
                    assert isinstance(node.value, ast.Name)
                    node = node.value
                else:
                    assert isinstance(node, ast.Name)
                    addr_mode = 'i' if is_constant_ident(node.id) else 'd'

                assert self._ident_labels is not None
                ident_label = self._ident_labels[node.id]

            self._record_instruction(f'{instruction} {ident_label},{addr_mode}', label)

        else:
            compile_error(node, f"Cannot access memory of {node}")

    @property
    def local_variables(self): return self.__local_variables
