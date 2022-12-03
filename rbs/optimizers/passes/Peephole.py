from ...common.Types import LabeledInstruction


def peephole_double_load(instructions: list[LabeledInstruction]) -> list[LabeledInstruction]:
    def extract_from_instruction(instr: str) -> tuple[str, str]:
        _, operand = instr.split(' ')
        var, mode = operand.split(',')
        return var, mode

    var_in_acc = None
    var_in_idx = None
    did_asl_idx = False
    new_instructions = []

    for instruction in instructions:
        label, instr = instruction

        if label is not None or instr.startswith("CALL"):
            # If branched to here from somewhere, there's no way to know what's in the registers
            var_in_acc = None
            var_in_idx = None
            did_asl_idx = False

        if instr.startswith("LDWA"):
            var, mode = extract_from_instruction(instr)

            if not mode.endswith('x'):
                if var_in_acc == var:
                    # Same variable, skip
                    continue
                var_in_acc = var
            else:
                # Indexing
                assert var_in_idx is not None
                if var_in_acc is not None and var_in_acc + var_in_idx == var:
                    # Same variable, skip
                    continue
                assert var_in_idx is not None
                var_in_acc = var + var_in_idx

        elif instr.startswith("LDWX"):
            # Assuming that the index register will never be addressed by indexing
            var, _ = extract_from_instruction(instr)
            if var_in_idx == var:
                # Same variable, skip
                continue
            # Did change
            var_in_idx = var

        # These instructions change what is in the register, forget the saved variable
        elif any(instr.startswith(s) for s in
                 ("NOT", "NEG", "ASL", "ASR", "ROL", "ROR", "ADD", "SUB", "AND", "OR")):

            reg = instr[2 if instr.startswith("OR") else 3]

            if reg == 'A':
                var_in_acc = None
            else:
                if var_in_idx is not None and instr.startswith("ASL"):
                    # Skip ASLX when reusing value in idx register
                    if did_asl_idx:
                        continue
                    did_asl_idx = True
                else:
                    var_in_idx = None
                    did_asl_idx = False

        # Every other instruction remains
        new_instructions.append(instruction)

    return new_instructions


def peephole_nops(instructions: list[LabeledInstruction]) -> list[LabeledInstruction]:
    if len(instructions) == 0:
        return instructions

    new_instructions = []
    skip_next = False
    for curr_instruction, next_instruction in zip(instructions, instructions[1:]):
        if skip_next:
            skip_next = False
            continue
        curr_label, curr_instr = curr_instruction
        next_label, next_instr = next_instruction
        # TODO: Collapse consecutive labels with NOP
        if curr_instr.startswith('NOP1') and next_label is None:
            new_instructions.append((curr_label, next_instr))
            skip_next = True
        else:
            new_instructions.append(curr_instruction)

    if not skip_next:
        new_instructions.append(next_instruction)

    return new_instructions


# TODO: Passes for augmented assignments, consecutive comparisons, ...
