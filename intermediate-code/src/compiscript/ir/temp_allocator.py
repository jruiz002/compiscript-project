"""Asignación y reciclaje de temporales.

new_temp() da el temporal libre más pequeño (min-heap), release() lo devuelve y max_used
guarda el máximo usado a la vez, que se usa para el tamaño del frame.
"""
from __future__ import annotations

import heapq
from typing import Set

from .operands import Operand, Temp


class TempAllocatorError(RuntimeError):
    """Se liberó un temporal que no estaba en uso."""


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
