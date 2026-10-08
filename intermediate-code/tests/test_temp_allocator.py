"""Tests de TempAllocator."""
from compiscript.ir.operands import Temp
from compiscript.ir.temp_allocator import TempAllocator, TempAllocatorError

import pytest


def test_new_temp_assigns_increasing_indices():
    alloc = TempAllocator()
    assert alloc.new_temp() == Temp(0)
    assert alloc.new_temp() == Temp(1)
    assert alloc.new_temp() == Temp(2)


def test_release_then_new_temp_reuses_smallest_free_index():
    alloc = TempAllocator()
    t0 = alloc.new_temp()
    t1 = alloc.new_temp()
    t2 = alloc.new_temp()
    alloc.release(t1)
    alloc.release(t0)
    # debe reusar el índice libre más pequeño, no el último liberado
    assert alloc.new_temp() == Temp(0)
    assert alloc.new_temp() == Temp(1)
    assert alloc.new_temp() == Temp(3)


def test_release_ignores_non_temp_operands():
    alloc = TempAllocator()
    from compiscript.ir.operands import Const, VarRef

    alloc.release(Const(5))
    alloc.release(None)
    assert alloc.live == 0


def test_max_used_tracks_peak_live_temporaries():
    alloc = TempAllocator()
    a = alloc.new_temp()
    b = alloc.new_temp()
    alloc.release(a)
    alloc.release(b)
    c = alloc.new_temp()
    alloc.release(c)
    assert alloc.max_used == 2  # máximo 2 vivos a la vez


def test_double_release_raises():
    alloc = TempAllocator()
    t = alloc.new_temp()
    alloc.release(t)
    with pytest.raises(TempAllocatorError):
        alloc.release(t)


def test_reset_clears_state():
    alloc = TempAllocator()
    alloc.new_temp()
    alloc.new_temp()
    alloc.reset()
    assert alloc.live == 0
    assert alloc.max_used == 0
    assert alloc.new_temp() == Temp(0)


def test_destination_can_reuse_freed_operand_index():
    """x = (a + b) * (c - d) + e se resuelve con 2 temporales."""
    from conftest import compile_ok

    result = compile_ok(
        "let a: integer = 1; let b: integer = 2; let c: integer = 3; "
        "let d: integer = 4; let e: integer = 5; let x: integer = 0; "
        "x = (a + b) * (c - d) + e;"
    )
    tac = result.tac_text
    assert "t2" not in tac  # no hizo falta un tercer temporal
    assert "t0 = a + b" in tac
    assert "t1 = c - d" in tac
    assert "t0 = t0 * t1" in tac
    assert "x = t0 + e" in tac
