"""Pipeline de compilación: .cps -> TAC. Lo usan el CLI, el IDE y los tests.

Etapas: parser -> análisis semántico -> layout de clases -> generador de TAC -> printer.
Si hay errores sintácticos o semánticos se detiene antes de generar código.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from antlr4 import CommonTokenStream, InputStream
from antlr4.error.ErrorListener import ErrorListener

from .generated.CompiscriptLexer import CompiscriptLexer
from .generated.CompiscriptParser import CompiscriptParser
from .ir import memory_layout
from .ir.printer import print_program
from .ir.tac_generator import TACGenerator
from .semantic import SemanticAnalyzer


@dataclass
class CompileResult:
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    tac_text: str | None = None
    tac_text_addresses: str | None = None
    program: Any | None = None  # ir.program.TACProgram
    symbol_table: Any | None = None  # semantic.symbol_table.SymbolTable
    analyzer: Any | None = None  # semantic.SemanticAnalyzer


class _SyntaxErrorCollector(ErrorListener):
    def __init__(self) -> None:
        super().__init__()
        self.errors: list[str] = []

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):  # noqa: N802 (API de antlr4)
        self.errors.append(f"[ERROR] Line {line}:{column} — {msg}")


def compile(source: str, source_name: str = "<input>") -> CompileResult:
    """Compila código fuente Compiscript a TAC."""
    input_stream = InputStream(source)
    input_stream.name = source_name

    lexer = CompiscriptLexer(input_stream)
    lexer.removeErrorListeners()
    syntax_collector = _SyntaxErrorCollector()
    lexer.addErrorListener(syntax_collector)
    token_stream = CommonTokenStream(lexer)

    parser = CompiscriptParser(token_stream)
    parser.removeErrorListeners()
    parser.addErrorListener(syntax_collector)
    tree = parser.program()

    if syntax_collector.errors:
        return CompileResult(ok=False, errors=syntax_collector.errors)

    analyzer = SemanticAnalyzer()
    analyzer.visit(tree)

    errors = [str(e) for e in analyzer.errors.errors_only()]
    warnings = [str(e) for e in analyzer.errors.warnings_only()]
    if errors:
        return CompileResult(ok=False, errors=errors, warnings=warnings,
                              symbol_table=analyzer.symbols, analyzer=analyzer)

    memory_layout.compute_class_layouts(analyzer.class_registry)

    generator = TACGenerator(analyzer)
    program = generator.generate(tree)

    tac_text = print_program(program, addresses=False)
    tac_text_addresses = print_program(program, addresses=True)

    return CompileResult(
        ok=True,
        errors=errors,
        warnings=warnings,
        tac_text=tac_text,
        tac_text_addresses=tac_text_addresses,
        program=program,
        symbol_table=analyzer.symbols,
        analyzer=analyzer,
    )
