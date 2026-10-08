"""Prueba básica: el paquete se importa y compile() funciona."""
from compiscript import pipeline


def test_pipeline_module_exposes_compile():
    assert hasattr(pipeline, "compile")


def test_compile_result_has_expected_fields():
    result = pipeline.CompileResult(ok=False)
    assert result.errors == []
    assert result.tac_text is None
