"""Tests de arreglos 1D/2D, literales, indexación y boundscheck (ticket B-7)."""
from conftest import compile_ok, run_source


def test_array_literal_and_index_read():
    assert run_source("let a: integer[] = [10, 20, 30];\nprint(a[1]);\n") == "20\n"


def test_array_index_write():
    src = "let a: integer[] = [1, 2, 3];\na[0] = 99;\nprint(a[0]);\n"
    assert run_source(src) == "99\n"


def test_2d_array_as_array_of_arrays():
    src = "let m: integer[][] = [[1, 2], [3, 4]];\nprint(m[1][0]);\n"
    assert run_source(src) == "3\n"


def test_array_index_offset_skips_length_header():
    result = compile_ok("let a: integer[] = [7, 8, 9];\nprint(a[0]);\n")
    # el offset del primer elemento debe saltar los 4 bytes del header de longitud
    assert "boundscheck" in result.tac_text
    assert "+ 4" in result.tac_text


def test_out_of_bounds_raises_runtime_error_caught_by_try_catch():
    src = (
        "try {\n"
        "  let a: integer[] = [1, 2, 3];\n"
        "  print(a[10]);\n"
        "} catch (err) {\n"
        "  print(\"capturado\");\n"
        "}\n"
    )
    assert run_source(src) == "capturado\n"


def test_len_builtin_via_foreach_visits_every_element():
    src = "let a: integer[] = [1, 2, 3, 4];\nlet total: integer = 0;\n" \
          "foreach (n in a) { total = total + n; }\nprint(total);\n"
    assert run_source(src) == "10\n"


def test_reassigning_array_literal_that_reads_the_same_variable():
    # regresion: la optimizacion de destino creaba el arreglo nuevo directo en `a` antes de
    # leer `a[2]`/`a[0]` (que entonces leian el arreglo nuevo -> indice fuera de rango)
    src = (
        "let a: integer[] = [3, 1, 2];\n"
        "a = [a[2], a[0]];\n"
        "print(a[0]); print(a[1]);\n"
    )
    assert run_source(src) == "2\n3\n"
