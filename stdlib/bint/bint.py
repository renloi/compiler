from llvmlite import ir
from stdlib.utils import Module

module = Module(
    name="bint",
    datatype="bint",
    typeRepresentation=ir.PointerType(ir.IntType(8)),
    libraries=["-lgmp", "-lgmpxx"]
)

for op in ["add", "sub", "mul", "div", "mod", "and", "or", "xor"]:
    module.functions[op] = ("bint", ["bint", "bint"])

module.functions["not"] = ("bint", ["bint"])

for cmp in ["eq", "ne", "lt", "le", "gt", "ge"]:
    module.functions[cmp] = ("bool", ["bint", "bint"])

module.functions["lshift"] = ("bint", ["bint", "int"])
module.functions["rshift"] = ("bint", ["bint", "int"])
module.functions["print"] = ("void", ["bint"])

module.addConversion("int", "bint", "fromInt")

module.functions["fromInt"] = ("bint", ["int"])
module.mapping["fromInt"] = "bint_from_int"
module.functions["fromString"] = ("bint", ["string"])
module.mapping["fromString"] = "bint_from_string"

module = module.export()
