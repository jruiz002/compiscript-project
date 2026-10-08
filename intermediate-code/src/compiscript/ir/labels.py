"""Etiquetas L<n> para los saltos (las de funciones se asignan en el semántico)."""
from __future__ import annotations


class LabelGenerator:
    """Uno por programa, para que no se repitan etiquetas."""

    def __init__(self):
        self._counter = 0

    def new_label(self) -> str:
        name = f"L{self._counter}"
        self._counter += 1
        return name
