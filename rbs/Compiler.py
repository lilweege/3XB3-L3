from sys import stdout
from .visitors.GlobalVariables import GlobalVariableExtraction
from .visitors.TopLevelProgram import TopLevelProgram
from .generators.StaticMemoryAllocation import StaticMemoryAllocation
from .generators.EntryPoint import EntryPoint
from .common.Output import CompilerOutput


UNSAFE_IDENTS = False


def compile(root_node, input_file, output_file=stdout):
    output = CompilerOutput(output_file, UNSAFE_IDENTS)
    print(f'; Translating {input_file}', file=output_file)
    extractor = GlobalVariableExtraction(output)
    extractor.visit(root_node)
    memory_alloc = StaticMemoryAllocation(output, extractor.results)
    print('; Branching to top level (tl) instructions', file=output_file)
    print('\t\tBR tl', file=output_file)
    memory_alloc.generate()
    top_level = TopLevelProgram(output, 'tl')
    top_level.visit(root_node)
    ep = EntryPoint(top_level.finalize())
    ep.generate()
