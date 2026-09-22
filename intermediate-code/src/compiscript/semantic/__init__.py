"""Analizador semántico de Compiscript (copiado y extendido de la Fase 1, ver FEATURES.md
ticket A-0) más las extensiones de la Fase 2: tablas laterales para ICG (A-1), tabla de
símbolos con offsets/registros de activación (A-2) y layout de clases/vtables (A-4, en
ir.memory_layout, que consume `SemanticAnalyzer.class_registry`).
"""
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
