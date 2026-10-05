# ARCHITECTURE — Fase 2

## Pipeline

```
fuente .cps
  -> CompiscriptLexer/Parser (ANTLR, src/compiscript/generated/)   errores sintácticos -> abortar
  -> SemanticAnalyzer (src/compiscript/semantic/)                  errores semánticos  -> abortar
       + tablas laterales (node_types, scope_of, symbol_of)
       + offsets/ActivationRecord asignados en línea, a medida que se declara cada símbolo
  -> ir.memory_layout.compute_class_layouts(analyzer.class_registry)
       (offsets de atributos + vtables; necesita TODAS las clases ya registradas)
  -> ir.tac_generator.TACGenerator(analyzer).generate(tree)  -> TACProgram
  -> ir.printer.print_program(program)                        -> texto .tac (dos modos)
  -> ir.interpreter.Interpreter(program, class_registry)       -> ejecución (CLI/tests/IDE)
```

`pipeline.compile(source: str) -> CompileResult` es el único punto de entrada; lo usan el CLI
(`main.py`), el IDE (`ide/app.py`) y los tests (`tests/conftest.py`). Ninguno de los tres
reimplementa estas etapas por su cuenta. `CompileResult` expone además
`tac_text_addresses` (el mismo TAC con `fp[off]`/`gp[off]`) y `analyzer` (para que el IDE y los
tests puedan inspeccionar `class_registry`, `node_types`, etc. sin recompilar).

## Módulos y responsabilidades

| Módulo | Responsabilidad |
|---|---|
| `semantic/semantic_analyzer.py` | Visitor de la Fase 1 (tipos, ámbitos) + tablas laterales (`node_types`/`scope_of`/`symbol_of`, llenadas interceptando `visit()`) + asignación de offsets/`ActivationRecord` en línea, mientras se declara cada símbolo |
| `semantic/symbol_table.py` | `Symbol` (offset/size/storage/label/`address()`), `Scope`, `ActivationRecord` (con `save_cursor`/`restore_cursor` para que bloques hermanos reusen offsets), `GlobalAllocator`, `SymbolTable.dump()` |
| `semantic/types.py` | Sistema de tipos de la Fase 1 + `ClassType.field_offsets/instance_size/vtable/method_slots` (llenados por `ir.memory_layout`) |
| `ir/operands.py` | `Temp`, `VarRef`, `Const`, `StrConst`, `Label`, `FramePointer` (static link) |
| `ir/instructions.py` | `OpCode`, `Quad`, tablas de saltos relacionales/negados |
| `ir/program.py` | `TACProgram` (funciones + strings deduplicados), `TACFunction` |
| `ir/labels.py` | Generador de etiquetas de control de flujo (`L<n>`) únicas por programa |
| `ir/temp_allocator.py` | Asignación y reciclaje de temporales (min-heap de libres) |
| `ir/memory_layout.py` | `compute_class_layouts`: offsets de atributos + vtables con herencia; constante `ARRAY_HEADER_SIZE` |
| `ir/tac_generator.py` | Visitor que recorre el mismo árbol de ANTLR que ya visitó `SemanticAnalyzer` y emite `Quad`s, consultando `node_types`/`scope_of`/`symbol_of` en vez de re-analizar |
| `ir/printer.py` | `TACProgram` → texto `.tac`, modo simbólico y con direcciones |
| `ir/interpreter.py` | Ejecuta un `TACProgram` (modelo de memoria: frames = dict, arreglos/objetos = listas de Python indexadas por `offset // WORD_SIZE`); usado por los tests de ejecución y el botón "Ejecutar" del IDE |
| `ide/app.py` | IDE Streamlit sobre `pipeline.compile` + `Interpreter` |

## Integración con la Fase 1

La Fase 1 no decora el AST, así que el `SemanticAnalyzer` llena tablas laterales
(`node_types`, `scope_of`, `symbol_of`) indexadas por `ParserRuleContext`, sin tocar las clases
generadas por ANTLR:

- `node_types` se llena **automáticamente**: `SemanticAnalyzer.visit()` está sobrescrito para
  interceptar cada llamada y, si el resultado es un `CompiscriptType`, guardarlo — como todo
  `visitXxxExpr` ya retorna su tipo inferido, no hizo falta anotar cada método a mano. La única
  excepción son los `suffixOp` dentro de un `leftHandSide` (`a.b[i].c`), que se procesan con un
  helper (`_apply_suffix`) fuera de `visit()`; `visitLeftHandSide` guarda su tipo explícitamente.
- `scope_of` se llena en cada punto donde se llama `symbols.enter_scope(...)`, asociando el
  `Scope` recién creado con el nodo que lo originó (bloque, función, clase, ciclo, `try`/
  `catch`, cada `case`/`default` de un `switch`).
- `symbol_of` se llena al resolver un identificador (`visitIdentifierExpr`, `visitThisExpr`) y
  al declarar uno (variable, constante, parámetro, función, clase, variable de `foreach`,
  variable de `catch`) — así el generador nunca necesita volver a buscar por nombre (lo que
  rompería con *shadowing*).

El `TACGenerator` solo lee de estas tablas y de la `SymbolTable` (ya con offsets asignados);
nunca vuelve a validar semántica. Precondición: `pipeline.compile` solo genera TAC si
`ErrorCollector` no tiene errores (`analyzer.errors.errors_only()` vacío).

## Por qué el cálculo de offsets vive en el semántico, no en un pase aparte

El diseño inicial contemplaba un módulo `MemoryLayout` como pase independiente. En la implementación
real, asignar offsets de **locales/parámetros/globales** en línea, a medida que
`SemanticAnalyzer` visita cada declaración, resultó más simple y evita un segundo recorrido del
árbol: el orden de declaración ya es exactamente el orden en que hay que asignar offsets, y
`ActivationRecord.allocate_local/allocate_param` son las únicas operaciones necesarias. Lo que
sí requiere un pase aparte, después de que **todas** las clases estén registradas, es el layout
de instancias/vtables (`ir.memory_layout.compute_class_layouts`), porque una clase puede
heredar de otra declarada más abajo en el archivo y necesita conocer el layout completo de su
superclase antes de calcular el propio.
