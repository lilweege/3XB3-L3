from itertools import product
from string import ascii_uppercase


def is_constant_ident(s):
    return s[0] == '_' and \
        all(c.isnumeric() or c.isupper() or c == '_' for c in s[1:])


def next_name_generator(n):
    return ("".join(s) for s in product(ascii_uppercase, repeat=n))


def reversed_next_name_generator(n):
    return ("".join(s) for s in product(reversed(ascii_uppercase), repeat=n))
