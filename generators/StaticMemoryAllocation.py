from typing import Iterable


class StaticMemoryAllocation():

    def __init__(self, global_vars: Iterable[str]) -> None:
        self.__global_vars = global_vars

    def generate(self):
        print('; Allocating Global (static) memory')
        for n in self.__global_vars:
            print(f'{str(n+":"):<9}\t.BLOCK 2')  # reserving memory
