from typing import Dict, List, Tuple
from llvmlite import ir

datatype = "bint"
typeRepresentation = ir.PointerType(ir.IntType(8))
libraries = ["-lgmp", "-lgmpxx"]

functions: Dict[str, Tuple[str, List[str]]] = {
    "add": ("bint", ["bint", "bint"]),
    "sub": ("bint", ["bint", "bint"]),
    "mul": ("bint", ["bint", "bint"]),
    "div": ("bint", ["bint", "bint"]),
    "mod": ("bint", ["bint", "bint"]),
    
    "eq": ("bool", ["bint", "bint"]),
    "ne": ("bool", ["bint", "bint"]),
    "lt": ("bool", ["bint", "bint"]),
    "le": ("bool", ["bint", "bint"]),
    "gt": ("bool", ["bint", "bint"]),
    "ge": ("bool", ["bint", "bint"]),
    
    "and": ("bint", ["bint", "bint"]),
    "or": ("bint", ["bint", "bint"]),
    "xor": ("bint", ["bint", "bint"]),
    "not": ("bint", ["bint"]),
    "lshift": ("bint", ["bint", "int"]),
    "rshift": ("bint", ["bint", "int"]),
    
    "to_int": ("int", ["bint"]),
    "to_string": ("string", ["bint"]),
    
    "print": ("void", ["bint"])
}

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
                    fromIntFunc = self.externalFunctions["bint"]["from_int"]
                    left = self.builder.call(fromIntFunc, [left], name="binop_left_to_bint")
                
                if not rightIsBint and right.type == ir.IntType(32):
                    fromIntFunc = self.externalFunctions["bint"]["from_int"]
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
    