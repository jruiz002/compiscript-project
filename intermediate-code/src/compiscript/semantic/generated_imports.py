"""Punto único de import de los artefactos generados por ANTLR (ticket A-0).

Aísla al resto del paquete `semantic` de la ubicación exacta de `generated/`, para que si se
regenera con otra estructura de salida solo haya que tocar este archivo.
"""
from __future__ import annotations

from ..generated.CompiscriptParser import CompiscriptParser
from ..generated.CompiscriptVisitor import CompiscriptVisitor

__all__ = ["CompiscriptParser", "CompiscriptVisitor"]
