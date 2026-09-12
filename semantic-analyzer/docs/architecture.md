# Arquitectura del Compilador Compiscript

## Visión General

El compilador de Compiscript implementa la **fase de análisis semántico** usando ANTLR4 para la generación del lexer/parser y un visitor Python personalizado para las reglas semánticas.

```
Código fuente (.cps)
       │
       ▼
  ┌─────────┐
  │  Lexer  │  CompiscriptLexer.py (generado por ANTLR4)
  └─────────┘
       │ Token stream
       ▼
  ┌─────────┐
  │ Parser  │  CompiscriptParser.py (generado por ANTLR4)
  └─────────┘
       │ Parse tree (CST)
       ▼
  ┌──────────────────┐
  │ SemanticAnalyzer │  compiler/semantic/semantic_analyzer.py
  │   (Visitor)      │
  └──────────────────┘
       │         │
       ▼         ▼
  ┌─────────┐  ┌──────────────┐
  │SymTable │  │ErrorCollector│
  └─────────┘  └──────────────┘
       │
       ▼
  ┌──────────────┐
  │ASTVisualizer │  compiler/ast_visualizer.py
  └──────────────┘
       │
       ▼ (SVG/PNG)
  ┌─────────────┐
  │  IDE / CLI  │
  └─────────────┘
```

---

## Componentes

### 1. Gramática (`compiler/Compiscript.g4`)

La gramática ANTLR4 define la sintaxis completa de Compiscript.
Se extiende con soporte para `float` como tipo base adicional.
Se compila con ANTLR4 para generar el lexer y parser en Python.

### 2. Sistema de Tipos (`compiler/semantic/types.py`)

Jerarquía de tipos:

| Clase | Descripción |
|-------|-------------|
| `PrimitiveType` | `integer`, `float`, `string`, `boolean`, `null`, `void`, `any` |
| `ArrayType` | Arreglo con tipo de elemento y dimensiones |
| `FunctionType` | Tipos de parámetros y tipo de retorno |
| `ClassType` | Nombre, superclase, atributos, métodos |

**Reglas de compatibilidad:**
- `integer` es asignable a `float` (coerción numérica)
- `any` es compatible con todo (tipo de inferencia)
- `error_type` suprime errores en cascada
- `string + string` produce `string`

### 3. Tabla de Símbolos (`compiler/semantic/symbol_table.py`)

#### `Symbol`
```python
@dataclass
class Symbol:
    name: str          # nombre del identificador
    kind: SymbolKind   # VARIABLE | CONSTANT | FUNCTION | PARAMETER | CLASS | LOOP_VAR
    data_type: ...     # tipo Compiscript
    line: int          # línea de declaración
    column: int        # columna de declaración
    scope_level: int   # nivel de anidamiento
    is_initialized: bool
    is_const: bool
```

#### `Scope`
- Diccionario `name → Symbol`
- Referencia al scope padre (cadena de entornos)
- Árbol de hijos para serialización

#### `SymbolTable`
- Pila de scopes activos
- Helpers de contexto: `is_inside_loop()`, `is_inside_function()`, `is_inside_class()`, `current_class_type()`
- Serializable a JSON para el IDE

### 4. Analizador Semántico (`compiler/semantic/semantic_analyzer.py`)

Implementa `CompiscryptVisitor` con métodos para cada regla de la gramática.

#### Reglas implementadas

| Categoría | Regla | Implementación |
|-----------|-------|----------------|
| Tipos | Aritméticas | `visitAdditiveExpr`, `visitMultiplicativeExpr` |
| Tipos | Lógicas | `visitLogicalOrExpr`, `visitLogicalAndExpr`, `visitUnaryExpr` |
| Tipos | Comparaciones | `visitEqualityExpr`, `visitRelationalExpr` |
| Tipos | Asignación | `visitVariableDeclaration`, `visitAssignExpr` |
| Tipos | Const inicialización | `visitConstantDeclaration` |
| Tipos | Arrays | `visitArrayLiteral`, `_apply_suffix` (IndexExpr) |
| Ámbito | Undeclared variable | `visitIdentifierExpr` |
| Ámbito | Redeclaración | `visitVariableDeclaration`, `visitFunctionDeclaration` |
| Ámbito | Nested scopes | `visitBlock` |
| Funciones | Arg count/type | `_apply_suffix` (CallExpr), `visitFunctionDeclaration` |
| Funciones | Return type | `visitReturnStatement` |
| Funciones | Recursión | definición previa al cuerpo |
| Funciones | Closures | scope chain lookup |
| Control | Condición booleana | `visitIfStatement`, `visitWhileStatement`, etc. |
| Control | break/continue | `visitBreakStatement`, `visitContinueStatement` |
| Control | return fuera de función | `visitReturnStatement` |
| Clases | Superclase existe | `visitClassDeclaration` |
| Clases | Acceso a miembros | `_apply_suffix` (PropertyAccessExpr) |
| Clases | Constructor | `visitNewExpr` |
| Clases | this en clase | `visitThisExpr` |
| Generales | Código muerto | `_visit_block_with_dead_code_check` |

#### Estrategia de dos pasadas para clases

Para soportar referencias hacia adelante (forward references), el analizador realiza:
1. **Pre-registro**: scan rápido de todas las declaraciones de clase en el nivel global para crear sus `ClassType` antes de procesar el cuerpo de ninguna función.
2. **Visita completa**: visita normal de todo el árbol con los tipos ya registrados.

### 5. Visualizador AST (`compiler/ast_visualizer.py`)

Usa la librería `graphviz` para:
- Recorrer el árbol de parseo ANTLR4
- Asignar colores por tipo de nodo (statement, expression, literal, terminal)
- Generar un archivo `.dot` y renderizarlo a SVG/PNG
- Retornar el SVG como string para embeber en el IDE

### 6. IDE Web (`ide/`)

**Backend (Flask):**
- `POST /compile` → recibe código fuente, retorna `{ errors, warnings, symbol_table, ast_svg }`
- Genera el AST SVG en un directorio temporal
- Acumula todos los errores (no para al primer error)

**Frontend:**
- Editor con numeración de líneas, soporte de Tab, atajos de teclado
- Panel de diagnósticos con línea/columna clicable
- Árbol de símbolos colapsable por scope
- Panel de AST con zoom
- Ejemplos precargados

---

## Flujo de Compilación

```
1. Crear InputStream con el código fuente
2. CompiscryptLexer tokeniza el stream
3. CompiscryptParser construye el árbol de parseo (CST)
4. SyntaxErrorCollector captura errores de sintaxis
   └─ Si hay errores de sintaxis → retornar, no ejecutar semántica
5. SemanticAnalyzer.visit(tree) recorre el CST:
   a. Pre-registro de clases (primera pasada rápida)
   b. visitProgram → visita todos los statements
   c. Cada visitor retorna el tipo inferido de la expresión
   d. Los errores se acumulan en ErrorCollector
   e. Los símbolos se registran en SymbolTable
6. Si se solicitó AST → ASTVisualizer.generate()
7. Retornar resultado JSON: { errors, warnings, symbol_table, ast_svg }
```

---

## Decisiones de Diseño

### Acumulación de errores vs. fail-fast
El analizador **no detiene** el análisis al primer error. Usa `ERROR_TYPE` como sentinela para evitar errores en cascada (e.g., si una variable no está declarada, su tipo es `ERROR_TYPE` y no se generan más errores sobre esa variable).

### Inferencia de tipos
Cuando una variable se declara sin anotación de tipo (`let x = 5;`), el tipo se infiere del inicializador. Esto permite código más conciso sin sacrificar la verificación de tipos.

### Compatibilidad numérica
`integer` es asignable a `float` (coerción implícita). Esto refleja la semántica de TypeScript/JavaScript donde los números son compatibles.

### String como tipo para `+`
El operador `+` funciona tanto para `integer + integer` (suma) como para `string + string` (concatenación). Para cualquier otra combinación se genera un error.

### `switch`: compatibilidad de tipos en lugar de `boolean` obligatorio
El enunciado lista `switch` junto con `if`/`while`/`do-while`/`for` como una construcción cuya condición "debe evaluar expresiones de tipo boolean". `visitSwitchStatement` (`compiler/semantic/semantic_analyzer.py`) implementa deliberadamente algo distinto: valida que el tipo de la expresión del `switch` sea **compatible** con el tipo de cada expresión `case`, sin exigir que sea `boolean`.

Exigir `boolean` en el switch anularía la utilidad de la construcción — un `switch` sobre un `integer`, `string` o `enum`-like es el caso de uso típico, y es exactamente lo que valida el chequeo de compatibilidad. `boolean` no es un caso especial ni una excepción: es simplemente uno más de los tipos que el chequeo genérico soporta. Se verificó empíricamente que un `switch` sobre una expresión `boolean` compila sin errores cuando los tipos de `switch` y `case` son consistentes:

```cps
let flag: boolean = true;
switch (flag) {
  case true: print("si");
  case false: print("no");
}
```
→ `✓ No errors found`. Si algún `case` tuviera un tipo incompatible con el `switch` (p. ej. `case 10:` sobre un `switch (flag)` boolean), el chequeo de compatibilidad existente ya lo reporta como error.

En resumen: no se restringe el tipo de la condición del `switch` a `boolean`, sino que se valida compatibilidad de tipos entre `switch` y cada `case` — y `boolean` es uno de los tipos que ese chequeo acepta correctamente, no uno que quede fuera.
