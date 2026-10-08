"""Tests de if/while/do-while/for/foreach/switch/break/continue (tickets C-1, C-2)."""
from conftest import compile_ok, run_source


def test_if_else():
    assert run_source("if (3 > 1) { print(\"si\"); } else { print(\"no\"); }\n") == "si\n"
    assert run_source("if (1 > 3) { print(\"si\"); } else { print(\"no\"); }\n") == "no\n"


def test_while_loop():
    src = "let x: integer = 0;\nwhile (x < 3) { print(x); x = x + 1; }\n"
    assert run_source(src) == "0\n1\n2\n"


def test_do_while_runs_at_least_once():
    src = "let x: integer = 10;\ndo { print(x); x = x + 1; } while (x < 3);\n"
    assert run_source(src) == "10\n"


def test_for_loop():
    src = "for (let i: integer = 0; i < 3; i = i + 1) { print(i); }\n"
    assert run_source(src) == "0\n1\n2\n"


def test_nested_break_continue():
    src = (
        "for (let i: integer = 0; i < 3; i = i + 1) {\n"
        "  for (let j: integer = 0; j < 3; j = j + 1) {\n"
        "    if (j == 1) { continue; }\n"
        "    if (j == 2) { break; }\n"
        "    print(i * 10 + j);\n"
        "  }\n"
        "}\n"
    )
    # para cada i: j=0 imprime i*10; j=1 continue; j=2 break -> solo un print por i
    assert run_source(src) == "0\n10\n20\n"


def test_break_inside_switch_does_not_break_enclosing_loop():
    src = (
        "for (let i: integer = 0; i < 2; i = i + 1) {\n"
        "  switch (i) {\n"
        "    case 0: print(\"cero\"); break;\n"
        "    default: print(\"otro\");\n"
        "  }\n"
        "}\n"
        "print(\"fin\");\n"
    )
    assert run_source(src) == "cero\notro\nfin\n"


def test_switch_fallthrough_and_default():
    src = "switch (2) { case 1: print(\"uno\"); case 2: print(\"dos\"); default: print(\"otro\"); }\n"
    assert run_source(src) == "dos\notro\n"


def test_switch_with_break_stops_fallthrough():
    src = "switch (1) { case 1: print(\"uno\"); break; case 2: print(\"dos\"); }\n"
    assert run_source(src) == "uno\n"


def test_foreach_over_array():
    src = "let a: integer[] = [1, 2, 3];\nforeach (n in a) { print(n); }\n"
    assert run_source(src) == "1\n2\n3\n"


def test_or_condition_in_if_jumps_to_body_when_first_operand_is_true():
    # regresion: con l_true=None (el `if` "cae" al cuerpo), un `||` cuyo primer operando era
    # verdadero seguia evaluando el ultimo operando y tomaba la rama falsa
    src = (
        "let a: integer = 5;\n"
        "if (a > 1 || a > 100) { print(\"si\"); } else { print(\"no\"); }\n"
        "if (a > 100 || a > 1) { print(\"si\"); } else { print(\"no\"); }\n"
        "if (a > 100 || a < 1) { print(\"si\"); } else { print(\"no\"); }\n"
    )
    assert run_source(src) == "si\nsi\nno\n"


def test_or_condition_in_while_and_for():
    src = (
        "let i: integer = 0;\n"
        "while (i == 0 || i == 5) { print(i); i = i + 1; }\n"
        "for (let j: integer = 0; j < 1 || j == 9; j = j + 1) { print(j); }\n"
    )
    assert run_source(src) == "0\n0\n"


def test_and_condition_in_do_while_stops_when_first_operand_is_false():
    # regresion simetrica: la condicion de un do-while "cae" en el caso falso (l_false=None)
    src = (
        "let i: integer = 0;\n"
        "do { i = i + 1; } while (i > 100 && i < 200);\n"
        "print(i);\n"
    )
    assert run_source(src) == "1\n"


def test_relational_condition_uses_direct_jump_without_temporaries():
    result = compile_ok(
        "let a: integer = 1; let b: integer = 2;\n"
        "if (a < b && !(a == b)) { print(a); }\n"
    )
    assert "if a >= b goto" in result.tac_text
    assert "if a == b goto" in result.tac_text
    assert "t0" not in result.tac_text


def test_foreach_inside_function_block_does_not_clobber_locals():
    # regresion: las variables ocultas del foreach (__arr/__idx/__len) se reservaban al
    # generar TAC y reusaban los offsets de `x`/`y`, dando 10 en vez de 60
    src = (
        "function total(a: integer[]): integer {\n"
        "  let s: integer = 0;\n"
        "  if (true) {\n"
        "    foreach (x in a) { let y: integer = x * 10; s = s + y; }\n"
        "  }\n"
        "  return s;\n"
        "}\n"
        "print(total([1, 2, 3]));\n"
    )
    assert run_source(src) == "60\n"


def test_nested_foreach_inside_function():
    src = (
        "function pares(a: integer[], b: integer[]): integer {\n"
        "  let n: integer = 0;\n"
        "  foreach (x in a) { foreach (y in b) { if (x == y) { n = n + 1; } } }\n"
        "  return n;\n"
        "}\n"
        "print(pares([1, 2, 3], [2, 3, 4]));\n"
    )
    assert run_source(src) == "2\n"
