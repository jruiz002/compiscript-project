"""Tests de if/while/do-while/for/foreach/switch/break/continue (tickets C-1, C-2)."""
from conftest import run_source


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
