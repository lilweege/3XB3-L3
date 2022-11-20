from typing import Iterable
from ..common.Types import LabeledInstruction
from ..common.Output import CompilerOutput


class EntryPoint():

    def __init__(self, output: CompilerOutput, instructions: Iterable[LabeledInstruction]) -> None:
        self.__output = output
        self.__instructions = instructions

    def generate(self):
        print('; Top Level instructions', file=self.__output.output_file)
        for label, instr in self.__instructions:
            if label is None:
                s = f'\t\t{instr}'
            else:
                s = f'{str(label+":"):<9}\t{instr}'
            print(s, file=self.__output.output_file)
