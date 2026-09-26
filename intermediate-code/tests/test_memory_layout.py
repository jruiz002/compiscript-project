"""Tests de offsets, frame_size y layout de clases (tickets A-2, A-4)."""
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
    # 2 locales (x, y) = 8 bytes; sin static link; y la optimizacion de destino (regla 4,
    # docs/TAC_LANGUAGE.md §5) hace que ni siquiera haga falta un temporal aqui.
    assert ar.temp_count == 0
    assert ar.frame_size == 8


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

    # 'nombre' se hereda y CONSERVA su offset; 'raza' se agrega despues
    assert perro.field_offsets["nombre"] == 4
    assert perro.field_offsets["raza"] == 8
    assert perro.instance_size == 12

    # 'hablar' esta sobrescrito: mismo slot que en Animal
    assert animal.method_slot("hablar") == perro.method_slot("hablar")
    assert perro.vtable[perro.method_slot("hablar")] == "Perro_hablar"
    # el constructor no se sobrescribe: Perro hereda el de Animal en el mismo slot
    assert perro.vtable[perro.method_slot("constructor")] == "Animal_constructor"
