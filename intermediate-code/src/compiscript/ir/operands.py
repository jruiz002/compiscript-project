"""Operandos del TAC: Temp, VarRef, Const, StrConst, Label.

Diseño: docs/TAC_LANGUAGE.md §1. Todos son inmutables (frozen dataclasses) para que puedan
vivir como valores dentro de un Quad y compararse/hashearse con seguridad. Ticket B-1.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Union


@dataclass(frozen=True)
class Temp:
    """Temporal (t0, t1, ...). El índice es reasignado por TempAllocator."""
    index: int

    def __str__(self) -> str:
        return f"t{self.index}"


@dataclass(frozen=True)
class VarRef:
    """Referencia a una variable/parámetro/campo. La dirección sale de `symbol`."""
    symbol: "object"  # compiscript.semantic.symbol_table.Symbol — evita import circular

    def __str__(self) -> str:
        return self.symbol.name

    def with_addresses(self) -> str:
        return self.symbol.address() if self.symbol.storage else self.symbol.name


@dataclass(frozen=True)
class Const:
    """Constante entera/booleana/float. Booleanos son 1/0; null es 0."""
    value: Union[int, float]

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class StrConst:
    """Dirección de un string en la sección de datos (ver ir.program.TACProgram)."""
    label: str

    def __str__(self) -> str:
        return self.label


@dataclass(frozen=True)
class Label:
    """Etiqueta de control de flujo o de función."""
    name: str

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True)
class FramePointer:
    """Marcador especial: 'pasar mi propio fp actual' (usado como argumento de `param` al
    invocar una función anidada directamente desde su padre léxico inmediato, ver ticket A-5
    y docs/TAC_LANGUAGE.md §6, supuestos)."""

    def __str__(self) -> str:
        return "fp"


FP = FramePointer()

Operand = Union[Temp, VarRef, Const, StrConst, Label, FramePointer, None]


def is_temp(op: Operand) -> bool:
    return isinstance(op, Temp)
