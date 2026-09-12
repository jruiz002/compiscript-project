#!/usr/bin/env python3
# program/Driver.py
"""
Compiscript Playground Driver.
Used inside the Docker container for quick testing.

Usage (inside Docker):
  antlr -Dlanguage=Python3 Compiscript.g4   # generate parser (flat output)
  python3 Driver.py program.cps             # run semantic analysis
"""
import sys
import os

PROGRAM_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(PROGRAM_DIR, "..")

# Generated files may be in the same directory (Docker context) or in compiler/generated
for _p in [
    PROGRAM_DIR,
    os.path.join(PROJECT_ROOT, "compiler", "generated"),
    os.path.join(PROJECT_ROOT, "compiler", "generated", "compiler"),
]:
    if os.path.isfile(os.path.join(_p, "CompiscriptLexer.py")):
        sys.path.insert(0, os.path.abspath(_p))
        break

sys.path.insert(0, PROJECT_ROOT)

from antlr4 import CommonTokenStream, FileStream
from antlr4.error.ErrorListener import ErrorListener

from CompiscriptLexer import CompiscriptLexer
from CompiscriptParser import CompiscriptParser

from compiler.semantic import SemanticAnalyzer


class SyntaxErrorListener(ErrorListener):
    def __init__(self):
        super().__init__()
        self.errors = []

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        self.errors.append(f"Syntax Error at {line}:{column} — {msg}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 Driver.py <file.cps>")
        sys.exit(1)

    source_file = sys.argv[1]
    if not os.path.isfile(source_file):
        print(f"File not found: {source_file}")
        sys.exit(1)

    input_stream = FileStream(source_file, encoding="utf-8")
    lexer = CompiscriptLexer(input_stream)
    token_stream = CommonTokenStream(lexer)

    err_listener = SyntaxErrorListener()
    parser = CompiscriptParser(token_stream)
    parser.removeErrorListeners()
    parser.addErrorListener(err_listener)

    tree = parser.program()

    if err_listener.errors:
        for e in err_listener.errors:
            print(e)
        sys.exit(1)

    analyzer = SemanticAnalyzer()
    analyzer.visit(tree)

    if analyzer.errors.has_errors():
        for err in analyzer.errors:
            print(str(err))
        sys.exit(1)

    # No output = success (per assignment spec)


if __name__ == "__main__":
    main()
