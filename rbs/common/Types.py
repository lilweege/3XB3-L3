from enum import Enum


# The first string is the label (optional), and the second is the Pep/9 mnemonic
LabeledInstruction = tuple[str | None, str]


class InitKind(Enum):
    BLOCK = 1
    EQUATE = 2
    WORD = 3


# The string contains the identifier, and InitKind specifies how the global variable is allocated
# The optional int holds the value to set to if InitKind is EQUATE or WORD
VariableIdentifier = tuple[str, InitKind, int | None]
