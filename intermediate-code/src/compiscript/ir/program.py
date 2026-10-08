"""Programa TAC: lista de funciones y sección de datos con los strings."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from .instructions import Quad


@dataclass
class TACFunction:
    """Función o método traducido a TAC."""
    name: str
    frame_size: int = 0
    has_static_link: bool = False
    quads: List[Quad] = field(default_factory=list)

    def emit(self, quad: Quad) -> Quad:
        self.quads.append(quad)
        return quad


@dataclass
class TACProgram:
    functions: List[TACFunction] = field(default_factory=list)
    strings: Dict[str, str] = field(default_factory=dict)  # label -> valor
    _string_by_value: Dict[str, str] = field(default_factory=dict, repr=False, compare=False)

    def add_function(self, func: TACFunction) -> TACFunction:
        self.functions.append(func)
        return func

    def intern_string(self, value: str) -> str:
        """Devuelve la etiqueta del string (si ya existe, reusa la misma)."""
        existing = self._string_by_value.get(value)
        if existing is not None:
            return existing
        label = f"str_{len(self.strings)}"
        self.strings[label] = value
        self._string_by_value[value] = label
        return label

    def function_by_name(self, name: str) -> TACFunction | None:
        for f in self.functions:
            if f.name == name:
                return f
        return None
