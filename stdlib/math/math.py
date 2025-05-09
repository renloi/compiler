from typing import Dict, List, Tuple

functions: Dict[str, Tuple[str, List[str]]] = {
    "sin": ("float", ["float"]),
    "cos": ("float", ["float"]),
    "tan": ("float", ["float"]),
    "sqrt": ("float", ["float"]),
    "pow": ("float", ["float", "float"]),
    "log": ("float", ["float"]),
    "exp": ("float", ["float"]),
    "abs": ("float", ["float"]),
    "floor": ("float", ["float"]),
    "ceil": ("float", ["float"]),
    "round": ("float", ["float"]),
}

constants: Dict[str, Tuple[str, str]] = {
    "PI": ("float", "math_PI"),
    "E": ("float", "math_E"),
}

mapping: Dict[str, str] = {
    "sin": "math_sin",
    "cos": "math_cos",
    "tan": "math_tan",
    "sqrt": "math_sqrt",
    "pow": "math_pow",
    "log": "math_log",
    "exp": "math_exp",
    "abs": "math_abs",
    "floor": "math_floor",
    "ceil": "math_ceil",
    "round": "math_round",
} 