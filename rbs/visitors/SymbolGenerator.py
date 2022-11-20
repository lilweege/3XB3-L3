from typing import Iterator


class SymbolGenerator:

    def __init__(self, generator: Iterator[str]):
        self.__generator = generator
        self.__names: dict[str, str] = {}

    def lookup_or_create(self, name: str):
        if name in self.__names:
            return self.__names[name]
        label = next(self.__generator)
        self.__names[name] = label
        return label
