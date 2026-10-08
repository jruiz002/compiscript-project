"""Analizador semántico de la Fase 1, extendido para la generación de código intermedio."""
from .semantic_analyzer import SemanticAnalyzer
from .symbol_table import SymbolTable, Symbol, SymbolKind, Scope, ActivationRecord, GlobalAllocator, WORD_SIZE
from .errors import ErrorCollector, SemanticError, Severity
from .types import (
    CompiscriptType, TypeKind, PrimitiveType, ArrayType, FunctionType, ClassType,
    INTEGER, FLOAT, STRING, BOOLEAN, NULL, VOID, ANY, ERROR_TYPE, type_from_annotation,
)

__all__ = [
    "SemanticAnalyzer",
    "SymbolTable", "Symbol", "SymbolKind", "Scope", "ActivationRecord", "GlobalAllocator", "WORD_SIZE",
    "ErrorCollector", "SemanticError", "Severity",
    "CompiscriptType", "TypeKind", "PrimitiveType", "ArrayType", "FunctionType", "ClassType",
    "INTEGER", "FLOAT", "STRING", "BOOLEAN", "NULL", "VOID", "ANY", "ERROR_TYPE", "type_from_annotation",
]
