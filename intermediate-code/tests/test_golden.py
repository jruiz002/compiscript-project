"""Compara el TAC y la salida de cada programa de tests/cases/success/ con sus .tac/.out.

Para regenerarlos: pytest --update-golden
"""
from __future__ import annotations

from pathlib import Path

import pytest

from compiscript import pipeline
from compiscript.ir.interpreter import Interpreter
from conftest import normalize_tac

CASES_DIR = Path(__file__).parent / "cases" / "success"
CPS_FILES = sorted(CASES_DIR.glob("*.cps"))


@pytest.mark.parametrize("cps_path", CPS_FILES, ids=lambda p: p.stem)
def test_golden_case(cps_path: Path, update_golden: bool):
    source = cps_path.read_text(encoding="utf-8")
    result = pipeline.compile(source)
    assert result.ok, f"{cps_path.name}: {result.errors}"

    tac_path = cps_path.with_suffix(".tac")
    out_path = cps_path.with_suffix(".out")

    interp = Interpreter(result.program, result.analyzer.class_registry)
    actual_out = interp.run()

    if update_golden:
        tac_path.write_text(result.tac_text, encoding="utf-8")
        out_path.write_text(actual_out, encoding="utf-8")
        return

    assert tac_path.exists(), f"falta {tac_path.name}; correr con --update-golden"
    expected_tac = tac_path.read_text(encoding="utf-8")
    assert normalize_tac(result.tac_text) == normalize_tac(expected_tac)

    if out_path.exists():
        expected_out = out_path.read_text(encoding="utf-8")
        assert actual_out == expected_out
