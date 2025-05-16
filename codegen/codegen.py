from llvmlite import ir
import importlib
from .expression import ExpressionCodegen
from .statement import StatementCodegen
from .declaration import DeclarationCodegen

class Codegen(ExpressionCodegen, StatementCodegen, DeclarationCodegen):
    def __init__(self, language):
        self.language = language
        self.module = ir.Module(name="module")
        self.builder = None
        self.funcSymtab = {}
        self.stringCounter = 0
        self.programNode = None
        self.classStructTypes = {}
        self.declarePrintFunc()
        self.binOpMap = language["operators"]["binOpMap"]
        self.compMap = language["operators"]["compMap"]
        self.datatypes = language["datatypes"]
        self.arrayTypesCache = {}
        self.externalFunctions = {}
        self.externalConstants = {}
        self.modules = {}
        self.opFuncMap = {op: vals[0] for op, vals in self.binOpMap.items()}

        self.printSpec = {
            ir.FloatType(): '%f',
            ir.IntType(32): '%d',
            ir.IntType(8):  '%c'
        }

    def initModule(self, moduleName):
        if moduleName not in self.modules:
            self.modules[moduleName] = {}
            
        return self.modules[moduleName]

    def registerExternalFunction(self, moduleName, funcName, cFuncName, returnType, paramTypes):
        self.initModule(moduleName)
        llvmReturnType = self.datatypes.get(returnType, ir.IntType(32))
        llvmParamTypes = []
        
        for paramType in paramTypes:
            if paramType in self.datatypes:
                llvmParamTypes.append(self.datatypes[paramType])
            elif paramType in self.classStructTypes:
                llvmParamTypes.append(ir.PointerType(self.classStructTypes[paramType]))
            else:
                llvmParamTypes.append(ir.IntType(32))
                
        funcType = ir.FunctionType(llvmReturnType, llvmParamTypes)
        func = ir.Function(self.module, funcType, name=cFuncName)
        
        if moduleName not in self.externalFunctions:
            self.externalFunctions[moduleName] = {}
            
        self.externalFunctions[moduleName][funcName] = func
        self.modules[moduleName][funcName] = func
        
        return func
        
    def registerExternalConstant(self, moduleName, constName, cFuncName, constType):
        self.initModule(moduleName)
        llvmReturnType = self.datatypes.get(constType, ir.IntType(32))
        funcType = ir.FunctionType(llvmReturnType, [])
        
        func = ir.Function(self.module, funcType, name=cFuncName)
        
        if moduleName not in self.externalConstants:
            self.externalConstants[moduleName] = {}
            
        self.externalConstants[moduleName][constName] = func
        self.modules[moduleName][constName] = func
        
        return func

    def declarePrintFunc(self):
        printType = ir.FunctionType(ir.IntType(32), [ir.PointerType(ir.IntType(8))], var_arg=True)
        self.printFunc = ir.Function(self.module, printType, name="printf")

    def generateCode(self, node):
        if node.__class__.__name__ == "Program":
            self.programNode = node
            for cls in node.classes:
                self.ClassDeclaration(cls)
            for func in node.functions:
                self.Function(func)
        return self.module

    def createStringConstant(self, s):
        sBytes = bytearray((s + "\0").encode("utf8"))
        strType = ir.ArrayType(ir.IntType(8), len(sBytes))
        name = ".str." + str(self.stringCounter)
        self.stringCounter += 1
        globalStr = ir.GlobalVariable(self.module, strType, name=name)
        globalStr.global_constant = True
        globalStr.linkage = "private"
        globalStr.initializer = ir.Constant(strType, sBytes)
        zero = ir.Constant(ir.IntType(32), 0)
        return self.builder.gep(globalStr, [zero, zero], name="str")

    def getMemberIndex(self, className, memberName):
        for cls in self.programNode.classes:
            if cls.name == className:
                for i, field in enumerate(cls.fields):
                    if field.name == memberName:
                        return i
        raise NameError("Member '" + memberName + "' not found in class '" + className + "'.")

    def promoteToFloat(self, left, right):
        if left.type != ir.FloatType():
            left = self.builder.sitofp(left, ir.FloatType())
        if right.type != ir.FloatType():
            right = self.builder.sitofp(right, ir.FloatType())
        return left, right

    def genArith(self, node, intOp, floatOp, resName):
        left = self.codegen(node.left)
        right = self.codegen(node.right)
        if floatOp is not None and (left.type == ir.FloatType() or right.type == ir.FloatType()):
            left, right = self.promoteToFloat(left, right)
            return getattr(self.builder, floatOp)(left, right, name="f" + resName)
        return getattr(self.builder, intOp)(left, right, name=resName)

    def genCompare(self, node, intCmp, floatCmp, resName):
        left = self.codegen(node.left)
        right = self.codegen(node.right)
        if left.type == ir.FloatType() or right.type == ir.FloatType():
            left, right = self.promoteToFloat(left, right)
            cmpRes = self.builder.fcmp_ordered(floatCmp, left, right, name="f" + resName)
        else:
            cmpRes = self.builder.icmp_signed(intCmp, left, right, name=resName)
        return self.builder.zext(cmpRes, ir.IntType(32), name=resName + "Int")

    def codegen(self, node):
        nodeType = node.__class__.__name__
        method = getattr(self, nodeType, None)
        if method is None:
            raise NotImplementedError("Codegen not implemented for " + nodeType)
        return method(node)
        
    def getMallocFunc(self):
        if hasattr(self, "mallocFunc"):
            return self.mallocFunc

        mallocType = ir.FunctionType(
            ir.PointerType(ir.IntType(8)),
            [ir.IntType(32)]
        )
        self.mallocFunc = ir.Function(self.module, mallocType, name="malloc")
        return self.mallocFunc
        
    def convertValue(self, value, sourceType, targetTypeName):
        if targetTypeName == "float" and sourceType == ir.IntType(32):
            return self.builder.sitofp(value, ir.FloatType())
            
        if sourceType == self.datatypes.get(targetTypeName, None):
            return value
            
        if targetTypeName in self.externalFunctions:
            moduleFuncs = self.externalFunctions[targetTypeName]

            intCtor = 'fromInt' if 'fromInt' in moduleFuncs else 'from_int'
            strCtor = 'fromString' if 'fromString' in moduleFuncs else 'from_string'

            if sourceType == ir.IntType(32) and intCtor in moduleFuncs:
                convFunc = moduleFuncs[intCtor]
                return self.builder.call(convFunc, [value], name=f"{targetTypeName}FromInt")

            if value.type.is_pointer and value.type.pointee == ir.IntType(8) and strCtor in moduleFuncs:
                convFunc = moduleFuncs[strCtor]
                return self.builder.call(convFunc, [value], name=f"{targetTypeName}FromString")

        for moduleName in self.externalFunctions:
            try:
                module = importlib.import_module(f"stdlib.{moduleName}.{moduleName}")
                
                metaObj = getattr(module, 'module', module)
                convTable = getattr(metaObj, 'typeConversion', getattr(metaObj, 'type_conversion', {}))

                for convName, convInfo in convTable.items():
                    sourceTypeName = convInfo.get('sourceType', convInfo.get('source_type', ''))
                    convTargetType = convInfo.get('targetType', convInfo.get('target_type', ''))
                    
                    if (convTargetType == targetTypeName and 
                        ((sourceTypeName == "int" and sourceType == ir.IntType(32)) or
                         (sourceTypeName == "float" and sourceType == ir.FloatType()) or
                         (sourceTypeName == "string" and value.type.is_pointer and value.type.pointee == ir.IntType(8)) or
                         (sourceTypeName in self.datatypes and sourceType == self.datatypes[sourceTypeName]))):
                        
                        funcName = convInfo.get('function', '')
                        if funcName in self.externalFunctions[moduleName]:
                            convFunc = self.externalFunctions[moduleName][funcName]
                            return self.builder.call(convFunc, [value], name=f"{targetTypeName}_conv")
            except (ImportError, AttributeError):
                continue
                
        return value 

    def externalFunction(self, moduleName, funcName):
        """Return the registered LLVM Function for a stdlib module or None."""
        return self.externalFunctions.get(moduleName, {}).get(funcName)

    def externalConstant(self, moduleName, constName):
        """Return the registered LLVM Function wrapper for a constant or None."""
        return self.externalConstants.get(moduleName, {}).get(constName)

    def callExternal(self, moduleName, funcName, args=None, constant=False):
        store = self.externalConstants if constant else self.externalFunctions
        func = store.get(moduleName, {}).get(funcName)
        if func is None:
            return None
        return self.builder.call(func, args or [])

    def elementPointer(self, arrayInfoOrAddr, idx, name="elem_pointer"):
        if isinstance(arrayInfoOrAddr, dict):
            arrayInfo = arrayInfoOrAddr
            arrayAddr = arrayInfo["addr"]

            if "isArray" in arrayInfo and "sizeVar" in arrayInfo:
                arrayPtr = self.builder.load(arrayAddr, name="array_ptr")
                return self.builder.gep(arrayPtr, [idx], name=name)

            return self.builder.gep(arrayAddr, [ir.Constant(ir.IntType(32), 0), idx], name=name)

        return self.builder.gep(arrayInfoOrAddr, [ir.Constant(ir.IntType(32), 0), idx], name=name)

    def structFieldPointer(self, structPointer, fieldIndex, name="field_pointer"):
        return self.builder.gep(structPointer, [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), fieldIndex)], name=name)

    def emitArrayStore(self, dstArr, srcArr, nElems):
        for i in range(nElems):
            idxConst = ir.Constant(ir.IntType(32), i)
            srcPointer = self.elementPointer(srcArr, idxConst, f"src_{i}")
            dstPointer = self.elementPointer(dstArr, idxConst, f"dst_{i}")
            value = self.builder.load(srcPointer, name=f"load_{i}")
            self.builder.store(value, dstPointer)

    def checkArrayBounds(self, arrayInfo, idx):
        if isinstance(idx, ir.Constant):
            if "size" in arrayInfo and int(idx.constant) >= arrayInfo["size"]:
                raise IndexError(f"Array index {idx.constant} out of bounds for array of size {arrayInfo['size']}")
        elif "size" in arrayInfo:
            sizeConst = ir.Constant(ir.IntType(32), arrayInfo["size"])
            isValid = self.builder.icmp_signed("<", idx, sizeConst, name="bounds_check")
            with self.builder.if_then(isValid, likely=True):
                pass 

    def preparePrintArg(self, value):
        valueType = value.type
        for moduleName, funcTable in self.externalFunctions.items():
            if valueType == self.datatypes.get(moduleName, None) and 'print' in funcTable:
                self.builder.call(funcTable['print'], [value])
                return True, None, None

        if valueType == ir.FloatType():
            value = self.builder.fpext(value, ir.DoubleType())
        spec = self.printSpec.get(valueType, '%s' if valueType.is_pointer else '%p')
        return False, spec, value 