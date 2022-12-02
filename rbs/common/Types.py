from enum import Enum
from typing import Callable, TypeAlias
from dataclasses import dataclass, field


# The first string is the label (optional), and the second is the Pep/9 mnemonic
LabeledInstruction: TypeAlias = tuple[str | None, str]


class InitKind(Enum):
    BLOCK = 1
    EQUATE = 2
    WORD = 3


# The string contains the identifier, and InitKind specifies how the global variable is allocated
# The int holds the value to follow the InitKind directive (either a value, or number of bytes)
GlobalVariable: TypeAlias = tuple[str, InitKind, int]

# The string is the label name, followed by the stack offset then the array size (size=1 is scalar)
LocalVariable: TypeAlias = tuple[str, int, int]


@dataclass
class CallFrame:
    locals: dict[str, LocalVariable] = field(default_factory=dict)
    stack_space: int = 0

    # __iter__ is provided to allow unpacking
    def __iter__(self): yield from (self.locals, self.stack_space)


# A pass is a function that takes a list of instructions and returns a new (modified) list
OptimizationPass: TypeAlias = Callable[[list[LabeledInstruction]], list[LabeledInstruction]]
