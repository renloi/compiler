from typing import Dict, List, Tuple
from llvmlite import ir

datatype = "bint"
typeRepresentation = ir.PointerType(ir.IntType(8))
libraries = ["-lgmp", "-lgmpxx"]

printConfig = {
    "conversion_function": "to_string",
    "format_specifier": "%s"
}

functions: Dict[str, Tuple[str, List[str]]] = {
    "from_int": ("bint", ["int"]),
    "from_string": ("bint", ["string"]),
    
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

constructors = {
    "int": "from_int",
    "string": "from_string"
}

mapping: Dict[str, str] = {
    "from_int": "bint_from_int",
    "from_string": "bint_from_string",
    
    "add": "bint_add",
    "sub": "bint_sub",
    "mul": "bint_mul",
    "div": "bint_div",
    "mod": "bint_mod",
    
    "eq": "bint_eq",
    "ne": "bint_ne",
    "lt": "bint_lt",
    "le": "bint_le",
    "gt": "bint_gt",
    "ge": "bint_ge",
    
    "and": "bint_and",
    "or": "bint_or",
    "xor": "bint_xor",
    "not": "bint_not",
    "lshift": "bint_lshift",
    "rshift": "bint_rshift",
    
    "to_int": "bint_to_int",
    "to_string": "bint_to_string",
    
    "print": "bint_print"
}

# Auto-conversion from int literals to bint
typeConversion = {
    "from_int": {
        "source_type": "int",
        "target_type": "bint",
        "function": "from_int"
    }
}

def registerWithCodegen(codegen):
    # Store original functions
    originalConvertValue = codegen.convertValue
    originalBinOp = codegen.BinOp
    
    def enhancedConvertValue(self, value, sourceType, targetTypeName):
        # Special case: convert int to bint
        if targetTypeName == "bint" and sourceType == ir.IntType(32):
            print(f"Converting int to bint")
            fromIntFunc = self.externalFunctions["bint"]["from_int"]
            return self.builder.call(fromIntFunc, [value], name="int_to_bint")
        
        # Default case: use original implementation
        return originalConvertValue(value, sourceType, targetTypeName)
    
    def enhancedBinOp(self, node):
        # Handle binary operations with bint operands
        if node.op in ['+', '-', '*', '/', '%']:
            left = self.codegen(node.left)
            right = self.codegen(node.right)
            
            # Check if either operand is a bint
            leftIsBint = left.type.is_pointer and left.type.pointee == ir.IntType(8)
            rightIsBint = right.type.is_pointer and right.type.pointee == ir.IntType(8)
            
            if leftIsBint or rightIsBint:
                # Convert int to bint if needed
                if not leftIsBint and left.type == ir.IntType(32):
                    fromIntFunc = self.externalFunctions["bint"]["from_int"]
                    left = self.builder.call(fromIntFunc, [left], name="binop_left_to_bint")
                
                if not rightIsBint and right.type == ir.IntType(32):
                    fromIntFunc = self.externalFunctions["bint"]["from_int"]
                    right = self.builder.call(fromIntFunc, [right], name="binop_right_to_bint")
                
                # Call appropriate bint operation
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
        
        # Use original implementation for all other cases
        return originalBinOp(node)
    
    # Replace the methods
    codegen.convertValue = enhancedConvertValue.__get__(codegen, codegen.__class__)
    codegen.BinOp = enhancedBinOp.__get__(codegen, codegen.__class__) 
    