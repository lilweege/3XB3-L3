class EntryPoint():

    def __init__(self, instructions) -> None:
        self.__instructions = instructions

    def generate(self):
        print('; Top Level instructions')
        for label, instr in self.__instructions:
            if label is None:
                s = f'\t\t{instr}'
            else:
                s = f'{str(label+":"):<9}\t{instr}'
            print(s)
