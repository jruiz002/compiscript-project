"""Cálculo de layouts de clase/vtable (ticket A-4) y constantes de layout de arreglos usadas
por ir.tac_generator (ticket B-7). Los offsets de variables/parámetros (locales, globales,
registros de activación) se asignan en semantic/semantic_analyzer.py a medida que se declaran
(ver ActivationRecord y GlobalAllocator en semantic/symbol_table.py); este módulo se limita a
lo que solo puede resolverse una vez que TODAS las clases están registradas (herencia) y a
fórmulas de acceso a memoria que pertenecen al nivel de IR, no de tabla de símbolos.

Diseño: docs/TAC_LANGUAGE.md §3 (frame), §4 (clases), §2 (convención de acceso a arreglos).
"""
from __future__ import annotations

from typing import Dict

from ..semantic.symbol_table import WORD_SIZE
from ..semantic.types import ClassType

__all__ = ["WORD_SIZE", "ARRAY_HEADER_SIZE", "compute_class_layouts"]

#: Los arreglos guardan su longitud en un word al inicio; los elementos empiezan después.
ARRAY_HEADER_SIZE = WORD_SIZE


def compute_class_layouts(class_registry: Dict[str, ClassType]) -> None:
    """Calcula field_offsets, instance_size, vtable y method_slots de cada ClassType,
    procesando superclases antes que subclases (para que los atributos y slots heredados
    conserven su offset/índice, ver CLAUDE.md §5.4).

    Layout de instancia: slot 0 = puntero a vtable, luego los atributos (heredados primero,
    en su offset original; luego los propios, en orden de declaración).
    """
    processed: set[str] = set()

    def process(ct: ClassType) -> None:
        if ct.name in processed:
            return
        if ct.superclass is not None:
            process(ct.superclass)
            field_offsets = dict(ct.superclass.field_offsets)
            vtable = list(ct.superclass.vtable)
            method_slots = dict(ct.superclass.method_slots)
            next_offset = ct.superclass.instance_size
        else:
            field_offsets = {}
            vtable = []
            method_slots = {}
            next_offset = WORD_SIZE  # slot 0: puntero a vtable

        for attr_name in ct.attributes:
            if attr_name in field_offsets:
                continue  # heredado, conserva su offset
            field_offsets[attr_name] = next_offset
            next_offset += WORD_SIZE

        for method_name in ct.methods:
            label = f"{ct.name}_{method_name}"
            if method_name in method_slots:
                slot = method_slots[method_name]  # override: reusa el slot del ancestro
                vtable[slot] = label
            else:
                slot = len(vtable)
                vtable.append(label)
            method_slots[method_name] = slot

        ct.field_offsets = field_offsets
        ct.instance_size = next_offset
        ct.vtable = vtable
        ct.method_slots = method_slots
        processed.add(ct.name)

    for class_type in class_registry.values():
        process(class_type)
