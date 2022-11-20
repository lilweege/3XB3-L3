from typing import Iterable
from ..common.Types import VariableIdentifier, InitKind
from ..common.Output import CompilerOutput
from ..common.SymbolTable import SymbolTable


class StaticMemoryAllocation():

    def __init__(self,
                 output: CompilerOutput,
                 symbol_table: SymbolTable,
                 global_vars: Iterable[VariableIdentifier]) -> None:
        self.__output = output
        self.__symbol_table = symbol_table
        self.__global_vars = global_vars

    def generate(self):
        print('; Allocating Global (static) memory')
        for s, kind, x in self.__global_vars:
            ident = s
            if not self.__output.unsafe_identifiers:
                s = self.__symbol_table[s]
            label = f'{str(s+":"):<9}\t'
            match kind:
                case InitKind.BLOCK:
                    print(f'{label}{".BLOCK 2":<14}', end='', file=self.__output.output_file)
                case InitKind.EQUATE:
                    print(f'{label}{f".EQUATE {x}":<14}', end='', file=self.__output.output_file)
                case InitKind.WORD:
                    print(f'{label}{f".WORD {x}":<14}', end='', file=self.__output.output_file)
            print(f'; {ident}', file=self.__output.output_file)
