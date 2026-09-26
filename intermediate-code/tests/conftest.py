"""Configuración y helpers compartidos de pytest para la Fase 2 (ver ../../FEATURES.md)."""
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
    """Compila `source` y falla el test (con los errores) si no compiló limpio."""
    result = pipeline.compile(source)
    assert result.ok, f"esperaba compilar sin errores, obtuve: {result.errors}"
    return result


def compile_fail(source: str) -> pipeline.CompileResult:
    """Compila `source` y falla el test si SÍ compiló (se esperaba un error)."""
    result = pipeline.compile(source)
    assert not result.ok, "esperaba un error de compilacion, pero compiló sin errores"
    return result


def run_source(source: str) -> str:
    """Compila y ejecuta `source` con el intérprete; retorna la salida de `print`."""
    result = compile_ok(source)
    interp = Interpreter(result.program, result.analyzer.class_registry)
    return interp.run()


def normalize_tac(text: str) -> str:
    """Normaliza espacios para comparar contra los .tac esperados (ver --update-golden)."""
    lines = [line.rstrip() for line in text.strip().splitlines()]
    return "\n".join(line for line in lines if line != "") + "\n"
