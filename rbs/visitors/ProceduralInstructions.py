import ast
from ..common.Errors import compile_error, ensure_args, ensure_condition, ensure_assign
from ..common.Types import LabeledInstruction
from ..common.Utils import reversed_next_name_generator, assign_from_augassign
from ..common.SymbolTable import SymbolTable
from abc import ABC, abstractmethod


class ProceduralInstructions(ABC, ast.NodeVisitor):

    def __init__(self,
                 symbol_table: SymbolTable | None,
                 label_table: SymbolTable | None = None) -> None:
        super().__init__()
        self._instructions: list[LabeledInstruction] = list()
        self._should_save = True
        self._current_variable: ast.expr | None = None
        self._scope_depth = 0
        self.__label_id = 0
        self._ident_labels = symbol_table
        self.__label_generator = label_table if label_table else \
            SymbolTable(reversed_next_name_generator(8))
        # Branch labels and functions share the same generator so they never overlap
        self._function_definitions: dict[str, int] = {}
        self._variable_names: set[str] = set()

    supported_nodes = (
        ast.Module,
        ast.FunctionDef,
        ast.Constant,
        ast.Name,
        ast.AugAssign,
        ast.Assign,
        ast.BinOp,
        ast.Call,
        ast.If,
        ast.While,
        ast.Return,
        ast.Expr,
    )

    def visit(self, node: ast.AST):
        if not isinstance(node, self.supported_nodes):
            compile_error(node, f'Unsupported AST node kind "{type(node).__name__}"')
        return super().visit(node)

    def visit_Constant(self, node: ast.Constant):
        self._access_memory(node, 'LDWA')

    def visit_Name(self, node: ast.Name):
        self._access_memory(node, 'LDWA')

    def visit_BinOp(self, node: ast.BinOp):
        self._access_memory(node.left, 'LDWA')
        if isinstance(node.op, ast.Add):
            self._access_memory(node.right, 'ADDA')
        elif isinstance(node.op, ast.Sub):
            self._access_memory(node.right, 'SUBA')
        else:
            compile_error(node, f'Unsupported binary operator: {type(node.op).__name__}')

    def visit_Call(self, node: ast.Call):
        assert isinstance(node.func, ast.Name)
        # TODO: Implement unnamed expressions as arguments
        match node.func.id:
            case 'exit':
                self._record_instruction('STOP')

            case 'int':
                # Let's visit whatever is casted into an int
                ensure_args(node, 1)
                self.visit(node.args[0])

            case 'input':
                # We are only supporting integers for now
                ensure_args(node, 0)
                assert self._current_variable is not None
                assert isinstance(self._current_variable, ast.Name)
                self._variable_names.add(self._current_variable.id)
                self._access_memory(self._current_variable, 'DECI')
                self._should_save = False  # DECI already save the value in memory

            case 'print':
                # We are only supporting integers for now
                ensure_args(node, 1)
                self._access_memory(node.args[0], 'DECO')

            case func_name:
                if func_name not in self._function_definitions:
                    compile_error(node, f'Unsupported function call: {node.func.id}')
                num_args = self._function_definitions[func_name]
                ensure_args(node, num_args)

                # Push arguments onto the stack before calling
                for idx, argument in enumerate(node.args):
                    stack_offset = -4 - idx * 2
                    self._access_memory(argument, 'LDWA')
                    self._record_instruction(f'STWA {stack_offset},s')

                func_label = self.__label_generator.lookup_or_create(func_name)
                self._record_instruction(f'CALL {func_label}')

                # The value of the function (if any) will already be in the A register

    # Map from node types to their corresponding "inverted" mnemonic
    __inv_comparisons = {
        ast.Lt:    'BRGE',  # '<'  in the code means we branch if '>='
        ast.LtE:   'BRGT',  # '<=' in the code means we branch if '>'
        ast.Gt:    'BRLE',  # '>'  in the code means we branch if '<='
        ast.GtE:   'BRLT',  # '>=' in the code means we branch if '<'
        ast.Eq:    'BRNE',
        ast.NotEq: 'BREQ',
    }

    def __branch_compare(self, node: ast.If | ast.While, entry_label: str | None, exit_label: str):
        '''Common logic shared between if and while statements'''
        ensure_condition(node.test)
        assert isinstance(node.test, ast.Compare)
        cmp: ast.Compare = node.test

        lhs, rhs = cmp.left, cmp.comparators[0]
        self._access_memory(lhs, 'LDWA', label=entry_label)
        self._access_memory(rhs, 'CPWA')

        cmp_typ = type(cmp.ops[0])
        if cmp_typ not in self.__inv_comparisons:
            compile_error(node, f"Unsuppored comparison '{cmp_typ.__name__}'")

        self._record_instruction(f'{self.__inv_comparisons[cmp_typ]} {exit_label}')

    def visit_If(self, node: ast.If):
        self._scope_depth += 1
        else_label = self.__label_generator.lookup_or_create(self.__label_id)
        self.__label_id += 1
        fi_label = self.__label_generator.lookup_or_create(self.__label_id)
        self.__label_id += 1

        has_else = len(node.orelse) > 0
        self.__branch_compare(node, None, else_label if has_else else fi_label)

        # Body of true (if) branch
        for contents in node.body:
            self.visit(contents)

        if has_else:
            self._record_instruction(f'BR {fi_label}')
            self._record_instruction('NOP1', label=else_label)

            # Body of false (else) branch
            for contents in node.orelse:
                self.visit(contents)

        # Sentinel marker for the end of the loop
        self._record_instruction('NOP1', label=fi_label)
        self._scope_depth -= 1

    ####
    # Handling While loops (only variable OP variable)
    ####

    def visit_While(self, node: ast.While):
        self._scope_depth += 1
        test_label = self.__label_generator.lookup_or_create(self.__label_id)
        self.__label_id += 1
        end_label = self.__label_generator.lookup_or_create(self.__label_id)
        self.__label_id += 1

        self.__branch_compare(node, test_label, end_label)

        # Body of the loop
        for contents in node.body:
            self.visit(contents)
        self._record_instruction(f'BR {test_label}')

        # Sentinel marker for the end of the loop
        self._record_instruction('NOP1', label=end_label)
        self._scope_depth -= 1

    def visit_FunctionDef(self, node: ast.FunctionDef):
        # Save the function identifier, so we can error on usage of undefined functions
        # TODO: Error checking for function args
        self._function_definitions[node.name] = len(node.args.args)

    def visit_AugAssign(self, node: ast.AugAssign):
        self.visit_Assign(assign_from_augassign(node))

    def visit_Assign(self,
                     node: ast.Assign) -> tuple[str, ast.expr, ast.Name | ast.Constant | None]:
        # Verify every assignment, regardless of scope
        ensure_assign(node)
        target = node.targets[0]
        if isinstance(target, ast.Subscript):
            subscript = target.slice
            if isinstance(subscript, ast.Slice):
                compile_error(subscript, "Array slicing is not supported")
            if not isinstance(subscript, (ast.Name, ast.Constant)):
                compile_error(subscript, "Unnamed expressions in array subscript is not supported")
            if not isinstance(target.value, ast.Name):
                compile_error(target.value, "Cannot index into non-array object")
            self._current_variable = target.value
        else:
            subscript = None
            self._current_variable = target

        assert isinstance(self._current_variable, ast.Name)
        ident = self._current_variable.id
        return ident, target, subscript  # type: ignore

    def _assign_store(self,
                      node: ast.Assign,
                      ident: str,
                      target: ast.expr,
                      subscript: ast.expr | None):
        self.visit(node.value)
        self._variable_names.add(ident)

        if self._should_save:
            if subscript is not None:
                self._access_memory(subscript, 'LDWX')
            self._access_memory(target, 'STWA')
        else:
            self._should_save = True

        self._current_variable = None

    def _record_instruction(self, instruction: str, label: str | None = None):
        self._instructions.append((label, instruction))

    @abstractmethod
    def _access_memory(self, node: ast.expr, instruction: str, label=None):
        '''Depending on the context (global or local), memory should be accessed differently'''
        if isinstance(node, ast.Name):
            if node.id not in self._variable_names:
                compile_error(node, f'Use of undeclared identifier "{node.id}"')

    @property
    def function_labels(self): return self.__label_generator

    def finalize(self): return self._instructions
