from typing import Iterable
from ..common.Types import VariableIdentifier, InitKind
from ..common.Output import CompilerOutput


class StaticMemoryAllocation():

    def __init__(self, output: CompilerOutput, global_vars: Iterable[VariableIdentifier]) -> None:
        self.__output = output
        self.__global_vars = global_vars

    def generate(self):
        print('; Allocating Global (static) memory')
        for s, kind, x in self.__global_vars:
            label = f'{str(s+":"):<9}\t'
            match kind:
                case InitKind.BLOCK:
                    print(f'{label}.BLOCK 2', file=self.__output.output_file)
                case InitKind.EQUATE:
                    print(f'{label}.EQUATE {x}', file=self.__output.output_file)
                case InitKind.WORD:
                    print(f'{label}.WORD {x}', file=self.__output.output_file)
