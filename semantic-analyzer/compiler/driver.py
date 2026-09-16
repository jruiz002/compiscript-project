#!/usr/bin/env python3
# compiler/driver.py
"""
Compiscript Compiler — CLI entry point.

Usage:
  python compiler/driver.py <source.cps> [--ast] [--symbols] [--ast-out PATH]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GENERATED_DIR = os.path.join(PROJECT_ROOT, "compiler", "generated")

# ANTLR output goes into a subdirectory matching the grammar's package
# Try both locations: flat (compiler/generated/) and nested (compiler/generated/compiler/)
for _path in [GENERATED_DIR, os.path.join(GENERATED_DIR, "compiler")]:
    if os.path.isfile(os.path.join(_path, "CompiscriptLexer.py")):
        sys.path.insert(0, _path)
        break

sys.path.insert(0, PROJECT_ROOT)

from antlr4 import CommonTokenStream, InputStream
from antlr4.error.ErrorListener import ErrorListener

from CompiscriptLexer import CompiscriptLexer
from CompiscriptParser import CompiscriptParser

from compiler.semantic import SemanticAnalyzer
from compiler.ast_visualizer import ASTVisualizer, tree_to_dict
from compiler import symbol_table_viz


class SyntaxErrorCollector(ErrorListener):
    """Collects ANTLR syntax errors without printing them to stderr."""

    def __init__(self):
        super().__init__()
        self.errors = []

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        self.errors.append({
            "message": msg,
            "line": line,
            "column": column,
            "severity": "error",
            "phase": "syntax",
        })


def compile_source(
    source: str,
    source_name: str = "<input>",
    generate_ast: bool = False,
    ast_output: str = None,
) -> dict:
    """
    Compile a Compiscript source string.
    Returns a dict with: errors, warnings, symbol_table, ast (if requested).
    """
    input_stream = InputStream(source)
    input_stream.name = source_name

    # --- Lexing ---
    lexer = CompiscriptLexer(input_stream)
    lexer.removeErrorListeners()
    syntax_collector = SyntaxErrorCollector()
    lexer.addErrorListener(syntax_collector)
    token_stream = CommonTokenStream(lexer)

    # --- Parsing ---
    parser = CompiscriptParser(token_stream)
    parser.removeErrorListeners()
    parser.addErrorListener(syntax_collector)

    tree = parser.program()

    result = {
        "errors": syntax_collector.errors,
        "warnings": [],
        "symbol_table": {},
        "ast": None,
    }

    if syntax_collector.errors:
        # Don't run semantic analysis if syntax is broken
        return result

    # --- Semantic Analysis ---
    analyzer = SemanticAnalyzer()
    analyzer.visit(tree)

    for err in analyzer.errors:
        entry = {
            "message": err.message,
            "line": err.line,
            "column": err.column,
            "severity": err.severity.value,
            "phase": "semantic",
        }
        if err.severity.value == "error":
            result["errors"].append(entry)
        else:
            result["warnings"].append(entry)

    result["symbol_table"] = analyzer.symbols.to_dict()

    # --- AST ---
    if generate_ast:
        result["ast"] = tree_to_dict(tree, parser)

        if ast_output:
            viz = ASTVisualizer(parser)
            path = viz.generate(tree, output_path=ast_output, fmt="svg")
            result["ast_file"] = path

    return result


def main():
    arg_parser = argparse.ArgumentParser(
        description="Compiscript Semantic Analyzer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python compiler/driver.py program.cps
  python compiler/driver.py program.cps --ast
  python compiler/driver.py program.cps --symbols --ast --ast-out output/ast
  python compiler/driver.py program.cps --symbols-out output/symbols
        """,
    )
    arg_parser.add_argument("source", help="Path to a .cps source file")
    arg_parser.add_argument("--ast", action="store_true", help="Generate and print AST as JSON")
    arg_parser.add_argument("--ast-out", metavar="PATH", help="Render AST as SVG to this path")
    arg_parser.add_argument("--symbols", action="store_true", help="Print symbol table as JSON")
    arg_parser.add_argument("--symbols-out", metavar="PATH", help="Render symbol table to this path (.svg or .png)")
    arg_parser.add_argument("--json", action="store_true", help="Output everything as JSON")
    args = arg_parser.parse_args()

    if not os.path.isfile(args.source):
        print(f"Error: File not found: {args.source}", file=sys.stderr)
        sys.exit(1)

    with open(args.source, encoding="utf-8") as f:
        source = f.read()

    result = compile_source(
        source,
        source_name=args.source,
        generate_ast=args.ast or bool(args.ast_out),
        ast_output=args.ast_out,
    )

    if args.json:
        print(json.dumps(result, indent=2, default=str))
        sys.exit(1 if result["errors"] else 0)

    # Human-readable output
    all_issues = result["errors"] + result["warnings"]
    if not all_issues:
        print(f"\033[32m✓ No errors found in '{args.source}'\033[0m")
    else:
        for issue in sorted(all_issues, key=lambda e: (e["line"], e["column"])):
            prefix = "\033[31m[ERROR]\033[0m" if issue["severity"] == "error" else "\033[33m[WARN]\033[0m"
            phase = f"[{issue['phase']}]"
            print(f"{prefix} {phase} Line {issue['line']}:{issue['column']} — {issue['message']}")

        errors = result["errors"]
        warnings = result["warnings"]
        print(f"\n{len(errors)} error(s), {len(warnings)} warning(s)")

    if args.symbols:
        print("\n--- Symbol Table ---")
        print(json.dumps(result["symbol_table"], indent=2))

    if args.symbols_out:
        base, ext = os.path.splitext(args.symbols_out)
        fmt = ext.lstrip(".").lower() or "svg"
        path = symbol_table_viz.generate(result["symbol_table"], output_path=base, fmt=fmt, dpi=150)
        msg = f"\nSymbol table rendered to: {path}" if path else "\nSymbol table not rendered (graphviz unavailable)"
        print(msg)

    if args.ast and result.get("ast"):
        print("\n--- AST ---")
        print(json.dumps(result["ast"], indent=2))

    if result.get("ast_file"):
        print(f"\nAST rendered to: {result['ast_file']}")

    sys.exit(1 if result["errors"] else 0)


if __name__ == "__main__":
    main()
