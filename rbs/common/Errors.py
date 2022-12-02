from typing import NoReturn
from sys import stderr
from ..common.Utils import is_array_ident
import ast


def compile_error(node: ast.AST, msg: str) -> NoReturn:
    print(f"Error at Ln {node.lineno}, Col {node.col_offset+1}: {msg}", file=stderr)
    # NOTE: Errors could be accumulated and handled gracefully, we don't do this...
    # Currently, the first error encountered will terminate compilation
    exit(1)


def ensure_args(node: ast.Call, num_args: int):
    if len(node.args) != num_args:
        compile_error(node, f"Expected {num_args} arguments, got {len(node.args)}")
    if len(node.keywords) != 0:
        compile_error(node, "Keyword arguments are not supported")
    for arg in node.args:
        if isinstance(arg, ast.Starred):
            compile_error(node, "Star arguments are not supported")
        if isinstance(arg, ast.Name):
            if is_array_ident(arg.id):
                compile_error(node, 'Passing arrays as parameters is not supported')
        elif not ((isinstance(arg, ast.Call) and arg.func.id == 'input')  # type: ignore
                  or isinstance(arg, ast.Constant) or isinstance(arg, ast.Subscript)):
            compile_error(node, 'Unnamed expressions as arguments are not supported')


def ensure_condition(node: ast.expr):
    if not isinstance(node, ast.Compare):
        compile_error(node, "Conditional must be comparison")
    if len(node.ops) != 1 or len(node.comparators) != 1:
        compile_error(node, "Multiple comparison are not supported")


def ensure_assign(node: ast.Assign):
    if len(node.targets) != 1:
        compile_error(node, "Only unary assignments are supported")
    var_name = node.targets[0]
    if not isinstance(var_name, (ast.Name, ast.Subscript)):
        compile_error(node, f'Unsupported target: {var_name}')


def ensure_array(node: ast.expr) -> int:
    msg = "Only static initialization of arrays is supported (ex. [0] * 25)"
    if not isinstance(node, ast.BinOp):
        compile_error(node, msg)
    if not isinstance(node.op, ast.Mult):
        compile_error(node, msg)

    lhs, rhs = node.left, node.right
    if not isinstance(lhs, ast.List):
        compile_error(lhs, msg)
    lst = lhs.elts
    if len(lst) != 1 or not isinstance(lst[0], ast.Constant) or lst[0].value != 0:
        compile_error(lhs, msg)

    # TODO: Allow propagated constants as array sizes
    if not isinstance(rhs, ast.Constant):
        compile_error(rhs, msg)

    if not isinstance(rhs.value, int):
        compile_error(rhs, msg)

    return rhs.value
