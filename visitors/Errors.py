from sys import stderr
import ast


def compile_error_and_crash(node: ast.AST, msg: str):
    print(f"Error at {node.lineno}:{node.col_offset}: {msg}", file=stderr)
    # NOTE: Errors could be accumulated and handled gracefully, we don't do this...
    # Currently, the first error encountered will terminate compilation
    exit(1)
