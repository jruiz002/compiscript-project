"""CLI de Compiscript Fase 2: compila un archivo .cps a TAC.

Uso:
    python -m compiscript.main archivo.cps [--out archivo.tac] [--addresses]
                                            [--dump-symbols] [--run]
"""
from __future__ import annotations

import argparse
import sys

from . import pipeline
from .ir.interpreter import CompiscriptRuntimeError, Interpreter


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="compiscript", description=__doc__)
    parser.add_argument("source", help="Archivo fuente .cps")
    parser.add_argument("--out", metavar="PATH", help="Ruta de salida para el .tac generado")
    parser.add_argument(
        "--addresses",
        action="store_true",
        help="Imprime el TAC con direcciones (fp[-8], gp[4]) en vez de nombres simbólicos",
    )
    parser.add_argument(
        "--dump-symbols",
        action="store_true",
        help="Imprime la tabla de símbolos con registros de activación",
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="Ejecuta el TAC generado con el intérprete y muestra la salida de print",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)

    with open(args.source, encoding="utf-8") as f:
        source = f.read()

    result = pipeline.compile(source, source_name=args.source)

    if not result.ok:
        for error in result.errors:
            print(error, file=sys.stderr)
        return 1

    tac_text = result.tac_text_addresses if args.addresses else result.tac_text

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(tac_text or "")
    else:
        print(tac_text)

    if args.dump_symbols and result.symbol_table is not None:
        print(result.symbol_table.dump())

    if args.run:
        interpreter = Interpreter(result.program, result.analyzer.class_registry)
        try:
            print(interpreter.run(), end="")
        except CompiscriptRuntimeError as exc:
            print(f"Excepción no capturada: {exc.value}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
