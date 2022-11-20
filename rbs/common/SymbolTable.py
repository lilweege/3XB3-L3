from typing import Iterator


class SymbolTable:

    def __init__(self, generator: Iterator[str]):
        self.__generator = generator
        self.__names: dict[str, str] = {}

    def lookup_or_create(self, name: str):
        if name in self.__names:
            return self.__names[name]
        label = next(self.__generator)
        self.__names[name] = label
        return label

    def __set__(self, key: str, val: str) -> None:
        if key in self.__names:
            raise KeyError(key)
        self.__names[key] = val

    def __getitem__(self, key: str) -> str:
        if key not in self.__names:
            raise KeyError(key)
        return self.__names[key]
