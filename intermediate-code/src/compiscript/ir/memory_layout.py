"""Layout de objetos en memoria (offsets de atributos y vtables) y header de arreglos."""
from __future__ import annotations

from typing import Dict

from ..semantic.symbol_table import WORD_SIZE
from ..semantic.types import ClassType

__all__ = ["WORD_SIZE", "ARRAY_HEADER_SIZE", "compute_class_layouts"]

# los arreglos guardan su longitud en la primera palabra
ARRAY_HEADER_SIZE = WORD_SIZE


def compute_class_layouts(class_registry: Dict[str, ClassType]) -> None:
    """Calcula offsets de atributos y vtable de cada clase. El padre se procesa primero para
    que lo heredado conserve su offset. Slot 0 = puntero a vtable."""
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
