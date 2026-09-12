#!/usr/bin/env python3
# ide/server.py
"""
Compiscript IDE — Flask backend.
Serves the IDE frontend and exposes a /compile endpoint.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

# Ensure project root is on path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GENERATED_DIR = os.path.join(PROJECT_ROOT, "compiler", "generated")

# Auto-detect generated file location
for _p in [GENERATED_DIR, os.path.join(GENERATED_DIR, "compiler")]:
    if os.path.isfile(os.path.join(_p, "CompiscriptLexer.py")):
        sys.path.insert(0, os.path.abspath(_p))
        break

sys.path.insert(0, PROJECT_ROOT)

from antlr4 import CommonTokenStream, InputStream
from antlr4.error.ErrorListener import ErrorListener
from CompiscriptLexer import CompiscriptLexer
from CompiscriptParser import CompiscriptParser

from compiler.driver import compile_source
from compiler.ast_visualizer import ASTVisualizer

app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


@app.route("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.route("/compile", methods=["POST"])
def compile_endpoint():
    """
    POST /compile
    Body: { "code": "<source code>", "ast": true/false }
    Returns: { "errors": [...], "warnings": [...], "symbol_table": {...}, "ast_svg": "..." | null }
    """
    data = request.get_json(force=True, silent=True) or {}
    source = data.get("code", "")
    generate_ast = data.get("ast", True)

    if not source.strip():
        return jsonify({"errors": [], "warnings": [], "symbol_table": {}, "ast_svg": None})

    try:
        ast_svg = None
        if generate_ast:
            ast_svg = _generate_ast_svg(source)

        result = compile_source(source, source_name="<ide>", generate_ast=False)
        result["ast_svg"] = ast_svg
        return jsonify(result)

    except Exception as exc:
        return jsonify({
            "errors": [{"message": f"Internal error: {exc}", "line": 0, "column": 0,
                        "severity": "error", "phase": "internal"}],
            "warnings": [],
            "symbol_table": {},
            "ast_svg": None,
        }), 200


def _generate_ast_svg(source: str) -> str | None:
    """Generate an SVG string of the parse tree."""
    try:
        class _Silent(ErrorListener):
            def syntaxError(self, *args): pass

        stream = InputStream(source)
        lexer = CompiscriptLexer(stream)
        lexer.removeErrorListeners()
        lexer.addErrorListener(_Silent())
        tokens = CommonTokenStream(lexer)
        parser = CompiscriptParser(tokens)
        parser.removeErrorListeners()
        parser.addErrorListener(_Silent())
        tree = parser.program()

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "ast")
            viz = ASTVisualizer(parser)
            rendered = viz.generate(tree, output_path=out_path, fmt="svg")
            if rendered and os.path.isfile(rendered):
                with open(rendered, "r", encoding="utf-8") as f:
                    return f.read()
    except Exception:
        pass
    return None


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "127.0.0.1")
    print(f"\n  🚀 Compiscript IDE started internally on port {port}")
    if host == "0.0.0.0":
        print(f"  🐳 Docker Mode: Please open 👉 http://127.0.0.1:8080 👈 in your browser (if you mapped -p 8080:{port})\n")
    else:
        print(f"  👉 Open: http://127.0.0.1:{port}\n")
    app.run(host=host, port=port, debug=True)
