from llvmlite import ir

class DeclarationCodegen:
    def VarDecl(self, node):
        if node.datatypeName.endswith("[]"):
            baseTypeName = node.datatypeName[:-2]
            if baseTypeName in self.datatypes:
                elemType = self.datatypes[baseTypeName]
            elif baseTypeName in self.classStructTypes:
                elemType = self.classStructTypes[baseTypeName]
            else:
                raise ValueError("Unknown datatype: " + baseTypeName)

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

                for i in range(numElements):
                    srcPtr = self.builder.gep(arrayLiteral, [
                        ir.Constant(ir.IntType(32), 0),
                        ir.Constant(ir.IntType(32), i)
                    ], name=f"src_ptr_{i}")

                    dstPtr = self.builder.gep(addr, [
                        ir.Constant(ir.IntType(32), 0),
                        ir.Constant(ir.IntType(32), i)
                    ], name=f"dst_ptr_{i}")

                    val = self.builder.load(srcPtr, name=f"elem_{i}")
                    self.builder.store(val, dstPtr)

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

        if node.datatypeName in self.datatypes:
            varType = self.datatypes[node.datatypeName]
            addr = self.builder.alloca(varType, name=node.name)
        elif node.datatypeName in self.classStructTypes:
            structType = self.classStructTypes[node.datatypeName]
            addr = self.builder.alloca(structType, name=node.name)
        else:
            raise ValueError("Unknown datatype: " + node.datatypeName)

        if node.init:
            init_val = self.codegen(node.init)
            
            # Handle type conversions
            if node.datatypeName == "float" and init_val.type == ir.IntType(32):
                init_val = self.builder.sitofp(init_val, ir.FloatType())
            else:
                # Generic type conversion
                init_val = self.convertValue(init_val, init_val.type, node.datatypeName)
                
            self.builder.store(init_val, addr)

        self.funcSymtab[node.name] = {"addr": addr, "datatypeName": node.datatypeName}
        return addr

    def ArrayDecl(self, node):
        elemTypeName = node.elemType
        if elemTypeName in self.datatypes:
            elemType = self.datatypes[elemTypeName]
        elif elemTypeName in self.classStructTypes:
            elemType = self.classStructTypes[elemTypeName]
        else:
            raise ValueError("Unknown element type: " + elemTypeName)

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
            if field.datatypeName in self.datatypes:
                fieldTypes.append(self.datatypes[field.datatypeName])
            elif field.datatypeName in self.classStructTypes:
                fieldTypes.append(self.classStructTypes[field.datatypeName])
            else:
                raise ValueError("Unknown datatype: " + field.datatypeName)

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
        func = ir.Function(self.module, funcType, name=funcName)
        entry = func.append_basic_block("entry")
        self.builder = ir.IRBuilder(entry)
        self.funcSymtab = {}
        self.funcSymtab["self"] = {"addr": func.args[0], "datatypeName": node.className}
        for i, param in enumerate(node.parameters, start=1):
            self.funcSymtab[param.name] = {"addr": func.args[i], "datatypeName": param.datatypeName}
        retval = None
        for stmt in node.body:
            retval = self.codegen(stmt)
        if not self.builder.block.terminator:
            self.builder.ret(retval if retval else ir.Constant(ir.IntType(32), 0))

    def Function(self, node):
        retTypeStr = node.returnType if hasattr(node, "returnType") else "int"
        if retTypeStr in self.datatypes:
            returnType = self.datatypes[retTypeStr]
        else:
            returnType = ir.IntType(32)

        funcType = ir.FunctionType(returnType, [])
        func = ir.Function(self.module, funcType, name=node.name)
        entry = func.append_basic_block("entry")
        self.builder = ir.IRBuilder(entry)
        self.funcSymtab = {}
        retval = None
        for stmt in node.body:
            retval = self.codegen(stmt)
        if not self.builder.block.terminator:
            self.builder.ret(retval if retval is not None else ir.Constant(returnType, 0)) 