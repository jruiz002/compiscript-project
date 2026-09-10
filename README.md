# Compiscript

Compilador de **Compiscript** (subset de TypeScript) construido por fases en el curso de
Construcción de Compiladores. Grupo de 3 integrantes — ver reparto de trabajo y estado en
[`FEATURES.md`](FEATURES.md).

## Fases

| Fase | Directorio | Estado | Descripción |
|---|---|---|---|
| 1 — Análisis semántico | [`semantic-analyzer/`](semantic-analyzer/) | ✅ Congelada (solo lectura) | Léxico/sintáctico (ANTLR4) + tipos, ámbitos y tabla de símbolos. |
| 2 — Código intermedio | [`intermediate-code/`](intermediate-code/) | ✅ Funcional | Generación de TAC, tabla de símbolos extendida (offsets, registros de activación), intérprete e IDE. |
| 3 — Código assembler | _(futura)_ | ⏳ Pendiente | Traducción del TAC a código de máquina/ensamblador. |

## Quickstart (Fase 2 — lo que se entrega ahora)

```bash
cd intermediate-code
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,ide]"

# Compilar y ejecutar un ejemplo
python -m compiscript.main examples/factorial.cps --run

# Correr toda la batería de tests
pytest -q

# Abrir el IDE (editor + botón Compilar + panel de TAC/símbolos/Ejecutar)
streamlit run src/compiscript/ide/app.py
```

Ver [`intermediate-code/docs/USAGE.md`](intermediate-code/docs/USAGE.md) para todas las
variantes del CLI (`--addresses`, `--dump-symbols`, `--out`), Docker, y cómo regenerar el
lexer/parser si cambia la gramática.

## Dónde encontrar cada cosa

| Quiero... | Voy a... |
|---|---|
| Entender el lenguaje intermedio (TAC) diseñado, con ejemplos y supuestos | [`intermediate-code/docs/TAC_LANGUAGE.md`](intermediate-code/docs/TAC_LANGUAGE.md) |
| Entender la arquitectura/pipeline del compilador | [`intermediate-code/docs/ARCHITECTURE.md`](intermediate-code/docs/ARCHITECTURE.md) |
| Ver qué falta y quién es dueño de qué (tickets, estado) | [`FEATURES.md`](FEATURES.md) |
| Ver las reglas de diseño y convenciones del proyecto | [`CLAUDE.md`](CLAUDE.md) |
| Ver la Fase 1 (análisis semántico, congelada) | [`semantic-analyzer/README.md`](semantic-analyzer/README.md) |

## Reglas importantes

- **Nunca editar `semantic-analyzer/`** — está congelada como entrega de la Fase 1. Todo el
  trabajo nuevo va en `intermediate-code/` (que sí copia y extiende el código semántico, en
  `intermediate-code/src/compiscript/semantic/`).
- Los commits se evalúan individualmente por integrante: la rúbrica exige que se note
  claramente qué porción implementó cada quien. Ver la nota de atribución en `FEATURES.md`.
