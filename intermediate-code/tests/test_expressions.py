"""Tests de expresiones aritméticas/relacionales/lógicas, precedencia y reciclaje de
temporales (ticket B-4). Ver también test_temp_allocator.py para el caso canónico de
docs/TAC_LANGUAGE.md §5."""
from conftest import compile_ok, run_source


def test_operator_precedence():
    assert run_source("print(5 + 3 * 2);\n") == "11\n"
    assert run_source("print((1 + 2) * 3);\n") == "9\n"


def test_left_associativity_of_subtraction():
    assert run_source("print(10 - 3 - 2);\n") == "5\n"


def test_relational_and_equality():
    assert run_source("print(3 < 5);\n") == "true\n"
    assert run_source("print(3 == 3);\n") == "true\n"
    assert run_source("print(3 != 3);\n") == "false\n"


def test_unary_not_and_neg():
    assert run_source("print(!(3 < 5));\n") == "false\n"
    assert run_source("print(-5 + 8);\n") == "3\n"


def test_ternary_materializes_value():
    assert run_source("let x: integer = 7; print(x > 5 ? 1 : 0);\n") == "1\n"
    assert run_source("let x: integer = 2; print(x > 5 ? 1 : 0);\n") == "0\n"


def test_short_circuit_or_does_not_evaluate_right_side():
    # si el '||' no cortocircuitara, dividir entre 0 fallaria al interpretar
    out = run_source(
        "function siempreTrue(): boolean { return true; }\n"
        "function division(): boolean { return (1 / 0) > 0; }\n"
        "print(siempreTrue() || division());\n"
    )
    assert out == "true\n"


def test_short_circuit_and_does_not_evaluate_right_side():
    out = run_source(
        "function siempreFalse(): boolean { return false; }\n"
        "function division(): boolean { return (1 / 0) > 0; }\n"
        "print(siempreFalse() && division());\n"
    )
    assert out == "false\n"


def test_booleans_print_and_concat_as_true_false():
    src = 'let c: boolean = true; print("v=" + c); print(!c);\n'
    assert run_source(src) == "v=true\nfalse\n"


def test_no_live_temps_after_statement_assertion_holds():
    # si el generador filtrara temporales, esto lanzaria AssertionError al compilar.
    result = compile_ok(
        "let a: integer = 1; let b: integer = 2; let c: integer = 3;\n"
        "print((a + b) * c - (a - b) / 1 + (a == b ? 1 : 0));\n"
    )
    assert result.ok


def test_destination_optimization_no_extra_temp_for_direct_assignment():
    result = compile_ok("let a: integer = 1; let b: integer = 2; let x: integer = a + b;\n")
    assert "x = a + b" in result.tac_text
    assert "t0" not in result.tac_text
