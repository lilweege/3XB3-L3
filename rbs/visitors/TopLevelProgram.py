import ast
from ..common.Errors import compile_error, ensure_args, ensure_condition, ensure_assign
from ..common.Types import LabeledInstruction
from ..common.Utils import is_constant_ident, reversed_next_name_generator
from ..common.Output import CompilerOutput
from .ConstantPropagator import ConstantPropagator
from ..common.SymbolTable import SymbolTable


class TopLevelProgram(ast.NodeVisitor):
    """We supports assignments and input/print calls"""

    def __init__(self, output: CompilerOutput, symbol_table: SymbolTable, entry_point: str) -> None:
        super().__init__()
        self.__output = output
        self.__instructions: list[LabeledInstruction] = list()
        self.__record_instruction('NOP1', label=entry_point)
        self.__should_save = True
        self.__current_variable: str | None = None
        self.__constant_propagator = ConstantPropagator()
        self.__loop_depth = 0
        self.__elem_id = 0
        self.__ident_label_generator = symbol_table
        self.__loop_label_generator = SymbolTable(reversed_next_name_generator(8))

    def finalize(self):
        self.__instructions.append((None, '.END'))
        return self.__instructions

    ####
    # Handling Assignments (variable = ...)
    ####

    def visit_Assign(self, node: ast.Assign):
        # remembering the name of the target
        ensure_assign(node)
        assert isinstance(node.targets[0], ast.Name)
        ident = node.targets[0].id
        self.__current_variable = self.__get_ident_label(ident)

        if is_constant_ident(ident):
            # This variable will be defined with .EQUATE, don't load and store
            return

        # Try to propagate constants, it may or may not be possible
        first_seen_now = ident not in self.__constant_propagator.seen_idents
        is_constexpr, _, _ = self.__constant_propagator.add_assign(ident, node.value)

        if first_seen_now and is_constexpr and self.__loop_depth == 0:
            # Don't load and store if the value can be statically initialized
            return

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
        ident_label = self.__get_ident_label(node.id)
        self.__record_instruction(f'LDWA {ident_label},d')

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
                ident_label = self.__get_ident_label(to_print.id)
                self.__record_instruction(f'DECO {ident_label},d')
            case _:
                compile_error(node, f'Unsupported function call: {node.func.id}')

    ####
    # Handling While loops (only variable OP variable)
    ####

    def visit_While(self, node: ast.While):
        ensure_condition(node.test)
        assert isinstance(node.test, ast.Compare)
        cmp: ast.Compare = node.test
        if self.__output.unsafe_identifiers:
            test_label = f'test_{self.__elem_id}'
            end_label = f'end_l_{self.__elem_id}'
            self.__elem_id += 1
        else:
            test_label = self.__identify()
            end_label = self.__identify()
        comparisons = {
            ast.Lt:    'BRGE',  # '<'  in the code means we branch if '>='
            ast.LtE:   'BRGT',  # '<=' in the code means we branch if '>'
            ast.Gt:    'BRLE',  # '>'  in the code means we branch if '<='
            ast.GtE:   'BRLT',  # '>=' in the code means we branch if '<'
            ast.Eq:    'BRNE',
            ast.NotEq: 'BREQ',
        }
        lhs, rhs = cmp.left, cmp.comparators[0]
        self.__access_memory(lhs, 'LDWA', label=test_label)
        self.__access_memory(rhs, 'CPWA')
        # Branching is condition is not true (thus, inverted)
        cmp_typ = type(cmp.ops[0])
        if cmp_typ not in comparisons:
            compile_error(node, f"Unsuppored comparison '{cmp_typ.__name__}'")
        self.__record_instruction(f'{comparisons[cmp_typ]} {end_label}')
        # Visiting the body of the loop
        self.__loop_depth += 1
        for contents in node.body:
            self.visit(contents)
        self.__loop_depth -= 1
        self.__record_instruction(f'BR {test_label}')
        # Sentinel marker for the end of the loop
        self.__record_instruction('NOP1', label=end_label)

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
            addr_mode = 'i' if is_constant_ident(node.id) else 'd'
            ident_label = self.__get_ident_label(node.id)
            self.__record_instruction(f'{instruction} {ident_label},{addr_mode}', label)
        else:
            compile_error(node, f"Cannot access memory of {node}")

    def __get_ident_label(self, ident: str):
        if self.__output.unsafe_identifiers:
            return ident
        else:
            return self.__ident_label_generator[ident]

    def __identify(self):
        result = self.__loop_label_generator.lookup_or_create(str(self.__elem_id))
        self.__elem_id += 1
        return result
