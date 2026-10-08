"""Tests de offsets, frame_size y layout de clases."""
from conftest import compile_ok


def test_frame_size_formula_locals_and_temps():
    result = compile_ok(
        "function f(a: integer, b: integer): integer {\n"
        "  let x: integer = a + b;\n"
        "  let y: integer = x * 2;\n"
        "  return y;\n"
        "}\n"
        "print(f(1, 2));\n"
    )
    func_scope = result.analyzer.symbols._global.children[0]
    ar = func_scope.activation_record
    assert ar.function_name == "f_f"
    # 4 (fp-4) + 2 locales = 12, sin temporales
    assert ar.temp_count == 0
    assert ar.frame_size == 12
    # el frame debe cubrir al local mas profundo
    assert min(s.offset for s in ar.locals) >= -ar.frame_size


def test_sibling_blocks_reuse_offsets():
    result = compile_ok(
        "function f(): integer {\n"
        "  if (true) { let a: integer = 1; }\n"
        "  else { let b: integer = 2; }\n"
        "  return 0;\n"
        "}\n"
        "print(f());\n"
    )
    func_scope = result.analyzer.symbols._global.children[0]
    ar = func_scope.activation_record
    # a y b son de bloques hermanos (then/else): deben compartir el mismo offset
    then_scope, else_scope = func_scope.children
    a_sym = then_scope.lookup_local("a")
    b_sym = else_scope.lookup_local("b")
    assert a_sym.offset == b_sym.offset == -8


def test_global_variable_gets_gp_address():
    result = compile_ok("let x: integer = 42;\nprint(x);\n")
    sym = result.analyzer.symbols._global.lookup_local("x")
    assert sym.storage == "global"
    assert sym.address() == "gp[0]"


def test_class_layout_inheritance_offsets_and_vtable():
    result = compile_ok(
        "class Animal {\n"
        "  let nombre: string;\n"
        "  function constructor(nombre: string) { this.nombre = nombre; }\n"
        "  function hablar(): string { return this.nombre; }\n"
        "}\n"
        "class Perro : Animal {\n"
        "  let raza: string;\n"
        "  function hablar(): string { return this.nombre; }\n"
        "}\n"
        "let a: Animal = new Perro(\"Toby\");\n"
        "print(a.hablar());\n"
    )
    animal = result.analyzer.class_registry["Animal"]
    perro = result.analyzer.class_registry["Perro"]

    assert animal.field_offsets["nombre"] == 4
    assert animal.instance_size == 8

    # 'nombre' se hereda con el mismo offset, 'raza' va después
    assert perro.field_offsets["nombre"] == 4
    assert perro.field_offsets["raza"] == 8
    assert perro.instance_size == 12

    # 'hablar' sobrescrito usa el mismo slot
    assert animal.method_slot("hablar") == perro.method_slot("hablar")
    assert perro.vtable[perro.method_slot("hablar")] == "Perro_hablar"
    # Perro hereda el constructor de Animal
    assert perro.vtable[perro.method_slot("constructor")] == "Animal_constructor"


def test_foreach_hidden_locals_get_their_own_offsets():
    result = compile_ok(
        "function f(a: integer[]): integer {\n"
        "  let s: integer = 0;\n"
        "  foreach (x in a) { s = s + x * 2; }\n"
        "  return s;\n"
        "}\n"
        "print(f([1]));\n"
    )
    ar = result.analyzer.symbols._global.children[0].activation_record
    offsets = [s.offset for s in ar.locals]
    # s, __arr, __idx, __len y x con offsets distintos
    assert len(offsets) == len(set(offsets)) == 5
    assert ar.frame_size == 4 + 4 * len(offsets) + 4 * ar.temp_count
