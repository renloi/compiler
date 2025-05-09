from llvmlite import ir

class ExpressionCodegen:
    def Return(self, node):
        return self.builder.ret(self.codegen(node.expr))

    def ExpressionStatement(self, node):
        return self.codegen(node.expr)

    def Num(self, node):
        return ir.Constant(ir.IntType(32), node.value)

    def FloatNum(self, node):
        return ir.Constant(ir.FloatType(), float(node.value))

    def String(self, node):
        # Check if quotes are already present in the node.value
        value = node.value
        if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
            # Remove quotes - they will be added back by createStringConstant
            value = value[1:-1]
        return self.createStringConstant(value)

    def Char(self, node):
        return ir.Constant(ir.IntType(8), ord(node.value))

    def BinOp(self, node):
        if node.op in self.binOpMap:
            intOp, floatOp, resName = self.binOpMap[node.op]
            return self.genArith(node, intOp, floatOp, resName)
        elif node.op in self.compMap:
            intCmp, floatCmp, resName = self.compMap[node.op]
            return self.genCompare(node, intCmp, floatCmp, resName)
        raise ValueError("Unknown binary operator " + node.op)

    def Var(self, node):
        info = self.funcSymtab.get(node.name)
        if info:
            return self.builder.load(info["addr"], name=node.name)
        raise NameError("Undefined variable: " + node.name)

    def FunctionCall(self, node):
        if node.callee.__class__.__name__ == "Var":
            if node.callee.name == "print":
                return self.PrintCall(node)
            func = self.module.get_global(node.callee.name)
            if not func:
                raise NameError("Unknown function: " + node.callee.name)
            llvmArgs = []
            for arg in node.args:
                llvmArgs.append(self.codegen(arg))
            return self.builder.call(func, llvmArgs)
        elif node.callee.__class__.__name__ == "MemberAccess":
            if node.callee.objectExpr.__class__.__name__ == "Var":
                moduleName = node.callee.objectExpr.name
                functionName = node.callee.memberName
                
                if moduleName in self.externalFunctions and functionName in self.externalFunctions[moduleName]:
                    func = self.externalFunctions[moduleName][functionName]
                    llvmArgs = []
                    for arg in node.args:
                        argValue = self.codegen(arg)
                        llvmArgs.append(argValue)
                    return self.builder.call(func, llvmArgs)
                elif moduleName in self.externalConstants and functionName in self.externalConstants[moduleName]:
                    func = self.externalConstants[moduleName][functionName]
                    return self.builder.call(func, [])
                
            obj = self.funcSymtab[node.callee.objectExpr.name]["addr"]
            methodName = node.callee.memberName
            info = self.funcSymtab.get(node.callee.objectExpr.name)
            if not info:
                raise NameError("Undefined variable: " + node.callee.objectExpr.name)
            className = info["datatypeName"]
            qualifiedName = f"{className}_{methodName}"
            llvmArgs = [obj]
            for arg in node.args:
                llvmArgs.append(self.codegen(arg))
            func = self.module.get_global(qualifiedName)
            if not func:
                raise NameError("Method " + qualifiedName + " not defined.")
            return self.builder.call(func, llvmArgs)
        else:
            raise SyntaxError("Invalid function call callee.")

    def PrintCall(self, node):
        fmtParts = []
        llvmArgs = []
        
        for i, arg in enumerate(node.args):
            val = self.codegen(arg)
            # Track if this value was directly printed
            directly_printed = False
            
            # Handle special case for custom datatype values
            val_type = val.type
            for module_name, module_functions in self.externalFunctions.items():
                if val_type == self.datatypes.get(module_name, None) and "print" in module_functions:
                    # The module has its own print function, use it
                    printFunc = module_functions["print"]
                    self.builder.call(printFunc, [val], name=f"{module_name}_print")
                    directly_printed = True
                    
                    # Add extra space if this isn't the last argument
                    if i < len(node.args) - 1:
                        fmtStr = self.createStringConstant(" ")
                        self.builder.call(self.printFunc, [fmtStr], name="print_space")
                    break
            
            # Skip this value in the format string if directly printed
            if directly_printed:
                continue
                
            # Handle standard types
            if val.type == ir.FloatType():
                val = self.builder.fpext(val, ir.DoubleType(), name="promoted")
                fmtParts.append("%f")
            elif val.type == ir.IntType(32):
                fmtParts.append("%d")
            elif val.type == ir.IntType(8):
                fmtParts.append("%c")
            elif val.type.is_pointer and val.type.pointee == ir.IntType(8):
                fmtParts.append("%s")
            else:
                # Generic handling for other types
                fmtParts.append("%p")  # Print as pointer by default
                
            llvmArgs.append(val)
        
        # If we have any standard types to print
        if fmtParts:
            fmtStr = " ".join(fmtParts) + "\n"
            fmtVal = self.createStringConstant(fmtStr)
            return self.builder.call(self.printFunc, [fmtVal] + llvmArgs)
        else:
            # If everything was directly printed, just print a newline
            if node.args:
                nlStr = self.createStringConstant("\n")
                return self.builder.call(self.printFunc, [nlStr], name="print_newline")
            else:
                # Empty print statement
                emptyStr = self.createStringConstant("\n")
                return self.builder.call(self.printFunc, [emptyStr], name="print_empty")

    def MemberAccess(self, node):
        objInfo = self.funcSymtab[node.objectExpr.name]
        idx = self.getMemberIndex(objInfo["datatypeName"], node.memberName)
        ptr = self.builder.gep(objInfo["addr"], [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), idx)], name="memberPtr")
        return self.builder.load(ptr, name=node.memberName)

    def Assign(self, node):
        if node.left.__class__.__name__ == "Var":
            info = self.funcSymtab.get(node.left.name)
            if not info:
                raise NameError("Variable '" + node.left.name + "' not declared.")
            val = self.codegen(node.right)
            
            # Generic type conversion
            val = self.convertValue(val, val.type, info["datatypeName"])
                
            self.builder.store(val, info["addr"])
            return val
        elif node.left.__class__.__name__ == "MemberAccess":
            return self.MemberAssignment(node.left, self.codegen(node.right))
        elif node.left.__class__.__name__ == "ArrayAccess":
            return self.ArrayElementAssignment(node.left, self.codegen(node.right))
        raise SyntaxError("Invalid left-hand side for assignment")

    def MemberAssignment(self, memberNode, val):
        objInfo = self.funcSymtab[memberNode.objectExpr.name]
        idx = self.getMemberIndex(objInfo["datatypeName"], memberNode.memberName)
        ptr = self.builder.gep(objInfo["addr"], [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), idx)], name="memberPtr")

        self.builder.store(val, ptr)
        return val

    def ArrayElementAssignment(self, arrayAccessNode, val):
        arrayInfo = self.funcSymtab.get(arrayAccessNode.array.name)
        if not arrayInfo:
            raise NameError(f"Undefined array: {arrayAccessNode.array.name}")

        idx = self.codegen(arrayAccessNode.index)
        arrayAddr = arrayInfo["addr"]

        if "isArray" in arrayInfo and "sizeVar" in arrayInfo:
            arrayPtr = self.builder.load(arrayAddr, name="array_ptr")
            elemPtr = self.builder.gep(arrayPtr, [idx], name="elem_ptr")
        else:
            elemPtr = self.builder.gep(arrayAddr, [
                ir.Constant(ir.IntType(32), 0),
                idx
            ], name="elem_ptr")

        self.builder.store(val, elemPtr)
        return val

    def ArrayAccess(self, node):
        arrayInfo = self.funcSymtab.get(node.array.name)
        if not arrayInfo:
            raise NameError(f"Undefined array: {node.array.name}")

        idx = self.codegen(node.index)
        arrayAddr = arrayInfo["addr"]

        if isinstance(idx, ir.Constant):
            if "size" in arrayInfo and idx.constant >= arrayInfo["size"]:
                raise IndexError(f"Array index {idx.constant} out of bounds for array of size {arrayInfo['size']}")
        else:
            if "size" in arrayInfo:
                size = ir.Constant(ir.IntType(32), arrayInfo["size"])
                is_valid = self.builder.icmp_signed("<", idx, size, name="bounds_check")
                with self.builder.if_then(is_valid, likely=True):
                    pass

        if "isArray" in arrayInfo and "sizeVar" in arrayInfo:
            arrayPtr = self.builder.load(arrayAddr, name="array_ptr")
            elemPtr = self.builder.gep(arrayPtr, [idx], name="elem_ptr")
        else:
            elemPtr = self.builder.gep(arrayAddr, [
                ir.Constant(ir.IntType(32), 0),
                idx
            ], name="elem_ptr")

        return self.builder.load(elemPtr, name="elem_value")

    def NewExpr(self, node):
        if node.className not in self.classStructTypes:
            raise ValueError("Unknown class: " + node.className)
        structType = self.classStructTypes[node.className]
        obj = self.builder.alloca(structType, name="objtmp")
        return obj
        
    def ArrayLiteral(self, node):
        if not node.elements:
            return ir.Constant(ir.ArrayType(ir.IntType(32), 0), [])

        firstElem = self.codegen(node.elements[0])
        elemType = firstElem.type

        arrayType = ir.ArrayType(elemType, len(node.elements))
        array = self.builder.alloca(arrayType, name="array_literal")

        for i, elem in enumerate(node.elements):
            elemValue = self.codegen(elem)
            if elemValue.type != elemType:
                if elemType == ir.FloatType() and elemValue.type == ir.IntType(32):
                    elemValue = self.builder.sitofp(elemValue, ir.FloatType())

            elemPtr = self.builder.gep(array, [
                ir.Constant(ir.IntType(32), 0),
                ir.Constant(ir.IntType(32), i)
            ], name=f"elem_ptr_{i}")
            self.builder.store(elemValue, elemPtr)

        return array 