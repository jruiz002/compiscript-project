"""Operandos del TAC: Temp, VarRef, Const, StrConst, Label y FP."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Union


@dataclass(frozen=True)
class Temp:
    """Temporal (t0, t1, ...)."""
    index: int

    def __str__(self) -> str:
        return f"t{self.index}"


@dataclass(frozen=True)
class VarRef:
    """Variable o parámetro; la dirección sale de su símbolo."""
    symbol: "object"  # Symbol (sin import para evitar import circular)

    def __str__(self) -> str:
        return self.symbol.name

    def with_addresses(self) -> str:
        return self.symbol.address() if self.symbol.storage else self.symbol.name


@dataclass(frozen=True)
class Const:
    """Constante. Los booleanos son 1/0 y null es 0."""
    value: Union[int, float]

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class StrConst:
    """String de la sección de datos (str_n)."""
    label: str

    def __str__(self) -> str:
        return self.label


@dataclass(frozen=True)
class Label:
    """Etiqueta de salto o de función."""
    name: str

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True)
class FramePointer:
    """El fp actual, se pasa como static link a una función anidada."""

    def __str__(self) -> str:
        return "fp"


FP = FramePointer()

Operand = Union[Temp, VarRef, Const, StrConst, Label, FramePointer, None]


def is_temp(op: Operand) -> bool:
    return isinstance(op, Temp)
