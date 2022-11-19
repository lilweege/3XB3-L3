from typing import NoReturn
from sys import stderr
import ast


def compile_error_and_crash(node: ast.AST, msg: str) -> NoReturn:
    print(f"Error at {node.lineno}:{node.col_offset}: {msg}", file=stderr)
    # NOTE: Errors could be accumulated and handled gracefully, we don't do this...
    # Currently, the first error encountered will terminate compilation
    exit(1)


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
    if len(node.ops) != 1 or len(node.comparators) != 1:
        compile_error_and_crash(node, "Multiple comparison are not supported")


def ensure_assign(node: ast.Assign):
    if len(node.targets) != 1:
        compile_error_and_crash(node, "Only unary assignments are supported")
    var_name = node.targets[0]
    if not isinstance(var_name, ast.Name):
        compile_error_and_crash(node, f'Unsupported target: {var_name}')
