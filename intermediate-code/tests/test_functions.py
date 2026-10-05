"""Tests de funciones, llamadas, retorno, recursión y funciones anidadas (tickets B-6, A-5)."""
from conftest import compile_ok, run_source


def test_factorial_matches_claude_md_example():
    src = (
        "function factorial(n: integer): integer {\n"
        "  if (n <= 1) { return 1; }\n"
        "  return n * factorial(n - 1);\n"
        "}\n"
        "print(factorial(5));\n"
    )
    assert run_source(src) == "120\n"


def test_deep_recursion():
    src = (
        "function suma(n: integer): integer {\n"
        "  if (n <= 0) { return 0; }\n"
        "  return n + suma(n - 1);\n"
        "}\n"
        "print(suma(100));\n"
    )
    assert run_source(src) == "5050\n"


def test_multiple_parameters_and_return():
    src = "function suma(a: integer, b: integer): integer { return a + b; }\nprint(suma(3, 4));\n"
    assert run_source(src) == "7\n"


def test_void_function_call_as_statement():
    src = 'function saluda(): void { print("hola"); }\nsaluda();\n'
    assert run_source(src) == "hola\n"


def test_nested_function_reads_outer_variable_via_static_link():
    src = (
        "function crearContador(): integer {\n"
        "  let base: integer = 10;\n"
        "  function siguiente(): integer { return base + 1; }\n"
        "  return siguiente();\n"
        "}\n"
        "print(crearContador());\n"
    )
    assert run_source(src) == "11\n"


def test_nested_function_generates_expected_label_and_static_link_param():
    result = compile_ok(
        "function crearContador(): integer {\n"
        "  let base: integer = 10;\n"
        "  function siguiente(): integer { return base + 1; }\n"
        "  return siguiente();\n"
        "}\n"
        "print(crearContador());\n"
    )
    assert "func f_crearContador__siguiente" in result.tac_text
    assert "param fp" in result.tac_text
    assert "up 1," in result.tac_text


def test_nested_function_calls_sibling():
    src = (
        "function outer(): integer {\n"
        "  let k: integer = 7;\n"
        "  function a(): integer { return k; }\n"
        "  function b(): integer { return a() + 1; }\n"
        "  return b();\n"
        "}\n"
        "print(outer());\n"
    )
    assert run_source(src) == "8\n"


def test_nested_function_recursion_keeps_static_link():
    src = (
        "function outer(): integer {\n"
        "  let k: integer = 3;\n"
        "  function r(n: integer): integer {\n"
        "    if (n <= 0) { return k; }\n"
        "    return r(n - 1) + 1;\n"
        "  }\n"
        "  return r(2);\n"
        "}\n"
        "print(outer());\n"
    )
    assert run_source(src) == "5\n"
