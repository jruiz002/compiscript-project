# compiler/symbol_table_viz.py
"""
Visual symbol table generator for Compiscript.
Renders the nested scope tree produced by SymbolTable.to_dict() as SVG/PNG,
one HTML-like table per scope.
"""
from __future__ import annotations

import os
from typing import Optional

try:
    import graphviz
    GRAPHVIZ_AVAILABLE = True
except ImportError:
    GRAPHVIZ_AVAILABLE = False


# Header color per scope kind
SCOPE_COLORS = {
    "global":   "#1a1a2e",
    "function": "#0f3460",
    "class":    "#533483",
    "loop":     "#27ae60",
    "switch":   "#b7791f",
    "block":    "#16213e",
}

# Text color per symbol kind
KIND_COLORS = {
    "constant":      "#e94560",
    "function":      "#58a6ff",
    "class":         "#c792ea",
    "parameter":     "#ffcb6b",
    "loop_variable": "#7ee787",
    "variable":      "#e6edf3",
}


def _esc(text: str) -> str:
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _scope_label(scope: dict) -> str:
    """Build an HTML-like table: header = scope, one row per symbol."""
    header_color = SCOPE_COLORS.get(scope["kind"], SCOPE_COLORS["block"])
    title = f'{_esc(scope["name"])}  ({_esc(scope["kind"])}, nivel {scope["level"]})'

    rows = [
        f'<TR><TD COLSPAN="4" BGCOLOR="{header_color}">'
        f'<FONT COLOR="white"><B>{title}</B></FONT></TD></TR>'
    ]

    symbols = [s for s in scope["symbols"] if not s["name"].startswith("__")]
    if not symbols:
        rows.append(
            '<TR><TD COLSPAN="4"><FONT COLOR="#6e7681"><I>(sin símbolos)</I></FONT></TD></TR>'
        )
    else:
        rows.append(
            '<TR><TD><FONT COLOR="#8b949e"><B>nombre</B></FONT></TD>'
            '<TD><FONT COLOR="#8b949e"><B>kind</B></FONT></TD>'
            '<TD><FONT COLOR="#8b949e"><B>tipo</B></FONT></TD>'
            '<TD><FONT COLOR="#8b949e"><B>línea</B></FONT></TD></TR>'
        )
        for sym in symbols:
            color = KIND_COLORS.get(sym["kind"], KIND_COLORS["variable"])
            init = "" if sym["is_initialized"] else " *"   # * = declarado, sin inicializar
            rows.append(
                f'<TR>'
                f'<TD ALIGN="LEFT"><FONT COLOR="{color}">{_esc(sym["name"])}{init}</FONT></TD>'
                f'<TD ALIGN="LEFT"><FONT COLOR="{color}">{_esc(sym["kind"])}</FONT></TD>'
                f'<TD ALIGN="LEFT"><FONT COLOR="#e6edf3">{_esc(sym["type"])}</FONT></TD>'
                f'<TD ALIGN="RIGHT"><FONT COLOR="#6e7681">{sym["line"]}</FONT></TD>'
                f'</TR>'
            )

    return (
        '<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4" '
        f'BGCOLOR="#161b22" COLOR="#30363d">{"".join(rows)}</TABLE>>'
    )


def _build(dot: "graphviz.Digraph", scope: dict, node_id: str = "s0") -> None:
    dot.node(node_id, label=_scope_label(scope), shape="plaintext")
    for i, child in enumerate(scope.get("children", [])):
        child_id = f"{node_id}_{i}"
        _build(dot, child, child_id)
        dot.edge(node_id, child_id)


def generate(symbol_table: dict, output_path: str = "symbols_output",
             fmt: str = "svg", dpi: int = 96) -> Optional[str]:
    """
    Render a SymbolTable.to_dict() result. Returns the output path,
    or None if graphviz is not available.
    """
    if not GRAPHVIZ_AVAILABLE or not symbol_table:
        return None

    dot = graphviz.Digraph(
        name="SymbolTable",
        graph_attr={"bgcolor": "#0d1117", "rankdir": "TB",
                    "nodesep": "0.5", "ranksep": "0.7", "dpi": str(dpi)},
        node_attr={"fontname": "Consolas, monospace", "fontsize": "11"},
        edge_attr={"color": "#58a6ff", "arrowsize": "0.7"},
    )
    _build(dot, symbol_table)

    parent = os.path.dirname(output_path)
    os.makedirs(parent if parent else ".", exist_ok=True)
    return dot.render(output_path, format=fmt, cleanup=True, quiet=True)
