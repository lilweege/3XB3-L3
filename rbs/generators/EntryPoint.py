from typing import Iterable
from ..common.Types import LabeledInstruction


class EntryPoint():

    def __init__(self, output, instructions: Iterable[LabeledInstruction]) -> None:
        self.__output = output
        self.__instructions = instructions

    def generate(self):
        for label, instr in self.__instructions:
            if label is None:
                s = f'\t\t{instr}'
            else:
                s = f'{str(label+":"):<9}\t{instr}'
            print(s, file=self.__output)
