"""IDE en Streamlit: editor, compilar, ver TAC y tabla de símbolos, y ejecutar.

Ejecutar con: streamlit run src/compiscript/ide/app.py
"""
from __future__ import annotations

import streamlit as st

from compiscript import pipeline
from compiscript.ir.interpreter import CompiscriptRuntimeError, Interpreter

try:
    from streamlit_ace import st_ace
    _HAS_ACE = True
except ImportError:  # si no está streamlit-ace se usa un text_area
    _HAS_ACE = False

DEFAULT_SOURCE = """function factorial(n: integer): integer {
  if (n <= 1) { return 1; }
  return n * factorial(n - 1);
}
print(factorial(5));
"""

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', -apple-system, sans-serif; }

.block-container { padding-top: 2.5rem; padding-bottom: 3rem; max-width: 1280px; }

/* Encabezado */
.cs-eyebrow {
    display: inline-flex; align-items: center; gap: .4rem;
    font-size: .75rem; font-weight: 600; letter-spacing: .08em; text-transform: uppercase;
    color: #8B96A5; background: rgba(91,141,239,.10); border: 1px solid rgba(91,141,239,.25);
    padding: .25rem .65rem; border-radius: 999px; margin-bottom: .9rem;
}
.cs-title { font-size: 2.1rem; font-weight: 700; line-height: 1.15; margin: 0 0 .35rem 0; }
.cs-subtitle { color: #8B96A5; font-size: .95rem; margin-bottom: 1.6rem; }

/* Tarjetas (st.container(border=True)) */
div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 14px !important;
    border-color: rgba(255,255,255,.08) !important;
    background: #12161F;
}
div[data-testid="stVerticalBlockBorderWrapper"] > div { padding: .35rem; }

.cs-panel-title {
    font-size: .78rem; font-weight: 600; letter-spacing: .04em; text-transform: uppercase;
    color: #8B96A5; margin-bottom: .6rem; display: flex; align-items: center; gap: .4rem;
}

/* Botones */
.stButton>button {
    border-radius: 10px; font-weight: 600; border: 1px solid rgba(255,255,255,.08);
    transition: transform .05s ease, filter .15s ease;
}
.stButton>button:hover { filter: brightness(1.08); }
.stButton>button:active { transform: scale(.99); }
.stButton>button[kind="primary"] { box-shadow: 0 4px 14px rgba(91,141,239,.28); }

/* Bloques de código / salida */
pre, code, .stCodeBlock, .stCodeBlock pre {
    font-family: 'JetBrains Mono', ui-monospace, monospace !important;
    font-size: .84rem !important;
}
.stCodeBlock pre { border-radius: 10px !important; border: 1px solid rgba(255,255,255,.06); }

/* Tabs */
.stTabs [data-baseweb="tab-list"] { gap: 4px; border-bottom: 1px solid rgba(255,255,255,.08); }
.stTabs [data-baseweb="tab"] {
    height: 38px; border-radius: 8px 8px 0 0; padding: 0 1rem; font-weight: 500;
}

/* Toggle / caption */
.stCaption, [data-testid="stCaptionContainer"] { color: #8B96A5 !important; }

/* Alerts mas discretas */
div[data-testid="stAlertContainer"] { border-radius: 10px; }

hr { border-color: rgba(255,255,255,.08) !important; }
</style>
"""


def _editor(source: str) -> str:
    if _HAS_ACE:
        return st_ace(
            value=source,
            language="typescript",
            theme="tomorrow_night_eighties",
            keybinding="vscode",
            font_size=14,
            tab_size=2,
            show_gutter=True,
            show_print_margin=False,
            wrap=False,
            auto_update=True,
            height=440,
            key="editor",
        )
    return st.text_area("Código Compiscript", value=source, height=440, key="editor",
                         label_visibility="collapsed")


def _render_errors(result) -> None:
    with st.container(border=True):
        st.markdown(
            f'<div class="cs-panel-title">⛔ {len(result.errors)} error(es) de compilación</div>',
            unsafe_allow_html=True,
        )
        for err in result.errors:
            st.code(err, language=None)


def _render_success(result) -> None:
    st.success(f"Compilación exitosa · {len(result.program.functions)} función(es) generada(s)",
               icon="✅")

    if result.warnings:
        with st.expander(f"⚠️ {len(result.warnings)} advertencia(s)"):
            for w in result.warnings:
                st.code(w, language=None)

    tab_tac, tab_symbols, tab_run = st.tabs(["📄 TAC", "🗂️ Tabla de símbolos", "▶️ Ejecutar"])

    with tab_tac:
        addresses = st.toggle("Mostrar direcciones de memoria (fp[off] / gp[off])", value=False)
        tac_text = result.tac_text_addresses if addresses else result.tac_text
        st.code(tac_text, language=None)

    with tab_symbols:
        st.code(result.symbol_table.dump(), language=None)

    with tab_run:
        run_clicked = st.button("Ejecutar", icon="▶️", use_container_width=False)
        if run_clicked:
            interp = Interpreter(result.program, result.analyzer.class_registry)
            try:
                st.session_state["run_output"] = interp.run()
                st.session_state["run_error"] = None
            except CompiscriptRuntimeError as exc:
                st.session_state["run_output"] = "\n".join(interp.output)
                st.session_state["run_error"] = str(exc.value)

        if st.session_state.get("run_error"):
            st.error(f"Excepción no capturada: {st.session_state['run_error']}", icon="💥")
        output = st.session_state.get("run_output")
        if output:
            st.markdown('<div class="cs-panel-title">Salida del programa</div>',
                        unsafe_allow_html=True)
            st.code(output, language=None)
        elif not run_clicked:
            st.caption("Presiona **Ejecutar** para correr el programa con el intérprete de TAC.")


def main() -> None:
    st.set_page_config(page_title="Compiscript IDE", page_icon="🧩", layout="wide")
    st.markdown(_CSS, unsafe_allow_html=True)

    st.markdown('<div class="cs-eyebrow">🧩 Fase 2 · Código intermedio</div>', unsafe_allow_html=True)
    st.markdown('<p class="cs-title">Compiscript IDE</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="cs-subtitle">Escribe Compiscript, compílalo a TAC y ejecútalo — '
        'ver <code>docs/TAC_LANGUAGE.md</code> para la especificación del lenguaje intermedio.</p>',
        unsafe_allow_html=True,
    )

    if "source" not in st.session_state:
        st.session_state["source"] = DEFAULT_SOURCE

    left, right = st.columns([1, 1], gap="large")

    with left:
        with st.container(border=True):
            st.markdown('<div class="cs-panel-title">✏️ Editor</div>', unsafe_allow_html=True)
            source = _editor(st.session_state["source"])
            st.session_state["source"] = source
            compile_clicked = st.button(
                "Compilar", type="primary", icon="⚙️", use_container_width=True,
            )

    if compile_clicked:
        st.session_state["result"] = pipeline.compile(source)
        st.session_state.pop("run_output", None)
        st.session_state.pop("run_error", None)

    result = st.session_state.get("result")

    with right:
        if result is None:
            with st.container(border=True):
                st.markdown('<div class="cs-panel-title">Resultado</div>', unsafe_allow_html=True)
                st.caption("Escribe código y presiona **Compilar** para ver el TAC generado, "
                           "la tabla de símbolos y la salida de ejecución.")
        elif not result.ok:
            _render_errors(result)
        else:
            _render_success(result)


if __name__ == "__main__":
    main()
