"""Los programas de tests/cases/failure/ no deben compilar."""
from __future__ import annotations

from pathlib import Path

import pytest

from compiscript import pipeline

CASES_DIR = Path(__file__).parent / "cases" / "failure"
CPS_FILES = sorted(CASES_DIR.glob("*.cps"))


@pytest.mark.parametrize("cps_path", CPS_FILES, ids=lambda p: p.stem)
def test_failure_case_reports_ok_false(cps_path: Path):
    source = cps_path.read_text(encoding="utf-8")
    result = pipeline.compile(source)
    assert result.ok is False, f"{cps_path.name} debia fallar mas no lo hizo"
    assert result.tac_text is None
    assert len(result.errors) >= 1
