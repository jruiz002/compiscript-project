"""Instrucciones del TAC: OpCode y Quad (cuádruplo)."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional

from .operands import Operand


class OpCode(Enum):
    # Copia
    ASSIGN = auto()
    # Binarias aritméticas
    ADD = auto()
    SUB = auto()
    MUL = auto()
    DIV = auto()
    MOD = auto()
    # Relacionales (producen 1/0 como valor)
    EQ = auto()
    NE = auto()
    LT = auto()
    LE = auto()
    GT = auto()
    GE = auto()
    # Unarias
    NEG = auto()
    NOT = auto()
    # Control de flujo
    GOTO = auto()
    IF = auto()
    IFFALSE = auto()
    IF_LT = auto()
    IF_LE = auto()
    IF_GT = auto()
    IF_GE = auto()
    IF_EQ = auto()
    IF_NE = auto()
    LABEL = auto()
    # Funciones
    FUNC = auto()
    ENDFUNC = auto()
    PARAM = auto()
    CALL = auto()
    VCALL = auto()
    RETURN = auto()
    # Memoria (objetos / arreglos)
    LOAD = auto()
    STORE = auto()
    NEWARRAY = auto()
    LEN = auto()
    BOUNDS = auto()
    NEW = auto()
    # Strings
    CONCAT = auto()
    TOSTR = auto()
    # Salida
    PRINT = auto()
    # Excepciones
    TRY_BEGIN = auto()
    TRY_END = auto()
    GETEXC = auto()
    THROW = auto()
    # Static link (funciones anidadas)
    UPLOAD = auto()
    UPSTORE = auto()


# saltos relacionales: if y relop z goto L
RELATIONAL_JUMPS = {
    OpCode.IF_LT: OpCode.LT,
    OpCode.IF_LE: OpCode.LE,
    OpCode.IF_GT: OpCode.GT,
    OpCode.IF_GE: OpCode.GE,
    OpCode.IF_EQ: OpCode.EQ,
    OpCode.IF_NE: OpCode.NE,
}

# salto contrario de cada uno (para negar una condición)
NEGATED_RELATIONAL = {
    OpCode.IF_LT: OpCode.IF_GE,
    OpCode.IF_LE: OpCode.IF_GT,
    OpCode.IF_GT: OpCode.IF_LE,
    OpCode.IF_GE: OpCode.IF_LT,
    OpCode.IF_EQ: OpCode.IF_NE,
    OpCode.IF_NE: OpCode.IF_EQ,
}

BINARY_ARITH_OPS = {OpCode.ADD, OpCode.SUB, OpCode.MUL, OpCode.DIV, OpCode.MOD}
RELATIONAL_VALUE_OPS = {OpCode.EQ, OpCode.NE, OpCode.LT, OpCode.LE, OpCode.GT, OpCode.GE}


@dataclass
class Quad:
    """Cuádruplo: result = arg1 op arg2."""
    op: OpCode
    arg1: Operand = None
    arg2: Operand = None
    result: Operand = None
    comment: Optional[str] = None

    def __repr__(self) -> str:
        return f"Quad({self.op.name}, {self.arg1!r}, {self.arg2!r}, {self.result!r})"
