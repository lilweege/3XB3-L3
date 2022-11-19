import ast
from ..common.Errors import compile_error, ensure_args, ensure_condition, ensure_assign
from ..common.Types import LabeledInstruction


class TopLevelProgram(ast.NodeVisitor):
    """We supports assignments and input/print calls"""

    def __init__(self, entry_point) -> None:
        super().__init__()
        self.__instructions: list[LabeledInstruction] = list()
        self.__record_instruction('NOP1', label=entry_point)
        self.__should_save = True
        self.__current_variable: str | None = None
        self.__elem_id = 0
        self.__propagated_constants: dict[str, int] = {}

    def finalize(self):
        self.__instructions.append((None, '.END'))
        return self.__instructions

    def try_propagate_constant(self, node: ast.AST) -> tuple[bool, int]:
        '''
        Returns:
            bool: Is it possible to propagate the expression
            int: If possible, the value of the propogated constant
        '''

        if isinstance(node, ast.BinOp):
            if not isinstance(node.op, (ast.Add, ast.Sub)):
                compile_error(node, f'Unsupported binary operator: {type(node.op).__name__}')

            ok1, lhs = self.try_propagate_constant(node.left)
            ok2, rhs = self.try_propagate_constant(node.right)
            if not (ok1 and ok2):
                return False, 0

            if isinstance(node.op, ast.Add):
                return True, lhs + rhs
            else:
                return True, lhs - rhs

        elif isinstance(node, ast.Constant):
            if not isinstance(node.value, int):
                compile_error(node, f"Unsupported type {type(node.value).__name__}")
            return True, node.value

        elif isinstance(node, ast.Name):
            if node.id not in self.__propagated_constants:
                return False, 0
            return True, self.__propagated_constants[node.id]

        elif isinstance(node, ast.Call):
            # Can't evaluate a function call
            return False, 0

        else:
            compile_error(node, f"Unsupported type {type(node).__name__} in expression")

    ####
    # Handling Assignments (variable = ...)
    ####

    def visit_Assign(self, node: ast.Assign):
        # remembering the name of the target
        ensure_assign(node)
        assert isinstance(node.targets[0], ast.Name)
        var_name: ast.Name = node.targets[0]
        self.__current_variable = var_name.id

        ok, const_val = self.try_propagate_constant(node.value)
        if ok:
            self.__propagated_constants[self.__current_variable] = const_val
        elif self.__current_variable in self.__propagated_constants:
            # Value was constant but is changing to a non-constant value
            self.__propagated_constants.pop(self.__current_variable)

        # visiting the left part, now knowing where to store the result
        self.visit(node.value)
        if self.__should_save:
            self.__record_instruction(f'STWA {self.__current_variable},d')
        else:
            self.__should_save = True
        self.__current_variable = None

    def visit_Constant(self, node: ast.Constant):
        self.__record_instruction(f'LDWA {node.value},i')

    def visit_Name(self, node: ast.Name):
        self.__record_instruction(f'LDWA {node.id},d')

    def visit_BinOp(self, node: ast.BinOp):
        self.__access_memory(node.left, 'LDWA')
        if isinstance(node.op, ast.Add):
            self.__access_memory(node.right, 'ADDA')
        elif isinstance(node.op, ast.Sub):
            self.__access_memory(node.right, 'SUBA')
        else:
            compile_error(node, f'Unsupported binary operator: {type(node.op).__name__}')

    def visit_Call(self, node: ast.Call):
        assert isinstance(node.func, ast.Name)
        match node.func.id:
            case 'int':
                # Let's visit whatever is casted into an int
                ensure_args(node, 1)
                self.visit(node.args[0])
            case 'input':
                # We are only supporting integers for now
                ensure_args(node, 0)
                self.__record_instruction(f'DECI {self.__current_variable},d')
                self.__should_save = False  # DECI already save the value in memory
            case 'print':
                # We are only supporting integers for now
                ensure_args(node, 1)
                to_print = node.args[0]
                if not isinstance(to_print, ast.Name):
                    compile_error(node, "Printing unnamed expressions is unsupported")
                self.__record_instruction(f'DECO {to_print.id},d')
            case _:
                compile_error(node, f'Unsupported function call: {node.func.id}')

    ####
    # Handling While loops (only variable OP variable)
    ####

    def visit_While(self, node: ast.While):
        ensure_condition(node.test)
        assert isinstance(node.test, ast.Compare)
        cmp: ast.Compare = node.test
        loop_id = self.__identify()
        comparisons = {
            ast.Lt:    'BRGE',  # '<'  in the code means we branch if '>='
            ast.LtE:   'BRGT',  # '<=' in the code means we branch if '>'
            ast.Gt:    'BRLE',  # '>'  in the code means we branch if '<='
            ast.GtE:   'BRLT',  # '>=' in the code means we branch if '<'
            ast.Eq:    'BRNE',
            ast.NotEq: 'BREQ',
        }
        lhs, rhs = cmp.left, cmp.comparators[0]
        self.__access_memory(lhs, 'LDWA', label=f'test_{loop_id}')
        self.__access_memory(rhs, 'CPWA')
        # Branching is condition is not true (thus, inverted)
        cmp_typ = type(cmp.ops[0])
        if cmp_typ not in comparisons:
            compile_error(node, f"Unsuppored comparison '{cmp_typ.__name__}'")
        self.__record_instruction(f'{comparisons[cmp_typ]} end_l_{loop_id}')
        # Visiting the body of the loop
        for contents in node.body:
            self.visit(contents)
        self.__record_instruction(f'BR test_{loop_id}')
        # Sentinel marker for the end of the loop
        self.__record_instruction('NOP1', label=f'end_l_{loop_id}')

    ####
    # Not handling function calls
    ####

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """We do not visit function definitions, they are not top level"""
        pass

    ####
    # Helper functions to
    ####

    def __record_instruction(self, instruction: str, label: str | None = None):
        self.__instructions.append((label, instruction))

    def __access_memory(self, node: ast.expr, instruction: str, label=None):
        if isinstance(node, ast.Constant):
            self.__record_instruction(f'{instruction} {node.value},i', label)
        elif isinstance(node, ast.Name):
            self.__record_instruction(f'{instruction} {node.id},d', label)
        else:
            compile_error(node, f"Cannot access memory of {node}")

    def __identify(self):
        result = self.__elem_id
        self.__elem_id += 1
        return result
