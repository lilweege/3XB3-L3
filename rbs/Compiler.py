from sys import stdout
from .visitors.GlobalVariables import GlobalVariableExtraction
from .visitors.TopLevelProgram import TopLevelProgram
from .generators.StaticMemoryAllocation import StaticMemoryAllocation
from .generators.EntryPoint import EntryPoint
from .common.Output import CompilerOutput


UNSAFE_IDENTS = False


def compile(root_node, input_file, output_file=stdout):
    output = CompilerOutput(output_file, UNSAFE_IDENTS)

    extractor = GlobalVariableExtraction()
    extractor.visit(root_node)
    identifier_labels = extractor.symbol_table

    top_level = TopLevelProgram(output, identifier_labels, 'tl')
    top_level.visit(root_node)

    memory_alloc = StaticMemoryAllocation(output, identifier_labels, extractor.results)

    print(f'; Translating {input_file}', file=output_file)
    print('; Branching to top level (tl) instructions', file=output_file)
    print('\t\tBR tl', file=output_file)
    memory_alloc.generate()
    ep = EntryPoint(output, top_level.finalize())
    ep.generate()
