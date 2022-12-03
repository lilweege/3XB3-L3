from ..common.Types import LabeledInstruction, OptimizationPass
from functools import reduce


class Optimizer:

    def __init__(self) -> None:
        self.__passes: list[OptimizationPass] = []

    def add_pass(self, pass_func: OptimizationPass):
        self.__passes.append(pass_func)

    def optimize(self, instructions: list[LabeledInstruction]) -> list[LabeledInstruction]:
        return reduce(lambda instr, func: func(instr), self.__passes, instructions)
