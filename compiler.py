import subprocess
import os
import sys
import importlib.util
import glob
from lexer import Lexer
from parser import Parser
from codegen import Codegen
from llvmlite import binding as llvm
from lang import language
import argparse

def processImports(filePath, processedFiles=None):
    if processedFiles is None:
        processedFiles = set()

    if filePath in processedFiles:
        return ""

    processedFiles.add(filePath)

    with open(filePath, 'r') as f:
        content = f.readlines()

    resultContent = []
    importsToProcess = []
    stdlibImports = []

    for line in content:
        if line.strip().startswith("import"):
            importName = line.split("import")[1].strip()
            if importName.endswith(';'):
                importName = importName[:-1]  

            if os.path.exists(os.path.join("stdlib", importName)):
                stdlibImports.append(importName)
                resultContent.append("// " + line) 
            elif ".rn" in importName:
                importFile = importName.replace(".rn", "") + ".rn"
                importsToProcess.append(importFile)
                resultContent.append("// " + line) 
            else:
                resultContent.append("// " + line)
        else:
            resultContent.append(line)

    for importFile in importsToProcess:
        importFilePath = os.path.join(os.path.dirname(filePath), importFile)
        importedContent = processImports(importFilePath, processedFiles)
        resultContent.insert(0, importedContent) 

    return "".join(resultContent), stdlibImports

class Compiler:
    def __init__(self):

        self.language = {key: value.copy() if isinstance(value, dict) else value for key, value in language.items()}
        self.tokens = [(t["type"], t["regex"]) for t in self.language["tokens"]]
        self.customTokens = []
        self.lexer = None  
        self.stdlibModules = {}
        self.tempFiles = []
        self.customDatatypes = {}
        self.customTypeNames = set()

    def compileSource(self, sourceCode, outputExe, stdlibImports=None):
        if stdlibImports:
            self.loadStdlibModules(stdlibImports)

        allTokens = self.tokens + self.customTokens
        self.lexer = Lexer(allTokens)

        tokens = self.lexer.lex(sourceCode)

        parser = Parser(self.language, tokens)

        for typeName in self.customTypeNames:
            parser.classNames.add(typeName)

        ast = parser.parseProgram()
        codegen = Codegen(self.language)
        codegen.programNode = ast

        for typeName, typeInfo in self.customDatatypes.items():
            codegen.datatypes[typeName] = typeInfo

        for moduleName, moduleInfo in self.stdlibModules.items():
            functions = moduleInfo.get('functions', {})
            for funcName, funcInfo in functions.items():
                cFuncName = moduleInfo.get('mapping', {}).get(funcName, funcName)
                codegen.registerExternalFunction(
                    moduleName, 
                    funcName, 
                    cFuncName,
                    funcInfo[0],
                    funcInfo[1]
                )

            for constName, (constType, constFunc) in moduleInfo.get('constants', {}).items():
                codegen.registerExternalConstant(
                    moduleName,
                    constName,
                    constFunc,
                    constType
                )

        llvmModule = codegen.generateCode(ast)
        self.compileModule(llvmModule, outputExe, stdlibImports)
        self.cleanupTempFiles()

        if stdlibImports:
            for module in stdlibImports:
                self.cleanModule(module)
            print("All modules cleaned after compilation")

    def loadStdlibModules(self, moduleNames):
        for moduleName in moduleNames:
            modulePath = os.path.join("stdlib", moduleName, f"{moduleName}.py")
            if not os.path.exists(modulePath):
                print(f"Warning: stdlib module {moduleName} not found")
                continue

            spec = importlib.util.spec_from_file_location(moduleName, modulePath)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            meta = getattr(module, 'module', module)

            self.stdlibModules[moduleName] = {
                'functions': getattr(meta, 'functions', {}),
                'mapping': getattr(meta, 'mapping', {}),
                'constants': getattr(meta, 'constants', {}),
                'libraries': getattr(meta, 'libraries', [])
            }

            if hasattr(meta, 'datatype'):
                typeName = meta.datatype

                stdlibInfo = self.stdlibModules[moduleName]
                functionsDict = stdlibInfo['functions']
                mappingDict = stdlibInfo['mapping']

                def ensureConstructor(constructorName, sourceTypeName):
                    if constructorName not in functionsDict:
                        functionsDict[constructorName] = (typeName, [sourceTypeName])
                    if constructorName not in mappingDict:
                        mappingDict[constructorName] = f"{moduleName}_{constructorName}"

                    if not hasattr(module, 'typeConversion'):
                        module.typeConversion = {}
                    if constructorName not in module.typeConversion:
                        module.typeConversion[constructorName] = {
                            'sourceType': sourceTypeName,
                            'targetType': typeName,
                            'function': constructorName
                        }

                ensureConstructor('fromInt', 'int')
                ensureConstructor('fromString', 'string')

                for fn in list(functionsDict.keys()):
                    if fn not in mappingDict:
                        mappingDict[fn] = f"{moduleName}_{fn}"

                if hasattr(meta, 'type_representation'):
                    typeRepresentation = meta.type_representation
                elif hasattr(meta, 'typeRepresentation'):
                    typeRepresentation = meta.typeRepresentation
                else:
                    from llvmlite import ir
                    typeRepresentation = ir.PointerType(ir.IntType(8))

                self.customDatatypes[typeName] = typeRepresentation
                self.language["datatypes"][typeName] = typeRepresentation

                self.customTypeNames.add(typeName)
                print(f"Registered custom datatype: {typeName}")

                if hasattr(meta, 'token'):
                    token = meta.token
                    tokenType = token["type"]
                    tokenRegex = token["regex"]
                    self.customTokens.append((tokenType, tokenRegex))
                    print(f"Registered custom token: {tokenType}")

            else:
                functionsDict = self.stdlibModules[moduleName]['functions']
                mappingDict = self.stdlibModules[moduleName]['mapping']
                for fn in list(functionsDict.keys()):
                    if fn not in mappingDict:
                        mappingDict[fn] = f"{moduleName}_{fn}"

            self.compileStdlibModule(moduleName)

    def compileStdlibModule(self, moduleName):
        moduleDir = os.path.join("stdlib", moduleName)

        bcFile = os.path.join(moduleDir, f"{moduleName}.bc")
        cppFile = os.path.join(moduleDir, f"{moduleName}.cpp")

        if not os.path.exists(bcFile) or os.path.getmtime(cppFile) > os.path.getmtime(bcFile):
            print(f"Compiling stdlib module: {moduleName}")
            try:
                subprocess.run(["make", "-C", moduleDir], check=True)
            except subprocess.CalledProcessError as e:
                print(f"Error compiling stdlib module {moduleName}: {e}")
                sys.exit(1)

        self.tempFiles.append(bcFile)

    def compileModule(self, llvmModule, outputExe, stdlibImports=None):
        llvm.initialize()
        llvm.initialize_native_target()
        llvm.initialize_native_asmprinter()
        llvmIr = str(llvmModule)
        mod = llvm.parse_assembly(llvmIr)
        mod.verify()
        target = llvm.Target.from_default_triple()
        targetMachine = target.create_target_machine()
        objCode = targetMachine.emit_object(mod)
        objFilename = "output.o"
        with open(objFilename, "wb") as f:
            f.write(objCode)
        self.tempFiles.append(objFilename)

        bcFilename = "output.bc"
        with open(bcFilename, "w") as f:
            f.write(str(llvmModule))
        self.tempFiles.append(bcFilename)

        bcFiles = [bcFilename]
        libArguments = []
        if stdlibImports:
            for moduleName in stdlibImports:
                bcFile = os.path.join("stdlib", moduleName, f"{moduleName}.bc")
                if os.path.exists(bcFile):
                    bcFiles.append(bcFile)

                moduleInfo = self.stdlibModules.get(moduleName, {})
                if 'libraries' in moduleInfo:
                    libArguments.extend(moduleInfo['libraries'])

        linkedBcFilename = "linked.bc"
        subprocess.run(["llvm-link"] + bcFiles + ["-o", linkedBcFilename], check=True)
        self.tempFiles.append(linkedBcFilename)

        subprocess.run(["clang++", linkedBcFilename, "-o", outputExe, "-lstdc++", "-lm"] + libArguments, check=True)

        print(f"Executable '{outputExe}' generated.")

    def cleanupTempFiles(self):
        for file in self.tempFiles:
            if os.path.exists(file) and not file.startswith(os.path.join("stdlib", "")):
                os.remove(file)

        for pattern in ["*.o", "*.bc", "*.ll", "*.s"]:
            for file in glob.glob(pattern):
                if os.path.exists(file) and not file.startswith(os.path.join("stdlib", "")):
                    os.remove(file)

    def cleanModule(self, moduleName):
        """Clean generated files for a specific stdlib module"""
        moduleDir = os.path.join("stdlib", moduleName)
        if os.path.exists(moduleDir):
            try:
                subprocess.run(["make", "-C", moduleDir, "clean"], check=True)
                print(f"Cleaned module: {moduleName}")
            except subprocess.CalledProcessError as e:
                print(f"Error cleaning module {moduleName}: {e}")
        else:
            print(f"Module {moduleName} not found")

    def cleanAllModules(self):
        """Clean generated files for all stdlib modules"""
        for moduleDir in glob.glob(os.path.join("stdlib", "*")):
            if os.path.isdir(moduleDir) and os.path.exists(os.path.join(moduleDir, "makefile")):
                moduleName = os.path.basename(moduleDir)
                self.cleanModule(moduleName)



if __name__ == "__main__":
    argparser = argparse.ArgumentParser(prog='renloi', description='compiler for the renloi language')

    argparser.add_argument('-clean', help='Clean generated files for stdlib modules', default=False, action='store_true')
    argparser.add_argument('-clean-module', help='Clean generated files for specific module')
    argparser.add_argument('-o', help='Sets the output file', nargs=1, dest='output')
    argparser.add_argument('input', nargs='+')
    

    args = argparser.parse_args(sys.argv[1:])

    if args.clean or args.clean_module != None:
        compiler = Compiler()
        if args.clean_module != None:
            compiler.cleanModule(args.clean_module)
        else:
            compiler.cleanAllModules()
        sys.exit(0)
    
    sourceFile = args.input[0]

    finalContent, stdlibImports = processImports(sourceFile)

    baseFilename = os.path.splitext(sourceFile)[0]
    outputExe = baseFilename + ".exe"
    if args.output != None:
        outputExe = args.output[0]
    compiler = Compiler()
    compiler.compileSource(finalContent, outputExe, stdlibImports)