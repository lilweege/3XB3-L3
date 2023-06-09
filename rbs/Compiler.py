from sys import stdout
from .visitors.GlobalVariables import GlobalVariableExtraction
from .visitors.TopLevelProgram import TopLevelProgram
from .visitors.FunctionDefinition import FunctionDefinition
from .generators.StaticMemoryAllocation import StaticMemoryAllocation
from .generators.LocalMemoryAllocation import LocalMemoryAllocation
from .generators.EntryPoint import EntryPoint
from .optimizers.Optimizer import Optimizer
from .optimizers.passes.Peephole import peephole_double_load, peephole_nops


def compile(root_node, input_file, output_file=stdout):
    extractor = GlobalVariableExtraction()
    extractor.visit(root_node)
    identifier_labels = extractor.symbol_table

    top_level = TopLevelProgram(identifier_labels, 'main')
    top_level.visit(root_node)

    functions = FunctionDefinition(identifier_labels, top_level.function_labels)
    functions.visit(root_node)

    static_mem = StaticMemoryAllocation(output_file, identifier_labels, extractor.results)
    local_mem = LocalMemoryAllocation(output_file, functions.local_variables.items())

    print(f'; Translating {input_file}', file=output_file)
    print('; Branching to top level (main) instructions', file=output_file)
    print('\t\tBR main', file=output_file)
    static_mem.generate()
    local_mem.generate()

    passes = Optimizer()
    passes.add_pass(peephole_double_load)
    passes.add_pass(peephole_nops)

    ep = EntryPoint(output_file, passes.optimize(top_level.finalize()))
    fs = EntryPoint(output_file, passes.optimize(functions.finalize()))
    fs.generate()
    ep.generate()
