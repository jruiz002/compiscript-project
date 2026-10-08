"""Convierte un TACProgram a texto, con nombres o con direcciones (fp[-8], gp[4])."""
from __future__ import annotations

from .instructions import OpCode, Quad
from .operands import Operand, VarRef
from .program import TACProgram


def _fmt(operand: Operand, addresses: bool) -> str:
    if operand is None:
        return ""
    if isinstance(operand, VarRef) and addresses:
        return operand.with_addresses()
    return str(operand)


def _format_quad(q: Quad, addresses: bool) -> str:
    a1 = _fmt(q.arg1, addresses)
    a2 = _fmt(q.arg2, addresses)
    r = _fmt(q.result, addresses)
    op = q.op

    if op == OpCode.LABEL:
        line = f"{r}:"
    elif op == OpCode.ASSIGN:
        line = f"{r} = {a1}"
    elif op in (OpCode.ADD, OpCode.SUB, OpCode.MUL, OpCode.DIV, OpCode.MOD):
        symbol = {OpCode.ADD: "+", OpCode.SUB: "-", OpCode.MUL: "*", OpCode.DIV: "/", OpCode.MOD: "%"}[op]
        line = f"{r} = {a1} {symbol} {a2}"
    elif op in (OpCode.EQ, OpCode.NE, OpCode.LT, OpCode.LE, OpCode.GT, OpCode.GE):
        symbol = {OpCode.EQ: "==", OpCode.NE: "!=", OpCode.LT: "<", OpCode.LE: "<=",
                  OpCode.GT: ">", OpCode.GE: ">="}[op]
        line = f"{r} = {a1} {symbol} {a2}"
    elif op == OpCode.NEG:
        line = f"{r} = -{a1}"
    elif op == OpCode.NOT:
        line = f"{r} = !{a1}"
    elif op == OpCode.GOTO:
        line = f"goto {r}"
    elif op == OpCode.IF:
        line = f"if {a1} goto {r}"
    elif op == OpCode.IFFALSE:
        line = f"ifFalse {a1} goto {r}"
    elif op in (OpCode.IF_LT, OpCode.IF_LE, OpCode.IF_GT, OpCode.IF_GE, OpCode.IF_EQ, OpCode.IF_NE):
        symbol = {OpCode.IF_LT: "<", OpCode.IF_LE: "<=", OpCode.IF_GT: ">", OpCode.IF_GE: ">=",
                  OpCode.IF_EQ: "==", OpCode.IF_NE: "!="}[op]
        line = f"if {a1} {symbol} {a2} goto {r}"
    elif op == OpCode.PARAM:
        line = f"param {a1}"
    elif op == OpCode.CALL:
        line = f"{r} = call {a1}, {a2}" if q.result is not None else f"call {a1}, {a2}"
    elif op == OpCode.VCALL:
        line = f"{r} = vcall {a1}, {a2}" if q.result is not None else f"vcall {a1}, {a2}"
    elif op == OpCode.RETURN:
        line = f"return {a1}" if q.arg1 is not None else "return"
    elif op == OpCode.LOAD:
        line = f"{r} = {a1}[{a2}]"
    elif op == OpCode.STORE:
        line = f"{a1}[{a2}] = {r}"
    elif op == OpCode.NEWARRAY:
        line = f"{r} = newarray {a1}"
    elif op == OpCode.LEN:
        line = f"{r} = len {a1}"
    elif op == OpCode.BOUNDS:
        line = f"boundscheck {a1}, {a2}"
    elif op == OpCode.NEW:
        line = f"{r} = new {a1}, {a2}"
    elif op == OpCode.CONCAT:
        line = f"{r} = concat {a1}, {a2}"
    elif op == OpCode.TOSTR:
        line = f"{r} = tostr {a1}"
    elif op == OpCode.PRINT:
        line = f"print {a1}"
    elif op == OpCode.TRY_BEGIN:
        line = f"try_begin {r}"
    elif op == OpCode.TRY_END:
        line = "try_end"
    elif op == OpCode.GETEXC:
        line = f"{r} = get_exception"
    elif op == OpCode.THROW:
        line = f"throw {a1}"
    elif op == OpCode.UPLOAD:
        line = f"{r} = up {a1}, {a2}"
    elif op == OpCode.UPSTORE:
        line = f"up {a1}, {a2} = {r}"
    else:
        line = f"; instruccion desconocida: {q!r}"

    indent = "" if op == OpCode.LABEL else "    "
    if q.comment:
        return f"{indent}{line}    # {q.comment}"
    return f"{indent}{line}"


def print_program(program: TACProgram, addresses: bool = False) -> str:
    """Con addresses=True imprime fp[off]/gp[off] en vez de los nombres."""
    lines: list[str] = []

    if program.strings:
        lines.append("; --- sección de datos ---")
        for label, value in program.strings.items():
            lines.append(f'{label}: "{value}"')
        lines.append("")

    for func in program.functions:
        lines.append(f"func {func.name}, {func.frame_size}")
        for quad in func.quads:
            lines.append(_format_quad(quad, addresses))
        lines.append(f"endfunc {func.name}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
