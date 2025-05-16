from stdlib.module_utils import StdModule

module = StdModule(name="math")

for fn in ["sin", "cos", "tan", "sqrt", "log", "exp", "abs", "floor", "ceil", "round"]:
    module.functions[fn] = ("float", ["float"])

module.functions["pow"] = ("float", ["float", "float"])

module.constants["PI"] = ("float", "math_PI")
module.constants["E"] = ("float", "math_E")

module = module.export() 