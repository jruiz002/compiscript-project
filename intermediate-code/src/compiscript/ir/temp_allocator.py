"""Asignación y reciclaje de temporales (requisito explícito de la rúbrica, ticket B-3).

Diseño y reglas de uso: docs/TAC_LANGUAGE.md §5.
  - new_temp() reusa el índice libre más pequeño (min-heap de libres) o crea uno nuevo.
  - release(op) libera `op` si es un Temp; no hace nada con VarRef/Const/StrConst/Label/None.
  - max_used registra el pico de temporales vivos simultáneamente -> alimenta frame_size.
  - reset() se llama una vez por función (un TempAllocator se reutiliza entre funciones).
"""
from __future__ import annotations

import heapq
from typing import Set

from .operands import Operand, Temp


class TempAllocatorError(RuntimeError):
    """Uso incorrecto del allocator: liberar un temporal que no está vivo (doble-release,
    o release de un Temp obsoleto cuyo índice ya fue reciclado)."""


class TempAllocator:
    def __init__(self) -> None:
        self._free: list[int] = []
        self._next_index = 0
        self._live: Set[int] = set()
        self.max_used = 0

    def new_temp(self) -> Temp:
        if self._free:
            index = heapq.heappop(self._free)
        else:
            index = self._next_index
            self._next_index += 1
        self._live.add(index)
        self.max_used = max(self.max_used, len(self._live))
        return Temp(index)

    def release(self, operand: Operand) -> None:
        if not isinstance(operand, Temp):
            return
        if operand.index not in self._live:
            raise TempAllocatorError(
                f"Doble liberación (o liberación de un temporal obsoleto): t{operand.index}"
            )
        self._live.discard(operand.index)
        heapq.heappush(self._free, operand.index)

    @property
    def live(self) -> int:
        return len(self._live)

    def reset(self) -> None:
        self._free.clear()
        self._next_index = 0
        self._live.clear()
        self.max_used = 0
