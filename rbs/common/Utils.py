def is_constant_ident(s):
    return s[0] == '_' and \
        all(c.isnumeric() or c.isupper() or c == '_' for c in s[1:])
