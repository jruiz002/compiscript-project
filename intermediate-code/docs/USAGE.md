# USAGE — Instalación y comandos

## Docker

```bash
cd intermediate-code
docker build --rm . -t csp-ic
docker run --rm -ti -v "$(pwd)":/app -p 8501:8501 csp-ic
```

## Entorno local (sin Docker)

Requiere Python 3.10+ y Java (solo si vas a regenerar el lexer/parser con ANTLR).

```bash
cd intermediate-code
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,ide]"
```

## Regenerar lexer/parser (solo si cambia la gramática)

```bash
antlr -Dlanguage=Python3 -visitor -no-listener \
  -o src/compiscript/generated grammar/Compiscript.g4
```

## Compilar un programa

```bash
python -m compiscript.main examples/factorial.cps                 # imprime el .tac en stdout
python -m compiscript.main examples/factorial.cps --run           # además lo ejecuta y muestra la salida
python -m compiscript.main examples/factorial.cps --addresses     # TAC con fp[off]/gp[off] en vez de nombres
python -m compiscript.main examples/factorial.cps --dump-symbols  # + tabla de símbolos y registros de activación
python -m compiscript.main examples/factorial.cps --out salida.tac  # escribe el .tac a un archivo
```

Hay ejemplos listos en `examples/` (`factorial.cps`, `clases.cps`) y muchos más casos de prueba
(control de flujo, arreglos/foreach, funciones anidadas, try/catch, clases) en
`tests/cases/success/` y `tests/cases/failure/`.

## Tests

```bash
pytest -q
pytest -q --update-golden   # regenera los .tac esperados en tests/cases/success/ (revisar el diff antes de commitear)
```

## IDE

```bash
streamlit run src/compiscript/ide/app.py
```
