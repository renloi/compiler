from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Callable
from llvmlite import ir

@dataclass
class Module:
    name: str
    datatype: Optional[str] = None
    typeRepresentation: Optional[ir.Type] = None
    libraries: List[str] = field(default_factory=list)

    functions: Dict[str, Tuple[str, List[str]]] = field(default_factory=dict)
    constants: Dict[str, Tuple[str, str]] = field(default_factory=dict)
    mapping: Dict[str, str] = field(default_factory=dict)
    typeConversion: Dict[str, Dict[str, str]] = field(default_factory=dict)

    def func(self, returnType: str, *paramTypes: str, cName: Optional[str] = None):
        def decorator(f: Callable):
            self.functions[f.__name__] = (returnType, list(paramTypes))
            self.mapping[f.__name__] = cName or f"{self.name}_{f.__name__}"
            return f
        return decorator

    def const(self, constType: str, cSymbol: Optional[str] = None):
        def decorator(f: Callable):
            self.constants[f.__name__] = (constType, cSymbol or f"{self.name}_{f.__name__}")
            return f
        return decorator

    def addConversion(self, sourceType: str, targetType: str, functionName: str):
        self.typeConversion[functionName] = {
            'sourceType': sourceType,
            'targetType': targetType,
            'function': functionName
        }

    def export(self):
        return self 