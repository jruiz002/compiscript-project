# compiler/semantic/errors.py
"""
Semantic error and warning classes for Compiscript.

Copiado sin cambios de semantic-analyzer/compiler/semantic/errors.py (Fase 1) — ver
FEATURES.md ticket A-0.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List


class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"


@dataclass
class SemanticError:
    message: str
    line: int
    column: int
    severity: Severity = Severity.ERROR

    def __str__(self) -> str:
        tag = "[ERROR]" if self.severity == Severity.ERROR else "[WARNING]"
        return f"{tag} Line {self.line}:{self.column} — {self.message}"


class ErrorCollector:
    """Accumulates all semantic errors without stopping at the first one."""

    def __init__(self):
        self._errors: List[SemanticError] = []

    def error(self, message: str, line: int, column: int):
        self._errors.append(SemanticError(message, line, column, Severity.ERROR))

    def warning(self, message: str, line: int, column: int):
        self._errors.append(SemanticError(message, line, column, Severity.WARNING))

    def has_errors(self) -> bool:
        return any(e.severity == Severity.ERROR for e in self._errors)

    def all_errors(self) -> List[SemanticError]:
        return list(self._errors)

    def errors_only(self) -> List[SemanticError]:
        return [e for e in self._errors if e.severity == Severity.ERROR]

    def warnings_only(self) -> List[SemanticError]:
        return [e for e in self._errors if e.severity == Severity.WARNING]

    def count(self) -> int:
        return len(self._errors)

    def clear(self):
        self._errors.clear()

    def __iter__(self):
        return iter(self._errors)
