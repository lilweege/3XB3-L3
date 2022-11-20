class CompilerOutput:
    def __init__(self, output_file, unsafe_identifiers: bool):
        self.output_file = output_file
        self.unsafe_identifiers = unsafe_identifiers
