import ast
from ..common.Errors import compile_error, ensure_assign
from ..common.SymbolTable import SymbolTable
from ..common.Utils import is_constant_ident
# from .ConstantPropagator import ConstantPropagator
from .ProceduralInstructions import ProceduralInstructions


class FunctionDefinition(ProceduralInstructions):

    def __init__(self, output,
                 global_symbols: SymbolTable,
                 function_labels: SymbolTable) -> None:
        super().__init__(output, global_symbols, function_labels)
        self.__current_func: str | None = None
        self.__function_returned = False
        self.__local_variables: dict[str, dict[str, tuple[str, int]]] = {}
        self.__global_variables = global_symbols
        self.__function_labels = function_labels

    def visit(self, node: ast.AST):
        # Do not visit anything that is not a function or within a function
        if isinstance(node, (ast.Module, ast.FunctionDef)) or self.__current_func is not None:
            return super().visit(node)

    def __allocate_var(self, ident: str):
        key = f'{self.__current_func}{ident}'
        if key in self.__function_labels:
            return
        label = self.__function_labels.lookup_or_create(key)
        assert self.__current_func is not None
        self.__local_variables[self.__current_func][ident] = (label, self.__stack_space)
        self.__stack_space += 2
        yield key

    def __try_allocate_vars(self, node: ast.AST):
        assert self.__current_func is not None
        if isinstance(node, ast.While):
            for stmt in node.body:
                yield from self.__try_allocate_vars(stmt)
        elif isinstance(node, ast.If):
            for stmt in node.body + node.orelse:
                yield from self.__try_allocate_vars(stmt)
        elif isinstance(node, ast.Assign):
            ensure_assign(node)
            assert isinstance(node.targets[0], ast.Name)
            yield from self.__allocate_var(node.targets[0].id)
        elif isinstance(node, (ast.Return, ast.Call, ast.Expr)):
            pass
        else:
            assert 0, f"{node}"

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
        # self.__constant_propagator = ConstantPropagator()
        func_label = self.__function_labels.lookup_or_create(self.__current_func)

        var_names = []
        self.__local_variables[self.__current_func] = {}
        for arg in node.args.args:
            if arg in self.__local_variables[self.__current_func]:
                compile_error(arg, "Multiple parameters with same name")
            var_names.extend(self.__allocate_var(arg.arg))

        for stmt in node.body:
            var_names.extend(self.__try_allocate_vars(stmt))

        # Prepare stack (and extract names for printing tag information)
        self._record_instruction(f"; Function {self.__current_func}")
        locals = (self.__function_labels[self.__current_func+s]
                  for s in self.__local_variables[self.__current_func])
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
        ensure_assign(node)
        assert isinstance(node.targets[0], ast.Name)
        # TODO: Propagte constants

        self._current_variable = node.targets[0]

        self.visit(node.value)
        if self._should_save:
            self._access_memory(node.targets[0], 'STWA')
        else:
            self._should_save = True

        self._current_variable = None

    def _access_memory(self, node: ast.expr, instruction: str, label=None):
        if self.__current_func is None:
            return
        if isinstance(node, ast.Constant):
            self._record_instruction(f'{instruction} {node.value},i', label)
        elif isinstance(node, ast.Name):
            if self.__current_func is None:
                return
            curr_func = self.__local_variables[self.__current_func]
            if node.id in curr_func:
                # Local variable
                var_label, _ = curr_func[node.id]
                self._record_instruction(f'{instruction} {var_label},s', label)

            elif node.id in self.__global_variables:
                # Global variable
                addr_mode = 'i' if is_constant_ident(node.id) else 'd'
                assert self._ident_labels is not None
                ident_label = self._ident_labels[node.id]
                self._record_instruction(f'{instruction} {ident_label},{addr_mode}', label)

        else:
            compile_error(node, f"Cannot access memory of {node}")

    @property
    def local_variables(self): return self.__local_variables
