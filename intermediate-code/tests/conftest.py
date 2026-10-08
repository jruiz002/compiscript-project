"""Helpers compartidos de pytest."""
from __future__ import annotations

import pytest

from compiscript import pipeline
from compiscript.ir.interpreter import Interpreter


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--update-golden",
        action="store_true",
        default=False,
        help="Regenera los .tac esperados en tests/cases/success/ en vez de compararlos.",
    )


@pytest.fixture
def update_golden(request: pytest.FixtureRequest) -> bool:
    return request.config.getoption("--update-golden")


def compile_ok(source: str) -> pipeline.CompileResult:
    """Compila y falla el test si hubo errores."""
    result = pipeline.compile(source)
    assert result.ok, f"esperaba compilar sin errores, obtuve: {result.errors}"
    return result


def compile_fail(source: str) -> pipeline.CompileResult:
    """Compila y falla el test si no hubo errores."""
    result = pipeline.compile(source)
    assert not result.ok, "esperaba un error de compilacion, pero compiló sin errores"
    return result


def run_source(source: str) -> str:
    """Compila, ejecuta y devuelve lo que imprimió el programa."""
    result = compile_ok(source)
    interp = Interpreter(result.program, result.analyzer.class_registry)
    return interp.run()


def normalize_tac(text: str) -> str:
    """Quita espacios sobrantes para comparar contra los .tac esperados."""
    lines = [line.rstrip() for line in text.strip().splitlines()]
    return "\n".join(line for line in lines if line != "") + "\n"
