from llvmlite import ir

class DeclarationCodegen:
    def getTypeFromName(self, typeName):
        if typeName in self.datatypes:
            return self.datatypes[typeName]
        elif typeName in self.classStructTypes:
            return self.classStructTypes[typeName]
        else:
            raise ValueError("Unknown datatype: " + typeName)
    
    def VarDecl(self, node):
        if node.datatypeName.endswith("[]"):
            baseTypeName = node.datatypeName[:-2]
            elemType = self.getTypeFromName(baseTypeName)

            if node.init and node.init.__class__.__name__ == "ArrayLiteral":
                arrayLiteral = self.codegen(node.init)
                numElements = len(node.init.elements)
                arrayType = ir.ArrayType(elemType, numElements)
                addr = self.builder.alloca(arrayType, name=node.name)

                self.funcSymtab[node.name] = {
                    "addr": addr, 
                    "datatypeName": baseTypeName, 
                    "isArray": True,
                    "size": numElements
                }

                self.emitArrayStore(addr, arrayLiteral, numElements)

                return addr
            else:
                size = 10
                arrayType = ir.ArrayType(elemType, size)
                addr = self.builder.alloca(arrayType, name=node.name)

                self.funcSymtab[node.name] = {
                    "addr": addr, 
                    "datatypeName": baseTypeName, 
                    "isArray": True,
                    "size": size
                }
                return addr

        varType = self.getTypeFromName(node.datatypeName)
        addr = self.builder.alloca(varType, name=node.name)

        if node.init:
            initVal = self.codegen(node.init)
            initVal = self.convertValue(initVal, initVal.type, node.datatypeName)
            self.builder.store(initVal, addr)

        self.funcSymtab[node.name] = {"addr": addr, "datatypeName": node.datatypeName}
        return addr

    def ArrayDecl(self, node):
        elemTypeName = node.elemType
        elemType = self.getTypeFromName(elemTypeName)

        sizeVal = None
        if node.size:
            sizeVal = self.codegen(node.size)
            if not isinstance(sizeVal, ir.Constant):
                mallocFunc = self.getMallocFunc()
                byteSize = self.builder.mul(sizeVal, ir.Constant(ir.IntType(32), 4), name="bytesize")
                arrayPtr = self.builder.call(mallocFunc, [byteSize], name="arrayptr")
                arrayPtr = self.builder.bitcast(arrayPtr, ir.PointerType(elemType), name="typedptr")
                addr = self.builder.alloca(ir.PointerType(elemType), name=node.name)
                self.builder.store(arrayPtr, addr)
                self.funcSymtab[node.name] = {
                    "addr": addr, 
                    "datatypeName": elemTypeName, 
                    "isArray": True,
                    "sizeVar": sizeVal
                }
                return addr
            else:
                size = int(sizeVal.constant)  
        else:
            size = 10  

        arrayType = ir.ArrayType(elemType, size)
        addr = self.builder.alloca(arrayType, name=node.name)

        self.funcSymtab[node.name] = {
            "addr": addr, 
            "datatypeName": elemTypeName, 
            "isArray": True,
            "size": size
        }
        return addr

    def ClassDeclaration(self, node):
        structType = ir.global_context.get_identified_type(node.name)
        fieldTypes = []
        for field in node.fields:
            fieldTypes.append(self.getTypeFromName(field.datatypeName))

        structType.set_body(*fieldTypes)
        self.classStructTypes[node.name] = structType
        for method in node.methods:
            self.MethodDecl(method)

    def MethodDecl(self, node):
        if node.className not in self.classStructTypes:
            raise ValueError("Unknown class in method: " + node.className)
            
        classType = self.classStructTypes[node.className]
        paramTypes = [ir.PointerType(classType)]

        for param in node.parameters:
            dt = param.datatypeName
            if dt in self.datatypes:
                paramTypes.append(self.datatypes[dt])
            elif dt in self.classStructTypes:
                paramTypes.append(ir.PointerType(self.classStructTypes[dt]))
            else:
                raise ValueError("Unknown datatype in method parameter: " + dt)
                
        returnType = self.datatypes[node.returnType] if hasattr(node, "returnType") and node.returnType in self.datatypes else ir.IntType(32)
        funcType = ir.FunctionType(returnType, paramTypes)
        
        funcName = f"{node.className}_{node.name}"
        if funcName in self.module.globals:
            return self.module.globals[funcName]
            
        return self.defineFunction(funcName, funcType, ["self"] + [p.name for p in node.parameters], node.body)

    def Function(self, node):
        retTypeStr = node.returnType if hasattr(node, "returnType") else "int"
        returnType = self.datatypes.get(retTypeStr, ir.IntType(32))
        funcType = ir.FunctionType(returnType, [])
        
        return self.defineFunction(node.name, funcType, [], node.body)
        
    def defineFunction(self, name, funcType, paramNames, body):
        func = ir.Function(self.module, funcType, name=name)
        entry = func.append_basic_block("entry")
        self.builder = ir.IRBuilder(entry)
        self.funcSymtab = {}
        
        for i, paramName in enumerate(paramNames):
            if paramName == "self":
                self.funcSymtab[paramName] = {"addr": func.args[i], "datatypeName": name.split("_")[0]}
            else:
                self.funcSymtab[paramName] = {"addr": func.args[i], "datatypeName": "param"}
                
        retval = None
        for stmt in body:
            retval = self.codegen(stmt)
            
        returnType = funcType.return_type
        if not self.builder.block.terminator:
            self.builder.ret(retval if retval is not None else ir.Constant(returnType, 0))
            
        return func 