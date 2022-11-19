import ast
from .Errors import compile_error_and_crash

LabeledInstruction = tuple[str | None, str]


def ensure_args(node: ast.Call, num_args: int):
    if len(node.args) != num_args:
        compile_error_and_crash(node, f"Expected {num_args} arguments, got {len(node.args)}")
    if any(isinstance(x, ast.Starred) for x in node.args):
        compile_error_and_crash(node, "Star arguments are not supported")
    if len(node.keywords) != 0:
        compile_error_and_crash(node, "Keyword arguments are not supported")


def ensure_condition(node: ast.expr):
    if not isinstance(node, ast.Compare):
        compile_error_and_crash(node, "Conditional must be comparison")
    if len(node.ops) != 1:
        compile_error_and_crash(node, "Multiple comparison are not supported")
    if isinstance(node.ops[0], (ast.Is, ast.IsNot, ast.In, ast.NotIn)):
        compile_error_and_crash(node, f"Unsuppored comparison type '{type(node.ops[0]).__name__}'")


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

    ####
    # Handling Assignments (variable = ...)
    ####

    def visit_Assign(self, node: ast.Assign):
        # remembering the name of the target
        assert len(node.targets) > 0
        var_name = node.targets[0]
        if not isinstance(var_name, ast.Name):
            raise ValueError(f'Unsupported target: {var_name}')
        self.__current_variable = var_name.id
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
            raise ValueError(f'Unsupported binary operator: {node.op}')

    def visit_Call(self, node: ast.Call):
        assert isinstance(node.func, ast.Name)
        match node.func.id:
            case 'int':
                # Let's visit whatever is casted into an int
                ensure_args(node, 1)
                self.visit(node.args[0])
            case 'input':
                # We are only supporting integers for now
                self.__record_instruction(f'DECI {self.__current_variable},d')
                self.__should_save = False  # DECI already save the value in memory
            case 'print':
                # We are only supporting integers for now
                ensure_args(node, 1)
                to_print = node.args[0]
                if not isinstance(to_print, ast.Name):
                    raise ValueError("Printing unnamed expressions is unsupported")
                self.__record_instruction(f'DECO {to_print.id},d')
            case _:
                raise ValueError(f'Unsupported function call: {node.func.id}')

    ####
    # Handling While loops (only variable OP variable)
    ####

    def visit_While(self, node: ast.While):
        ensure_condition(node.test)
        loop_id = self.__identify()
        inverted = {
            ast.Lt:    'BRGE',  # '<'  in the code means we branch if '>='
            ast.LtE:   'BRGT',  # '<=' in the code means we branch if '>'
            ast.Gt:    'BRLE',  # '>'  in the code means we branch if '<='
            ast.GtE:   'BRLT',  # '>=' in the code means we branch if '<'
            ast.Eq:    'BRNE',
            ast.NotEq: 'BREQ',
        }
        # left part can only be a variable
        self.__access_memory(node.test.left, 'LDWA', label=f'test_{loop_id}')
        # right part can only be a variable
        self.__access_memory(node.test.comparators[0], 'CPWA')
        # Branching is condition is not true (thus, inverted)
        self.__record_instruction(f'{inverted[type(node.test.ops[0])]} end_l_{loop_id}')
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

    def __access_memory(self, node: ast.expr, instruction, label=None):
        if isinstance(node, ast.Constant):
            self.__record_instruction(f'{instruction} {node.value},i', label)
        else:
            assert isinstance(node, ast.Name)
            self.__record_instruction(f'{instruction} {node.id},d', label)

    def __identify(self):
        result = self.__elem_id
        self.__elem_id += 1
        return result
