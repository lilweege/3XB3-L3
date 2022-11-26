from typing import Iterable


class LocalMemoryAllocation():

    def __init__(self,
                 output,
                 func_defns: Iterable[tuple[str, dict[str, tuple[str, int]]]]) -> None:
        self.__output = output
        self.__func_defns = func_defns

    def generate(self):
        for name, vars in self.__func_defns:
            stack_space = 2 * (len(vars) - 1)
            print(f'; Allocating Local memory for {name}', file=self.__output)
            for var, (label, offset) in vars.items():
                allocation = f'{str(label+":"):<9}\t{f".EQUATE {stack_space - offset}":<14}'
                tag = f'; local var {var} #2d'
                print(allocation+tag, file=self.__output)
