from llvmlite import ir
from stdlib.module_utils import StdModule

module = StdModule(
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
module.functions["toInt"] = ("int", ["bint"])
module.mapping["toInt"] = "bint_to_int"
module.functions["toString"] = ("string", ["bint"])
module.mapping["toString"] = "bint_to_string"
module.functions["print"] = ("void", ["bint"])

module.addConversion("int", "bint", "fromInt")

module.functions["fromInt"] = ("bint", ["int"])
module.mapping["fromInt"] = "bint_from_int"
module.functions["fromString"] = ("bint", ["string"])
module.mapping["fromString"] = "bint_from_string"

module = module.export()

def registerWithCodegen(codegen):
    originalBinOp = codegen.BinOp

    def enhancedBinOp(self, node):
        if node.op in ['+', '-', '*', '/', '%']:
            left = self.codegen(node.left)
            right = self.codegen(node.right)
            
            leftIsBint = left.type.is_pointer and left.type.pointee == ir.IntType(8)
            rightIsBint = right.type.is_pointer and right.type.pointee == ir.IntType(8)
            
            if leftIsBint or rightIsBint:
                if not leftIsBint and left.type == ir.IntType(32):
                    fromIntFunc = self.externalFunctions["bint"]["fromInt"]
                    left = self.builder.call(fromIntFunc, [left], name="binop_left_to_bint")
                
                if not rightIsBint and right.type == ir.IntType(32):
                    fromIntFunc = self.externalFunctions["bint"]["fromInt"]
                    right = self.builder.call(fromIntFunc, [right], name="binop_right_to_bint")
                
                if node.op == '+':
                    return self.builder.call(self.externalFunctions["bint"]["add"], [left, right], name="bint_add_result")
                elif node.op == '-':
                    return self.builder.call(self.externalFunctions["bint"]["sub"], [left, right], name="bint_sub_result")
                elif node.op == '*':
                    return self.builder.call(self.externalFunctions["bint"]["mul"], [left, right], name="bint_mul_result")
                elif node.op == '/':
                    return self.builder.call(self.externalFunctions["bint"]["div"], [left, right], name="bint_div_result")
                elif node.op == '%':
                    return self.builder.call(self.externalFunctions["bint"]["mod"], [left, right], name="bint_mod_result")
        
        return originalBinOp(node)
    
    codegen.BinOp = enhancedBinOp.__get__(codegen, codegen.__class__) 
    