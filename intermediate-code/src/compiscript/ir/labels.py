"""Generación de etiquetas únicas del TAC.

Convención (docs/TAC_LANGUAGE.md §2):
  - L<n>                          control de flujo
  - f_<nombre>                    funciones de nivel superior
  - <Clase>_<metodo>               métodos (incluye constructor)
  - f_<externa>__<interna>        funciones anidadas
  - str_<n>                       strings en la sección de datos

Las etiquetas de funciones/métodos/anidadas ya se calculan en el semántico
(Symbol.label, ver semantic/semantic_analyzer.py ticket A-1/A-3) siguiendo esta misma
convención; este módulo solo genera las etiquetas de control de flujo (L<n>), que no tienen
una identidad léxica fija y se piden bajo demanda durante la generación de TAC. Ticket B-2.
"""
from __future__ import annotations


class LabelGenerator:
    """Un generador por programa: garantiza que dos L<n> nunca colisionen."""

    def __init__(self):
        self._counter = 0

    def new_label(self) -> str:
        name = f"L{self._counter}"
        self._counter += 1
        return name
