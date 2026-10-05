# TAC_LANGUAGE.md — Especificación del lenguaje intermedio

Implementado en `src/compiscript/ir/` (operandos, instrucciones, printer, temporales,
generador) y `src/compiscript/semantic/` (tabla de símbolos extendida). Todos los ejemplos de
este documento fueron generados con el compilador real (`pipeline.compile`), no son
aspiracionales.

## 1. Representación interna

Cuádruplos: `Quad(op: OpCode, arg1, arg2, result, comment: str | None)` (`ir/instructions.py`).

### Operandos (`ir/operands.py`)

| Clase | Ejemplo impreso | Significado |
|---|---|---|
| `Temp(n)` | `t3` | Temporal (vive en la zona de temporales del frame) |
| `VarRef(symbol)` | `x` o `fp[-12]` | Variable/parámetro/global; la dirección sale del `Symbol` |
| `Const(v)` | `5`, `1`, `0` | Entero o float; booleanos son `1`/`0`; `null` es `0` |
| `StrConst(label)` | `str_2` | Referencia a un string en la sección de datos |
| `Label(name)` | `L7`, `f_factorial` | Etiqueta |
| `FramePointer` (`FP`) | `fp` | Solo como argumento de `param`: "mi propio fp actual" (static link, ver §6) |

Todos son inmutables. El printer (`ir/printer.py`) tiene dos modos: **simbólico** (`x`) y
**con direcciones** (`fp[-12]`, `gp[4]`, `--addresses` en el CLI / toggle en el IDE).

## 2. Conjunto de instrucciones

| Categoría | Sintaxis impresa | OpCode |
|---|---|---|
| Copia | `x = y` | `ASSIGN` |
| Binaria | `x = y op z`, op ∈ `+ - * / %` | `ADD SUB MUL DIV MOD` |
| Relacional (valor) | `x = y op z`, op ∈ `== != < <= > >=` | `EQ NE LT LE GT GE` |
| Unaria | `x = -y`, `x = !y` | `NEG NOT` |
| Salto | `goto L` | `GOTO` |
| Salto condicional (valor) | `if x goto L` / `ifFalse x goto L` | `IF IFFALSE` |
| Salto relacional directo | `if x relop y goto L` | `IF_LT IF_LE IF_GT IF_GE IF_EQ IF_NE` |
| Etiqueta | `L:` | `LABEL` |
| Funciones | `func nombre, <frame_size>` / `endfunc nombre` | *(sintéticos, ver nota abajo)* |
| Llamadas | `param x` / `x = call f, n` / `call f, n` | `PARAM CALL` |
| Llamada virtual | `x = vcall obj, slot` (`n` va en el comentario) | `VCALL` |
| Retorno | `return x` / `return` | `RETURN` |
| Memoria (objetos/arreglos) | `x = y[off]` / `y[off] = x` | `LOAD STORE` |
| Arreglos | `x = newarray n` / `x = len a` / `boundscheck a, i` | `NEWARRAY LEN BOUNDS` |
| Objetos | `x = new ClassName, size` | `NEW` |
| Strings | `x = concat y, z` / `x = tostr y` | `CONCAT TOSTR` |
| Salida | `print x` | `PRINT` |
| Excepciones | `try_begin Lcatch` / `try_end` / `x = get_exception` / `throw x` | `TRY_BEGIN TRY_END GETEXC THROW` |
| Static link | `x = up k, off` / `up k, off = x` | `UPLOAD UPSTORE` |

**Nota — `func`/`endfunc` no son `Quad`s reales.** El printer los sintetiza a partir de
`TACFunction.name`/`.frame_size` (`ir/program.py`), porque `frame_size` solo se conoce al
terminar de generar el cuerpo (cuando ya se sabe `max_temps`, ver §5). Esto evita tener que
"parchar" un Quad ya emitido.

**Nota — `VCALL` y el conteo de argumentos `n`.** Un cuádruplo solo tiene 3 operandos
(`arg1, arg2, result`); `vcall` necesita 3 entradas (objeto, slot, n) + 1 salida, así que `n`
se imprime únicamente en el comentario (`# .metodo n=2`), no como operando real. El intérprete
no lo necesita: cada `param` empuja a una cola que el `call`/`vcall` siguiente vacía por
completo (el generador nunca deja `param`s pendientes sin consumir).

Convenciones:

- **Acceso a arreglos con offset en bytes explícito**: `a[i]` se traduce a
  `boundscheck a, i`, `t1 = i * 4`, `t1 = t1 + 4` (salta el header de longitud), `t2 = a[t1]`.
- **Campos por offset**: `obj.nombre` → `t = obj[8]  # .nombre` (el offset sale de
  `ClassType.field_offsets`, ver §4).
- Todos los valores ocupan **4 bytes** (`WORD_SIZE` en `semantic/symbol_table.py`). Strings,
  arreglos y objetos son referencias de 4 bytes.
- Etiquetas: `L<n>` control de flujo, `f_<nombre>` funciones de nivel superior,
  `<Clase>_<metodo>` métodos (incluye `constructor`), `f_<externa>__<interna>` funciones
  anidadas, `str_<n>` strings (deduplicados por valor).

## 3. Registros de activación (layout del frame)

El stack crece hacia abajo. `fp` apunta al inicio del frame:

```
          ...
fp + 8+4(n-1)  param n-1
          ...
fp + 8         param 0        (en métodos, param 0 = this)
fp + 4         dirección de retorno
fp + 0         fp anterior (dynamic link)
fp - 4         static link    (solo funciones anidadas; ver §6)
fp - 8         local 0
          ...
fp - k         temporales (t0, t1, ... tmax)
```

- `frame_size = 4 (static link si aplica) + tamaño_locales + 4 * max_temps`
  (`ActivationRecord.finalize()` en `semantic/symbol_table.py`).
- Las variables de bloques internos se aplanan en el frame de la función:
  `ActivationRecord.save_cursor()`/`restore_cursor()` hace que bloques **hermanos** (p.ej. el
  `then` y el `else` de un mismo `if`) reusen el mismo rango de offsets; `_max_local_bytes`
  guarda el punto más profundo alcanzado, que es lo que realmente determina el tamaño.
- Variables **globales** (y cualquier declaración fuera de toda función, incluso dentro de un
  bloque/if/while a nivel de programa) van en la sección de datos: `gp[off]`. Esto es una
  simplificación deliberada: no hace falta un `main` "de verdad" con su propio frame para el
  código de nivel superior.
- Atributos de clase (`storage="field"`) **no** tienen offset en su propio `Symbol`; su
  dirección real sale de `ClassType.field_offsets[nombre]` (ver §4), porque un mismo atributo
  puede alcanzarse desde muchas instancias distintas.

## 4. Clases

- Layout de instancia: slot `[0]` = referencia a la `ClassType` (actúa como "puntero a
  vtable"), luego los atributos. Los atributos **heredados van primero y conservan su offset**
  en la subclase (`ir/memory_layout.compute_class_layouts`).
- vtable por clase: lista de labels; un método sobrescrito ocupa el **mismo slot** que el del
  padre (incluye `constructor`: si una subclase no define uno propio, hereda el slot — y por
  lo tanto la llamada — del padre).
- `new C(args)`: `t = new C, size` → `param t` → `param args...` → `call C_constructor, n+1`.
  Si no hay constructor en toda la cadena de herencia, no se emite ninguna llamada (los campos
  quedan en su valor por defecto `0`, ver intérprete).
- Llamada a método `obj.metodo(args)`: `param obj` → `param args...` →
  `x = vcall obj, slot` — el generador detecta este patrón (`PropertyAccessExpr` seguido de
  `CallExpr` sobre un `ClassType`) en `ir/tac_generator._gen_left_hand_side`.

## 5. Temporales: asignación y reciclaje

`TempAllocator` (`ir/temp_allocator.py`), uno por función:

- `new_temp() -> Temp`: índice libre más pequeño (min-heap) o uno nuevo.
- `release(op)`: si `op` es `Temp`, lo devuelve al pool; no hace nada con otros operandos.
  Liberar un temporal ya liberado (o uno "obsoleto" cuyo índice ya fue reciclado) lanza
  `TempAllocatorError`.
- `max_used`: pico de temporales vivos simultáneamente → alimenta `frame_size`.
- `reset()` / instancia nueva: al entrar a cada función (`ir/tac_generator` mantiene una pila
  de `TempAllocator`, uno por nivel de función anidada, para no mezclar sus contadores).

Reglas de uso (`ir/tac_generator.py`):

1. Tras emitir `x = y op z`, liberar `y` y `z` **antes** de pedir el temporal destino.
2. Un temporal se libera **exactamente una vez**, cuando su valor se consume.
3. Al terminar una sentencia de nivel superior no debe quedar ningún temporal vivo — hay un
   `assert self.temps.live == 0` explícito en `_gen_statement`. Estado "oculto" que debe
   sobrevivir un ciclo completo (índice/longitud/base de un `foreach`) se aloja como
   **variable local oculta** (`_new_hidden_local`), no como temporal, precisamente para no
   violar esta regla.
4. Asignación directa a variable no necesita temporal extra ("optimización de destino"):
   `x = a + b` → `x = a + b`, nunca `t0 = a + b; x = t0`.

Ejemplo real (`tests/cases/success/temp_reuse.cps`) para `x = (a + b) * (c - d) + e;`:

```
t0 = a + b
t1 = c - d
t0 = t0 * t1
x = t0 + e
```

## 6. Funciones anidadas (closures)

Static link (access link): al invocar una función anidada se pasa el `fp` actual del llamador
(`param fp`, operando `FramePointer`); `up k, off` accede a una variable `k` niveles arriba
(`k` se calcula comparando la cadena de `ActivationRecord` activos al momento de generar el
acceso contra la del `Symbol`, en `_static_link_depth`).

**Supuesto/alcance (simplificación deliberada):** solo se soporta invocar una función anidada
**directamente desde su padre léxico inmediato** — se le pasa siempre el `fp` actual del
llamador como static link. Invocar una función anidada desde un "primo" (otra función anidada
en el mismo padre, o un nieto) requeriría encadenar el propio static link del llamador en vez
de su `fp`, lo cual no está implementado. La gramática de Compiscript no permite retornar
funciones como valores, así que no hace falta heap para closures.

Ejemplo real (`crearContador`/`siguiente` del enunciado):

```
func f_crearContador, 8
    base = 10
    param fp
    t0 = call f_crearContador__siguiente, 1    # siguiente n=1
    return t0
endfunc f_crearContador

func f_crearContador__siguiente, 8
    t0 = up 1, -8    # up base
    t0 = t0 + 1
    return t0
endfunc f_crearContador__siguiente
```

## 7. Control de flujo

- Condiciones con código de saltos: `_gen_cond(expr, l_true, l_false)` (cualquiera de los dos
  puede ser `None` = "cae al siguiente instrucción"), con corto-circuito real para `&&`, `||`
  y `!` (nunca evalúa el lado derecho si el corto-circuito ya decidió el resultado). Cuando el
  booleano se necesita **como valor** (`let b = x < 3 && y;`), se materializa `1`/`0` con
  etiquetas (`_gen_bool_value`).
- Comparaciones relacionales/de igualdad usadas como condición emiten el salto relacional
  directo (`IF_LT`, etc.) en vez de `t = a < b; ifFalse t goto L` — una instrucción menos y
  cero temporales, aprovechando que el operador negado (`NEGATED_RELATIONAL`) permite
  sintetizar la rama "falsa" sin duplicar código.
- Pila de ciclos (`LoopContext(break_label, continue_label)`): `while`/`do-while`/`for`/
  `foreach` apilan ambos labels; `switch` apila solo `break_label` (`continue_label=None`), así
  que un `continue` dentro de un `switch` sigue buscando hacia afuera hasta el ciclo más
  cercano, mientras que `break` sí se detiene en el `switch`.
- `for (init; cond; update)`: `init` → `L_cond:` → salto de salida si `cond` es falsa → body →
  `L_update:` (= destino de `continue`) → `update` → `goto L_cond` → `L_end:`.
- `foreach (item in arr)`: base/índice/longitud son **variables locales ocultas** (no
  temporales, ver §5 regla 3); `item` es el `Symbol` del scope del ciclo.
- `switch`: la expresión se evalúa **una sola vez** y se libera **después** de la cadena
  completa de comparaciones (nunca antes, aunque cada comparación individual sí libera su
  propio operando); cuerpos consecutivos (fallthrough real, sin `goto` implícito entre
  `case`s); `default` al final de la cadena de comparaciones.
- `try/catch`: `try_begin L_catch` … `try_end` → `goto L_end` → `L_catch:` →
  `err = get_exception` … `L_end:`. Un `boundscheck` fallido lanza una excepción (mensaje
  string) capturable por el `catch` más cercano.
- Ternario: como `if/else` escribiendo ambos lados en el mismo temporal/destino.

## 8. Strings y print

- Literales en sección de datos, deduplicados por **valor** (dos literales `"hola"` en
  cualquier parte del programa comparten `str_N`).
- `string + X` (o `X + string`): si `X` no es de tipo `string` (incluye `any`, p.ej. la
  variable de un `catch`) se convierte con `tostr` y luego se `concat`ena.
- `print x` imprime el valor tal cual (el intérprete usa `str()`); no hay opcodes separados
  `print_int`/`print_str` — no hicieron falta porque `tostr`/`str()` ya cubren todos los casos.

## 9. Ejemplo completo (`tests/cases/success/factorial.cps`)

```cps
function factorial(n: integer): integer {
  if (n <= 1) { return 1; }
  return n * factorial(n - 1);
}
print(factorial(5));
```

```
func main, 4
    param 5
    t0 = call f_factorial, 1    # factorial n=1
    print t0
    return
endfunc main

func f_factorial, 4
    t0 = n <= 1
    ifFalse t0 goto L0
    return 1
L0:
    t0 = n - 1
    param t0
    t0 = call f_factorial, 1    # factorial n=1
    t0 = n * t0
    return t0
endfunc f_factorial
```

(Nótese que aquí el generador usó `t0 = n <= 1; ifFalse t0 goto L0` en vez del salto relacional
directo porque la condición completa del `if` pasó por el camino general de `_gen_cond` — en
la práctica ambas formas conviven en el mismo programa según qué construcción dispara cada
camino del generador.)

## 10. Supuestos y decisiones de diseño

- Palabra de 4 bytes (`WORD_SIZE`), arquitectura destino asumida tipo MIPS para la Fase 3.
- Booleanos representados como `1`/`0`; `null` es `0`.
- `switch` hace fallthrough (semántica TS/C) salvo `break` explícito.
- **`float` (decisión tomada):** la gramática de este proyecto sí incluye
  `float` (`FloatLiteral`, `baseType` con `'float'`), a diferencia del supuesto original de que
  toda la aritmética era entera. Se decidió **(a) no crear opcodes flotantes separados**: los
  mismos `ADD/SUB/MUL/MOD` operan sobre `int` o `float` de Python indistintamente (no hay
  distinción de tipo a nivel de TAC, solo a nivel del análisis semántico que ya existía en la
  Fase 1); no hace falta `itof` porque Python promueve automáticamente al operar. La única
  instrucción sensible al tipo es `DIV`: si ambos operandos son enteros trunca hacia cero
  (convención C/Java), si alguno es flotante hace división real. Limitación conocida: el TAC
  impreso no distingue si una `Const` es entera o flotante salvo por su valor (`5` vs `5.0`).
- **Registro de activación de `main`:** las sentencias de nivel superior se agrupan en una
  función `main` real (con su propio frame para temporales), pero las declaraciones `let`/
  `const` de nivel superior — incluso dentro de bloques/if/while sueltos a nivel de programa —
  son **globales** (`gp[off]`), no locales de `main`. Esto simplifica el diseño (no hace falta
  decidir el frame de `main` de antemano) sin perder nada observable.
- **Funciones anidadas:** solo se soporta invocar una función anidada desde su padre léxico
  inmediato (ver §6). Llamar a una función anidada desde un "primo" no está soportado.
- **`VCALL` no lleva `n` como operando** (ver nota en §2): se infiere en tiempo de ejecución
  vaciando la cola de `param` pendientes.
