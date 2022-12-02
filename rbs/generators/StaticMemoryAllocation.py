from typing import Iterable
from ..common.Types import GlobalVariable, InitKind
from ..common.SymbolTable import SymbolTable


class StaticMemoryAllocation():

    def __init__(self,
                 output,
                 symbol_table: SymbolTable,
                 global_vars: Iterable[GlobalVariable]) -> None:
        self.__output = output
        self.__symbol_table = symbol_table
        self.__global_vars = global_vars

    def generate(self):
        print('; Allocating Global (static) memory', file=self.__output)
        for ident, kind, size in self.__global_vars:
            label_name = self.__symbol_table[ident]
            label = f'{str(label_name+":"):<9}\t'
            tag_arr_size = ""
            match kind:
                case InitKind.BLOCK:
                    print(f'{label}{f".BLOCK {size}":<14}', end='', file=self.__output)
                    tag_arr_size = f'{"" if size/2 <= 1 else f"{int(size/2)}a"}'
                case InitKind.EQUATE:
                    print(f'{label}{f".EQUATE {size}":<14}', end='', file=self.__output)
                case InitKind.WORD:
                    print(f'{label}{f".WORD {size}":<14}', end='', file=self.__output)
            print(f'; global variable {ident} #2d{tag_arr_size}', file=self.__output)
