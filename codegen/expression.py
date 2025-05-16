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
        value = node.value
        if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
            value = value[1:-1]
        return self.createStringConstant(value)

    def Char(self, node):
        return ir.Constant(ir.IntType(8), ord(node.value))

    def BinOp(self, node):
        custom_res = self._try_custom_binop(node)
        if custom_res is not None:
            return custom_res
        
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

    def handleFunctionArgs(self, func, args):
        llvmArgs = []
        for arg in args:
            llvmArgs.append(self.codegen(arg))
        return self.builder.call(func, llvmArgs)
        
    def FunctionCall(self, node):
        if node.callee.__class__.__name__ == "Var":
            if node.callee.name == "print":
                return self.PrintCall(node)
            func = self.module.get_global(node.callee.name)
            if not func:
                raise NameError("Unknown function: " + node.callee.name)
            return self.handleFunctionArgs(func, node.args)
        elif node.callee.__class__.__name__ == "MemberAccess":
            if node.callee.objectExpr.__class__.__name__ == "Var":
                moduleName = node.callee.objectExpr.name
                functionName = node.callee.memberName
                
                if moduleName in self.externalFunctions and functionName in self.externalFunctions[moduleName]:
                    func = self.externalFunctions[moduleName][functionName]
                    return self.handleFunctionArgs(func, node.args)
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

    def formatPrintValue(self, val, i, args, fmtParts, llvmArgs):
        directlyPrinted = False
        
        valType = val.type
        for moduleName, moduleFunctions in self.externalFunctions.items():
            if valType == self.datatypes.get(moduleName, None) and "print" in moduleFunctions:
                printFunc = moduleFunctions["print"]
                self.builder.call(printFunc, [val], name=f"{moduleName}_print")
                directlyPrinted = True
                
                if i < len(args) - 1:
                    fmtStr = self.createStringConstant(" ")
                    self.builder.call(self.printFunc, [fmtStr], name="print_space")
                break
                
        if directlyPrinted:
            return True
                
        if valType == ir.FloatType():
            val = self.builder.fpext(val, ir.DoubleType(), name="promoted")
            fmtParts.append("%f")
        elif valType == ir.IntType(32):
            fmtParts.append("%d")
        elif valType == ir.IntType(8):
            fmtParts.append("%c")
        elif valType.is_pointer and valType.pointee == ir.IntType(8):
            fmtParts.append("%s")
        else:
            fmtParts.append("%p")
            
        llvmArgs.append(val)
        return False

    def PrintCall(self, node):
        fmtParts = []
        llvmArgs = []
        
        for i, arg in enumerate(node.args):
            val = self.codegen(arg)
            self.formatPrintValue(val, i, node.args, fmtParts, llvmArgs)
        
        if fmtParts:
            fmtStr = " ".join(fmtParts) + "\n"
            fmtVal = self.createStringConstant(fmtStr)
            return self.builder.call(self.printFunc, [fmtVal] + llvmArgs)
        else:
            nlStr = self.createStringConstant("\n" if node.args else "\n")
            return self.builder.call(self.printFunc, [nlStr], name="print_newline")

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

    def getArrayElementPtr(self, arrayInfo, idx):
        arrayAddr = arrayInfo["addr"]
        
        if "isArray" in arrayInfo and "sizeVar" in arrayInfo:
            arrayPtr = self.builder.load(arrayAddr, name="array_ptr")
            return self.builder.gep(arrayPtr, [idx], name="elem_ptr")
        else:
            return self.builder.gep(arrayAddr, [
                ir.Constant(ir.IntType(32), 0),
                idx
            ], name="elem_ptr")

    def checkArrayBounds(self, arrayInfo, idx):
        if isinstance(idx, ir.Constant):
            if "size" in arrayInfo and int(idx.constant) >= arrayInfo["size"]:
                raise IndexError(f"Array index {idx.constant} out of bounds for array of size {arrayInfo['size']}")
        else:
            if "size" in arrayInfo:
                size = ir.Constant(ir.IntType(32), arrayInfo["size"])
                isValid = self.builder.icmp_signed("<", idx, size, name="bounds_check")
                with self.builder.if_then(isValid, likely=True):
                    pass

    def ArrayElementAssignment(self, arrayAccessNode, val):
        arrayInfo = self.funcSymtab.get(arrayAccessNode.array.name)
        if not arrayInfo:
            raise NameError(f"Undefined array: {arrayAccessNode.array.name}")

        idx = self.codegen(arrayAccessNode.index)
        self.checkArrayBounds(arrayInfo, idx)
        elemPtr = self.getArrayElementPtr(arrayInfo, idx)
        self.builder.store(val, elemPtr)
        return val

    def ArrayAccess(self, node):
        arrayInfo = self.funcSymtab.get(node.array.name)
        if not arrayInfo:
            raise NameError(f"Undefined array: {node.array.name}")

        idx = self.codegen(node.index)
        self.checkArrayBounds(arrayInfo, idx)
        elemPtr = self.getArrayElementPtr(arrayInfo, idx)
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

    # ------------------------------------------------------------------
    # Helper utilities for custom datatype operator overloading
    # ------------------------------------------------------------------
    def _infer_datatype_name(self, ast_node):
        """Best-effort inference of the semantic datatype name from an AST node.
        This relies on symbol-table information populated during code-generation
        of declarations. It falls back to primitive literal types when possible.
        Returns the datatype name as declared in source code, or None if it
        cannot be determined with confidence."""
        cls = ast_node.__class__.__name__
        if cls == "Var":
            info = self.funcSymtab.get(ast_node.name)
            if info:
                return info.get("datatypeName")
        elif cls == "Num":
            return "int"
        elif cls == "FloatNum":
            return "float"
        elif cls == "String":
            return "string"
        elif cls == "Char":
            return "char"
        return None  # Fallback when we cannot deduce the type reliably.

    def _try_custom_binop(self, node):
        """Intercept binary operations to see if either operand's datatype
        provides its own implementation (e.g. bint.add, bigdecimal.mul, etc.).
        If a matching implementation is found, emit a call to the external
        function and return the resulting LLVM value. Otherwise, return None
        so that the default arithmetic / comparison logic is used."""
        # Map language operator tokens to canonical function names used inside
        # stdlib modules.
        op_to_func = {
            '+': 'add',
            '-': 'sub',
            '*': 'mul',
            '/': 'div',
            '%': 'mod',
            '&': 'and',
            '^': 'xor',
            '|': 'or',
            '<<': 'lshift',
            '>>': 'rshift'
        }

        func_name = op_to_func.get(node.op)
        if not func_name:
            return None  # Not an arithmetic op we can overload here.

        # Code-generate operands first (required regardless of path).
        left_val = self.codegen(node.left)
        right_val = self.codegen(node.right)

        left_type_name = self._infer_datatype_name(node.left)
        right_type_name = self._infer_datatype_name(node.right)

        # Decide which side's datatype will drive the dispatch. Prefer the left
        # operand; if it does not expose the needed function, attempt right.
        chosen_type = None
        if left_type_name in self.externalFunctions and \
           func_name in self.externalFunctions[left_type_name]:
            chosen_type = left_type_name
        elif right_type_name in self.externalFunctions and \
             func_name in self.externalFunctions[right_type_name]:
            chosen_type = right_type_name

        if not chosen_type:
            return None  # No custom implementation available.

        # Retrieve the LLVM function for the overloaded operator.
        llvm_func = self.externalFunctions[chosen_type][func_name]

        # Ensure both operands are of the chosen datatype, performing implicit
        # conversions when possible through convertValue.
        if left_type_name != chosen_type:
            left_val = self.convertValue(left_val, left_val.type, chosen_type)
        if right_type_name != chosen_type:
            right_val = self.convertValue(right_val, right_val.type, chosen_type)

        return self.builder.call(llvm_func, [left_val, right_val],
                                 name=f"{chosen_type}_{func_name}_result") 