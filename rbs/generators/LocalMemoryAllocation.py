from typing import Iterable
from ..common.Types import CallFrame


class LocalMemoryAllocation():

    def __init__(self,
                 output,
                 func_defns: Iterable[tuple[str, CallFrame]]) -> None:
        self.__output = output
        self.__func_defns = func_defns

    def generate(self):
        for name, (vars, stack_space) in self.__func_defns:
            print(f'; Allocating Local memory for {name}', file=self.__output)
            for var, (label, offset, arr_size) in vars.items():
                constant = stack_space - offset - arr_size * 2
                allocation = f'{str(label+":"):<9}\t{f".EQUATE {constant}":<14}'
                tag = f'; local var {var} #2d{"" if arr_size <= 1 else f"{arr_size}a"}'
                print(allocation+tag, file=self.__output)
