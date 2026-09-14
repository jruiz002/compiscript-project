# compiler/semantic/types.py
"""
Type system definitions for Compiscript.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum, auto


class TypeKind(Enum):
    INTEGER = auto()
    FLOAT = auto()
    STRING = auto()
    BOOLEAN = auto()
    NULL = auto()
    ARRAY = auto()
    FUNCTION = auto()
    CLASS = auto()
    VOID = auto()
    ANY = auto()
    ERROR = auto()


class CompiscriptType:
    """Base class for all Compiscript types."""
    kind: TypeKind

    def is_numeric(self) -> bool:
        return self.kind in (TypeKind.INTEGER, TypeKind.FLOAT)

    def is_compatible_with(self, other: CompiscriptType) -> bool:
        if self.kind == TypeKind.ANY or other.kind == TypeKind.ANY:
            return True
        if self.kind == TypeKind.ERROR or other.kind == TypeKind.ERROR:
            return True
        # integer assignable to float (numeric widening)
        if self.kind == TypeKind.FLOAT and other.kind == TypeKind.INTEGER:
            return True
        return self == other

    def __repr__(self) -> str:
        return str(self)


@dataclass(frozen=True)
class PrimitiveType(CompiscriptType):
    kind: TypeKind

    def __str__(self) -> str:
        return self.kind.name.lower()

    def __eq__(self, other):
        if not isinstance(other, PrimitiveType):
            return False
        return self.kind == other.kind

    def __hash__(self):
        return hash(self.kind)


@dataclass
class ArrayType(CompiscriptType):
    element_type: CompiscriptType
    dimensions: int = 1

    def __post_init__(self):
        self.kind = TypeKind.ARRAY

    def __str__(self) -> str:
        return str(self.element_type) + "[]" * self.dimensions

    def __eq__(self, other):
        if not isinstance(other, ArrayType):
            return False
        return self.element_type == other.element_type and self.dimensions == other.dimensions

    def __hash__(self):
        return hash((TypeKind.ARRAY, self.element_type, self.dimensions))

    def is_compatible_with(self, other: CompiscriptType) -> bool:
        if other.kind in (TypeKind.ANY, TypeKind.ERROR):
            return True
        if not isinstance(other, ArrayType):
            return False
        return (self.element_type.is_compatible_with(other.element_type)
                and self.dimensions == other.dimensions)


@dataclass
class FunctionType(CompiscriptType):
    param_types: List[CompiscriptType]
    return_type: Optional[CompiscriptType] = None
    param_names: List[str] = field(default_factory=list)

    def __post_init__(self):
        self.kind = TypeKind.FUNCTION

    def __str__(self) -> str:
        params = ", ".join(str(t) for t in self.param_types)
        ret = str(self.return_type) if self.return_type else "void"
        return f"({params}) -> {ret}"

    def __eq__(self, other):
        if not isinstance(other, FunctionType):
            return False
        return self.param_types == other.param_types and self.return_type == other.return_type

    def __hash__(self):
        return hash((TypeKind.FUNCTION, tuple(self.param_types), self.return_type))


@dataclass
class ClassType(CompiscriptType):
    name: str
    superclass: Optional[ClassType] = None
    attributes: dict = field(default_factory=dict)
    methods: dict = field(default_factory=dict)

    def __post_init__(self):
        self.kind = TypeKind.CLASS

    def __str__(self) -> str:
        return self.name

    def __eq__(self, other):
        if not isinstance(other, ClassType):
            return False
        return self.name == other.name

    def __hash__(self):
        return hash((TypeKind.CLASS, self.name))

    def resolve_member(self, name: str) -> Optional[CompiscriptType]:
        """Lookup attribute or method, walking the inheritance chain."""
        if name in self.attributes:
            return self.attributes[name]
        if name in self.methods:
            return self.methods[name]
        if self.superclass:
            return self.superclass.resolve_member(name)
        return None

    def is_compatible_with(self, other: CompiscriptType) -> bool:
        if other.kind in (TypeKind.ANY, TypeKind.ERROR):
            return True
        if not isinstance(other, ClassType):
            return False
        # compatible if self IS other or a subclass of other
        cursor: Optional[ClassType] = self
        while cursor is not None:
            if cursor.name == other.name:
                return True
            cursor = cursor.superclass
        return False


# ---------------------------------------------------------------------------
# Singleton primitive instances
# ---------------------------------------------------------------------------
INTEGER = PrimitiveType(TypeKind.INTEGER)
FLOAT = PrimitiveType(TypeKind.FLOAT)
STRING = PrimitiveType(TypeKind.STRING)
BOOLEAN = PrimitiveType(TypeKind.BOOLEAN)
NULL = PrimitiveType(TypeKind.NULL)
VOID = PrimitiveType(TypeKind.VOID)
ANY = PrimitiveType(TypeKind.ANY)
ERROR_TYPE = PrimitiveType(TypeKind.ERROR)


def type_from_annotation(annotation_str: str, class_registry: dict = None) -> CompiscriptType:
    """
    Convert a type annotation string from the grammar to a CompiscriptType.
    Handles: 'integer', 'float', 'string', 'boolean', 'ClassName', and array variants 'T[]'.
    """
    s = annotation_str.strip()
    dims = 0
    while s.endswith("[]"):
        dims += 1
        s = s[:-2].strip()

    base = _resolve_base_type(s, class_registry)
    if dims > 0:
        return ArrayType(element_type=base, dimensions=dims)
    return base


def _resolve_base_type(name: str, class_registry: dict = None) -> CompiscriptType:
    mapping = {
        "integer": INTEGER,
        "float": FLOAT,
        "string": STRING,
        "boolean": BOOLEAN,
        "null": NULL,
        "void": VOID,
    }
    if name in mapping:
        return mapping[name]
    if class_registry and name in class_registry:
        return class_registry[name]
    return ANY
