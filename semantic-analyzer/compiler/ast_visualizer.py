# compiler/ast_visualizer.py
"""
Visual AST generator for Compiscript.
Uses the graphviz library to produce SVG/PNG representations of the parse tree.
"""
from __future__ import annotations

import os
import sys
from typing import Optional

# Auto-detect generated file location (flat or nested subdirectory)
_GEN_FLAT   = os.path.join(os.path.dirname(__file__), "generated")
_GEN_NESTED = os.path.join(os.path.dirname(__file__), "generated", "compiler")
for _p in [_GEN_FLAT, _GEN_NESTED]:
    if os.path.isfile(os.path.join(_p, "CompiscriptLexer.py")):
        sys.path.insert(0, os.path.abspath(_p))
        break

from antlr4 import ParserRuleContext, TerminalNode

try:
    import graphviz
    GRAPHVIZ_AVAILABLE = True
except ImportError:
    GRAPHVIZ_AVAILABLE = False


# Map rule index → friendly label
def _rule_name(parser, rule_index: int) -> str:
    names = parser.ruleNames
    if 0 <= rule_index < len(names):
        return names[rule_index]
    return f"rule_{rule_index}"


def _short_text(text: str, max_len: int = 24) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len - 3] + "..."


class ASTVisualizer:
    """
    Walks an ANTLR4 parse tree and builds a graphviz Digraph.
    """

    # Color palette for node kinds
    COLORS = {
        "program": "#1a1a2e",
        "statement": "#16213e",
        "declaration": "#0f3460",
        "expression": "#533483",
        "literal": "#e94560",
        "terminal": "#2c3e50",
        "default": "#27ae60",
    }

    def __init__(self, parser):
        self._parser = parser
        self._counter = 0

    def _next_id(self) -> str:
        self._counter += 1
        return f"n{self._counter}"

    def _categorize(self, name: str) -> str:
        n = name.lower()
        if n in ("program",):
            return "program"
        if "statement" in n:
            return "statement"
        if "declaration" in n:
            return "declaration"
        if "expr" in n or "expression" in n:
            return "expression"
        if "literal" in n:
            return "literal"
        return "default"

    def _add_node(self, graph: "graphviz.Digraph", label: str, kind: str) -> str:
        node_id = self._next_id()
        color = self.COLORS.get(kind, self.COLORS["default"])
        graph.node(
            node_id,
            label=label,
            style="filled,rounded",
            fillcolor=color,
            fontcolor="white",
            fontname="Consolas, monospace",
            shape="box",
        )
        return node_id

    def _build(self, graph: "graphviz.Digraph", ctx) -> str:
        if isinstance(ctx, TerminalNode):
            text = _short_text(ctx.getText())
            node_id = self._add_node(graph, text, "terminal")
            return node_id

        # Rule node
        rule_name = _rule_name(self._parser, ctx.getRuleIndex())
        kind = self._categorize(rule_name)
        node_id = self._add_node(graph, rule_name, kind)

        for child in ctx.getChildren():
            child_id = self._build(graph, child)
            graph.edge(node_id, child_id)

        return node_id

    def generate(
        self,
        parse_tree,
        output_path: str = "ast_output",
        fmt: str = "svg",
    ) -> Optional[str]:
        """
        Generate the AST and render it.
        Returns the output file path, or None if graphviz is not available.
        """
        if not GRAPHVIZ_AVAILABLE:
            return None

        dot = graphviz.Digraph(
            name="AST",
            graph_attr={
                "bgcolor": "#0d1117",
                "rankdir": "TB",
                "splines": "curved",
                "nodesep": "0.4",
                "ranksep": "0.6",
            },
            edge_attr={
                "color": "#58a6ff",
                "arrowsize": "0.7",
            },
        )
        self._build(dot, parse_tree)

        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
        rendered = dot.render(output_path, format=fmt, cleanup=True, quiet=True)
        return rendered


def tree_to_dict(ctx, parser) -> dict:
    """Serialize the parse tree to a JSON-friendly dict (for the IDE)."""
    if isinstance(ctx, TerminalNode):
        return {"type": "terminal", "text": ctx.getText()}
    rule_name = _rule_name(parser, ctx.getRuleIndex())
    children = [tree_to_dict(child, parser) for child in ctx.getChildren()]
    return {"type": rule_name, "children": children}
