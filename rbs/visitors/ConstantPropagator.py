import ast
from ..common.Errors import compile_error


class ConstantPropagator:

    def __init__(self) -> None:
        self.__propagated_constants: dict[str, int] = {}
        self.__reassigned_idents: set[str] = set()
        self.__seen_idents: set[str] = set()

    def try_propagate_constant(self, node: ast.AST) -> tuple[bool, bool, int]:
        '''
        Returns:
            bool: Is it possible to propagate the expression
            bool: Was any name in the expression reassigned (not initial)
            int: If possible, the value of the propogated constant
        '''
        if isinstance(node, ast.BinOp):
            if not isinstance(node.op, (ast.Add, ast.Sub)):
                return False, False, 0

            ok1, reassigned1, lhs = self.try_propagate_constant(node.left)
            ok2, reassigned2, rhs = self.try_propagate_constant(node.right)
            ok = ok1 and ok2
            reassigned = reassigned1 or reassigned2
            if not ok:
                return False, reassigned, 0

            if isinstance(node.op, ast.Add):
                return True, reassigned, lhs + rhs
            else:
                return True, reassigned, lhs - rhs

        elif isinstance(node, ast.Constant):
            if not isinstance(node.value, int):
                compile_error(node, f"Unsupported type {type(node.value).__name__}")
            return True, False, node.value

        elif isinstance(node, ast.Name):
            reassigned = node.id in self.__reassigned_idents
            if node.id not in self.__propagated_constants:
                return False, reassigned, 0
            return True, reassigned, self.__propagated_constants[node.id]

        elif isinstance(node, ast.Call):
            # Can't evaluate a function call
            return False, False, 0

        else:
            compile_error(node, f"Unsupported type {type(node).__name__} in expression")

    def add_assign(self, identifier: str, node: ast.expr):
        is_constexpr, used_reassigned, const_val = self.try_propagate_constant(node)

        if is_constexpr:
            self.__propagated_constants[identifier] = const_val
        elif identifier in self.__propagated_constants:
            # Value was constant but is changing to a non-constant value
            self.__propagated_constants.pop(identifier)

        if identifier in self.__seen_idents:
            self.__reassigned_idents.add(identifier)
        self.__seen_idents.add(identifier)

        return is_constexpr, used_reassigned, const_val

    @property
    def propagated_constants(self): return self.__propagated_constants

    @property
    def reassigned_idents(self): return self.__reassigned_idents

    @property
    def seen_idents(self): return self.__seen_idents
