from typing import Iterable
from ..common.Types import VariableIdentifier, InitKind


class StaticMemoryAllocation():

    def __init__(self, global_vars: Iterable[VariableIdentifier]) -> None:
        self.__global_vars = global_vars

    def generate(self):
        print('; Allocating Global (static) memory')
        for s, kind, x in self.__global_vars:
            label = f'{str(s+":"):<9}\t'
            match kind:
                case InitKind.BLOCK:
                    print(f'{label}.BLOCK 2')  # reserving memory
                case InitKind.EQUATE:
                    print(f'{label}.EQUATE {x}')
                case InitKind.WORD:
                    print(f'{label}.WORD {x}')
