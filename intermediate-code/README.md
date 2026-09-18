# intermediate-code — Fase 2: Generación de Código Intermedio

Genera Código de Tres Direcciones (TAC) a partir de Compiscript, reutilizando y extendiendo el
analizador semántico de la Fase 1 (`semantic-analyzer/`, congelada).

- Contexto y reglas de diseño completas: [`../CLAUDE.md`](../CLAUDE.md).
- Desglose de trabajo por ticket/integrante: [`../FEATURES.md`](../FEATURES.md).
- Arquitectura y pipeline: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).
- Especificación del lenguaje intermedio (TAC): [`docs/TAC_LANGUAGE.md`](docs/TAC_LANGUAGE.md).
- Referencia completa de comandos: [`docs/USAGE.md`](docs/USAGE.md).

## Cómo probar todo el proyecto

Sigue estos pasos en orden — cada uno prueba una parte distinta del compilador.

### 0. Requisitos

- Python 3.10 o superior.
- (Opcional) Java, solo si vas a regenerar el lexer/parser porque cambió la gramática.

### 1. Instalar

```bash
cd intermediate-code
python3 -m venv .venv
source .venv/bin/activate        # en Windows: .venv\Scripts\activate
pip install -e ".[dev,ide]"
```

Esto instala el paquete `compiscript` en modo editable (los cambios en `src/` se reflejan sin
reinstalar) más `pytest` (tests) y `streamlit`/`streamlit-ace` (IDE).

> **Importante:** repite `source .venv/bin/activate` cada vez que abras una terminal nueva
> antes de correr cualquier comando de esta guía. Si un comando dice
> `ModuleNotFoundError: No module named 'compiscript'`, es casi siempre porque el venv no está
> activo en esa terminal — ver la sección de *Solución de problemas* al final.

### 2. Compilar y ejecutar un programa por consola (CLI)

```bash
python -m compiscript.main examples/factorial.cps --run
```

Deberías ver el TAC generado (funciones `main` y `f_factorial`) y, al final, `120` (la salida
de `print(factorial(5))` ejecutada por el intérprete). Otras variantes útiles:

```bash
python -m compiscript.main examples/factorial.cps                 # solo imprime el .tac
python -m compiscript.main examples/factorial.cps --addresses     # TAC con fp[off]/gp[off]
python -m compiscript.main examples/factorial.cps --dump-symbols  # + tabla de símbolos y frames
python -m compiscript.main examples/clases.cps --run              # herencia + vtables + this/new
```

Prueba con un archivo con error a propósito para ver el reporte de errores:

```bash
python -m compiscript.main tests/cases/failure/undeclared_variable.cps
```

### 3. Correr la batería de tests

```bash
pytest -q
```

Deberían pasar **61 tests**. Qué valida cada grupo (`tests/test_*.py`):

| Archivo | Qué prueba |
|---|---|
| `test_temp_allocator.py` | Reciclaje de temporales (el requisito explícito de la rúbrica): reuso del índice más pequeño libre, `max_used`, doble liberación lanza error |
| `test_memory_layout.py` | Offsets de variables/parámetros, `frame_size`, reuso de offsets entre bloques hermanos, layout de clases con herencia |
| `test_symbol_table_ar.py` | Tablas laterales (`node_types`/`scope_of`/`symbol_of`), *shadowing*, registros de activación |
| `test_expressions.py` | Precedencia de operadores, asociatividad, cortocircuito de `&&`/`\|\|`, optimización de destino |
| `test_control_flow.py` | `if/while/do-while/for/foreach`, `break`/`continue` anidados, `switch` con fallthrough |
| `test_functions.py` | Funciones, recursión, funciones anidadas (closures) con static link |
| `test_classes.py` | Constructores, herencia, despacho virtual (`vtable`), instancias independientes |
| `test_arrays.py` | Arreglos 1D/2D, `boundscheck`, `try/catch` capturando un índice fuera de rango |
| `test_golden.py` | Compara el `.tac` generado contra los esperados en `tests/cases/success/*.tac` |
| `test_failures.py` | Los `.cps` en `tests/cases/failure/` deben fallar al compilar |

Para ver con detalle qué hace cada test (y aprender la sintaxis de Compiscript a la vez), abre
cualquiera de esos archivos — son cortos y legibles.

Si modificas el generador de TAC y necesitas regenerar los `.tac`/`.out` esperados:

```bash
pytest -q --update-golden    # revisa el diff (git diff tests/cases/success/) antes de commitear
```

### 4. Probar el IDE

```bash
python -m streamlit run src/compiscript/ide/app.py
```

Se abre en `http://localhost:8501`. Ahí puedes:

1. Escribir o pegar código Compiscript en el editor (ya trae el ejemplo de `factorial` cargado).
2. Presionar **Compilar** — si hay errores, se listan con línea/columna; si compila, se
   habilitan 3 pestañas:
   - **TAC**: el código de tres direcciones generado, con un switch para alternar entre
     nombres simbólicos (`x`) y direcciones de memoria (`fp[-8]`, `gp[4]`).
   - **Tabla de símbolos**: el árbol de *scopes* con offsets y registros de activación
     (lo mismo que `--dump-symbols` en el CLI).
   - **Ejecutar**: corre el TAC con el intérprete y muestra la salida de `print`.

Prueba pegando el contenido de `examples/clases.cps` o cualquier archivo de
`tests/cases/success/` para ver ejemplos más complejos (herencia, arreglos, etc.).

### 5. Escribir tu propio programa

Crea un archivo `.cps` en cualquier lado (o pégalo directo en el IDE) usando las construcciones
que soporta el lenguaje — ver los ejemplos en `examples/`, `tests/cases/success/`, o la
descripción completa del lenguaje en `docs/TAC_LANGUAGE.md`. Recuerda que **los bloques de
`if`/`while`/`for`/etc. requieren llaves `{ }`** (no se permite una sola sentencia sin llaves).

```bash
python -m compiscript.main mi_programa.cps --run
```

### 6. (Opcional) Docker

```bash
docker build --rm . -t csp-ic
docker run --rm -ti -v "$(pwd)":/app -p 8501:8501 csp-ic
```

> Nota: esta imagen no se ha verificado de punta a punta en este proyecto todavía (descarga
> ANTLR + Java). Si algo falla, la vía confiable por ahora es la instalación local (pasos 1–4).

## Solución de problemas

- **`ModuleNotFoundError: No module named 'compiscript'`** al correr `streamlit run` o
  `python -m compiscript.main`: el venv no está activo en esa terminal, o `streamlit` se está
  resolviendo a una instalación distinta (por ejemplo, `/Library/Frameworks/...` en macOS en
  vez de `.venv/bin/streamlit`). Solución:
  ```bash
  source .venv/bin/activate
  which python        # debe apuntar a .../intermediate-code/.venv/bin/python
  python -m streamlit run src/compiscript/ide/app.py   # usa python -m para forzar el venv activo
  ```
- **El IDE se ve con colores por defecto de Streamlit (fondo blanco en el editor, botón rojo)**:
  el tema sale de `.streamlit/config.toml` y solo se lee al **arrancar** el proceso — si lo
  cambiaste, reinicia Streamlit (`Ctrl+C` y volver a correr el comando).
- **`pytest -q` falla con errores de import**: asegúrate de correrlo desde `intermediate-code/`
  con el venv activo y el paquete instalado (`pip install -e ".[dev]"`).
