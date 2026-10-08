"""Tests de clases, herencia, this, new y despacho virtual."""
from conftest import compile_ok, run_source


def test_constructor_sets_fields_via_this():
    src = (
        "class Punto {\n"
        "  let x: integer;\n"
        "  let y: integer;\n"
        "  function constructor(x: integer, y: integer) { this.x = x; this.y = y; }\n"
        "  function suma(): integer { return this.x + this.y; }\n"
        "}\n"
        "let p: Punto = new Punto(3, 4);\n"
        "print(p.suma());\n"
    )
    assert run_source(src) == "7\n"


def test_inherited_method_not_overridden():
    src = (
        "class Animal {\n"
        "  let nombre: string;\n"
        "  function constructor(nombre: string) { this.nombre = nombre; }\n"
        "  function hablar(): string { return this.nombre + \" hace ruido.\"; }\n"
        "}\n"
        "class Pez : Animal {}\n"
        "let p: Pez = new Pez(\"Nemo\");\n"
        "print(p.hablar());\n"
    )
    assert run_source(src) == "Nemo hace ruido.\n"


def test_overridden_method_dispatches_dynamically_through_supertype_reference():
    src = (
        "class Animal {\n"
        "  let nombre: string;\n"
        "  function constructor(nombre: string) { this.nombre = nombre; }\n"
        "  function hablar(): string { return this.nombre + \" hace ruido.\"; }\n"
        "}\n"
        "class Perro : Animal {\n"
        "  function hablar(): string { return this.nombre + \" ladra.\"; }\n"
        "}\n"
        "let a: Animal = new Perro(\"Toby\");\n"
        "print(a.hablar());\n"
    )
    assert run_source(src) == "Toby ladra.\n"


def test_inherited_fields_keep_offset_across_subclass():
    result = compile_ok(
        "class A { let x: integer; function constructor(x: integer) { this.x = x; } }\n"
        "class B : A { let y: integer; function constructor(x: integer, y: integer) {\n"
        "  this.x = x; this.y = y;\n"
        "} }\n"
        "let b: B = new B(1, 2);\n"
        "print(b.x);\n"
    )
    a = result.analyzer.class_registry["A"]
    b = result.analyzer.class_registry["B"]
    assert a.field_offsets["x"] == b.field_offsets["x"]


def test_two_instances_have_independent_state():
    src = (
        "class Contador {\n"
        "  let n: integer;\n"
        "  function constructor() { this.n = 0; }\n"
        "  function inc(): integer { this.n = this.n + 1; return this.n; }\n"
        "}\n"
        "let a: Contador = new Contador();\n"
        "let b: Contador = new Contador();\n"
        "print(a.inc());\n"
        "print(a.inc());\n"
        "print(b.inc());\n"
    )
    assert run_source(src) == "1\n2\n1\n"


def test_field_initializers_run_before_constructor_base_first():
    src = (
        "class A { let a: integer = 1; const K: integer = 2; }\n"
        "class B : A {\n"
        "  let b: integer = 10;\n"
        "  function constructor() { this.a = this.a + 100; }\n"
        "  function suma(): integer { return this.a + this.b + this.K; }\n"
        "}\n"
        "print(new B().suma());\n"
    )
    assert run_source(src) == "113\n"
