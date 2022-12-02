import ast
from itertools import product
from string import ascii_uppercase
from typing import Iterator


def is_constant_ident(s: str) -> bool:
    return s[0] == '_' and all(c.isnumeric() or c.isupper() or c == '_' for c in s[1:])


def is_array_ident(s: str) -> bool:
    return s[-1] == '_'


def next_name_generator(n: int) -> Iterator[str]:
    return ("".join(s) for s in product(ascii_uppercase, repeat=n))


def reversed_next_name_generator(n: int) -> Iterator[str]:
    return ("".join(s) for s in product(reversed(ascii_uppercase), repeat=n))


def assign_from_augassign(node: ast.AugAssign):
    return ast.Assign(targets=[node.target], value=ast.BinOp(
            left=node.target,
            op=ast.Add(),
            right=node.value
        )
    )
