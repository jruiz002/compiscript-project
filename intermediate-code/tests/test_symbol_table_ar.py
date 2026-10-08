"""Tests de node_types/scope_of/symbol_of y de los registros de activación."""
from conftest import compile_ok


def test_symbol_of_resolves_shadowed_identifiers():
    result = compile_ok(
        "let x: integer = 1;\n"
        "{\n"
        "  let x: integer = 2;\n"
        "  print(x);\n"
        "}\n"
        "print(x);\n"
    )
    analyzer = result.analyzer
    # cada 'x' debe resolver al símbolo de su scope
    outer = analyzer.symbols._global.lookup_local("x")
    inner_scope = analyzer.symbols._global.children[0]
    inner = inner_scope.lookup_local("x")
    assert outer is not inner
    assert outer.offset != inner.offset

    identifier_ctxs = [ctx for ctx in analyzer.symbol_of if type(ctx).__name__ == "IdentifierExprContext"]
    resolved = [analyzer.symbol_of[ctx] for ctx in identifier_ctxs]
    assert any(r is outer for r in resolved)
    assert any(r is inner for r in resolved)


def test_node_types_populated_for_expressions():
    result = compile_ok("let x: integer = 1 + 2;\nprint(x);\n")
    analyzer = result.analyzer
    assert len(analyzer.node_types) > 0
    types_seen = {str(t) for t in analyzer.node_types.values()}
    assert "integer" in types_seen


def test_scope_of_maps_function_declaration_to_its_scope():
    result = compile_ok("function f(): integer { return 1; }\nprint(f());\n")
    analyzer = result.analyzer
    func_ctx = next(ctx for ctx in analyzer.scope_of if type(ctx).__name__ == "FunctionDeclarationContext")
    scope = analyzer.scope_of[func_ctx]
    assert scope.scope_kind == "function"
    assert scope.activation_record is not None


def test_activation_record_this_is_first_param_in_methods():
    result = compile_ok(
        "class C {\n"
        "  let v: integer;\n"
        "  function get(): integer { return this.v; }\n"
        "}\n"
        "let c: C = new C();\n"
        "print(c.get());\n"
    )
    c_type = result.analyzer.class_registry["C"]
    method_ctx = None
    for ctx, sym in result.analyzer.symbol_of.items():
        if type(ctx).__name__ == "FunctionDeclarationContext" and sym.name == "get":
            method_ctx = ctx
    scope = result.analyzer.scope_of[method_ctx]
    ar = scope.activation_record
    assert ar.params[0].name == "this"
    assert ar.params[0].offset == 8


def test_symbol_table_dump_includes_addresses():
    result = compile_ok("let x: integer = 1;\nfunction f(): integer { return x; }\nprint(f());\n")
    dump = result.symbol_table.dump()
    assert "gp[0]" in dump
    assert "ActivationRecord" in dump
