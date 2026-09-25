"""Ejecuta un TACProgram; usado como oráculo en los tests de ejecución (los más fuertes,
CLAUDE.md §7) y por el botón "Ejecutar" del IDE.

Modelo de memoria: cada frame de función es un dict `{offset_o_clave_temporal: valor}`.
Arreglos y objetos son listas de Python indexadas por `offset // WORD_SIZE` (slot 0 = longitud
en arreglos, o el ClassType actuando como "puntero a vtable" en objetos) — así la aritmética de
offsets en bytes que emite tac_generator (`ARRAY_HEADER_SIZE`, `field_offset`) se traduce
directamente a un índice de lista. Ticket C-4.
"""
from __future__ import annotations

import operator
from typing import Any, Dict, List, Optional

from ..semantic.symbol_table import WORD_SIZE
from .instructions import OpCode, Quad
from .operands import Const, FramePointer, Label, Operand, StrConst, Temp, VarRef
from .program import TACFunction, TACProgram


class CompiscriptRuntimeError(Exception):
    """Una excepción lanzada por el programa Compiscript en ejecución (THROW, boundscheck
    fallido). `value` es el valor capturado por `get_exception` en el `catch`."""

    def __init__(self, value: Any):
        super().__init__(str(value))
        self.value = value


_ARITH = {
    OpCode.ADD: operator.add,
    OpCode.SUB: operator.sub,
    OpCode.MUL: operator.mul,
    OpCode.MOD: operator.mod,
}


def _div(a, b):
    if isinstance(a, int) and isinstance(b, int):
        q = a / b
        return int(q) if q >= 0 else -int(-q)  # trunca hacia cero, no floor
    return a / b


_ARITH[OpCode.DIV] = _div

_REL_VALUE = {
    OpCode.EQ: operator.eq, OpCode.NE: operator.ne, OpCode.LT: operator.lt,
    OpCode.LE: operator.le, OpCode.GT: operator.gt, OpCode.GE: operator.ge,
}
_REL_JUMP = {
    OpCode.IF_LT: operator.lt, OpCode.IF_LE: operator.le, OpCode.IF_GT: operator.gt,
    OpCode.IF_GE: operator.ge, OpCode.IF_EQ: operator.eq, OpCode.IF_NE: operator.ne,
}


class Interpreter:
    def __init__(self, program: TACProgram, class_registry: Optional[dict] = None):
        self.program = program
        self.class_registry = class_registry or {}
        self.functions: Dict[str, TACFunction] = {f.name: f for f in program.functions}
        self.globals: Dict[int, Any] = {}
        self.output: List[str] = []
        self._pending_params: List[Any] = []
        self._pending_exception: Any = None

    def run(self) -> str:
        self.globals = {}
        self.output = []
        self._pending_params = []
        self._pending_exception = None
        main = self.functions.get("main")
        if main is not None:
            self._run_function(main, {})
        return "".join(line + "\n" for line in self.output)

    # ------------------------------------------------------------------
    # Acceso a memoria
    # ------------------------------------------------------------------

    def _get(self, operand: Operand, frame: dict) -> Any:
        if operand is None:
            return None
        if isinstance(operand, FramePointer):
            return frame
        if isinstance(operand, Const):
            return operand.value
        if isinstance(operand, StrConst):
            return self.program.strings.get(operand.label, "")
        if isinstance(operand, Temp):
            return frame.get(("t", operand.index), 0)
        if isinstance(operand, VarRef):
            sym = operand.symbol
            if sym.storage == "global":
                return self.globals.get(sym.offset, 0)
            return frame.get(sym.offset, 0)
        if isinstance(operand, Label):
            return operand.name
        raise TypeError(f"operando no soportado en tiempo de ejecucion: {operand!r}")

    def _set(self, operand: Operand, frame: dict, value: Any) -> None:
        if isinstance(operand, Temp):
            frame[("t", operand.index)] = value
        elif isinstance(operand, VarRef):
            sym = operand.symbol
            if sym.storage == "global":
                self.globals[sym.offset] = value
            else:
                frame[sym.offset] = value
        else:
            raise TypeError(f"destino invalido: {operand!r}")

    def _resolve_static_frame(self, frame: dict, k: int) -> dict:
        target = frame
        for _ in range(k):
            target = target[-4]
        return target

    def _to_str(self, value: Any) -> str:
        if isinstance(value, list):
            return "<array>" if (value and isinstance(value[0], int)) else "<object>"
        return str(value)

    # ------------------------------------------------------------------
    # Llamadas
    # ------------------------------------------------------------------

    def _invoke(self, label: str) -> Any:
        func = self.functions.get(label)
        if func is None:
            raise RuntimeError(f"funcion no encontrada: {label}")
        params = self._pending_params
        self._pending_params = []
        new_frame: dict = {}
        if func.has_static_link and params:
            new_frame[-4] = params[0]
            params = params[1:]
        offset = 8
        for value in params:
            new_frame[offset] = value
            offset += WORD_SIZE
        return self._run_function(func, new_frame)

    # ------------------------------------------------------------------
    # Bucle de ejecución de una función
    # ------------------------------------------------------------------

    def _run_function(self, func: TACFunction, frame: dict) -> Any:
        label_index = {q.result.name: i for i, q in enumerate(func.quads) if q.op == OpCode.LABEL}
        handler_stack: List[str] = []
        pc = 0
        n = len(func.quads)
        while pc < n:
            q = func.quads[pc]
            if q.op == OpCode.TRY_BEGIN:
                handler_stack.append(q.result.name)
                pc += 1
                continue
            if q.op == OpCode.TRY_END:
                if handler_stack:
                    handler_stack.pop()
                pc += 1
                continue
            try:
                outcome = self._exec(q, frame)
            except CompiscriptRuntimeError as exc:
                if handler_stack:
                    l_catch = handler_stack.pop()
                    self._pending_exception = exc.value
                    pc = label_index[l_catch]
                    continue
                raise
            if outcome is None:
                pc += 1
            elif outcome[0] == "goto":
                pc = label_index[outcome[1]]
            else:  # ('return', value)
                return outcome[1]
        return None

    def _exec(self, q: Quad, frame: dict):
        op = q.op
        get, set_ = self._get, self._set

        if op == OpCode.LABEL:
            return None
        if op == OpCode.ASSIGN:
            set_(q.result, frame, get(q.arg1, frame))
            return None
        if op in _ARITH:
            set_(q.result, frame, _ARITH[op](get(q.arg1, frame), get(q.arg2, frame)))
            return None
        if op in _REL_VALUE:
            set_(q.result, frame, 1 if _REL_VALUE[op](get(q.arg1, frame), get(q.arg2, frame)) else 0)
            return None
        if op == OpCode.NEG:
            set_(q.result, frame, -get(q.arg1, frame))
            return None
        if op == OpCode.NOT:
            set_(q.result, frame, 0 if get(q.arg1, frame) else 1)
            return None
        if op == OpCode.GOTO:
            return ("goto", q.result.name)
        if op == OpCode.IF:
            return ("goto", q.result.name) if get(q.arg1, frame) else None
        if op == OpCode.IFFALSE:
            return ("goto", q.result.name) if not get(q.arg1, frame) else None
        if op in _REL_JUMP:
            cond = _REL_JUMP[op](get(q.arg1, frame), get(q.arg2, frame))
            return ("goto", q.result.name) if cond else None
        if op == OpCode.PARAM:
            self._pending_params.append(get(q.arg1, frame))
            return None
        if op == OpCode.CALL:
            value = self._invoke(q.arg1.name)
            if q.result is not None:
                set_(q.result, frame, value)
            return None
        if op == OpCode.VCALL:
            obj = get(q.arg1, frame)
            slot = q.arg2.value
            class_type = obj[0]
            label = class_type.vtable[slot]
            value = self._invoke(label)
            if q.result is not None:
                set_(q.result, frame, value)
            return None
        if op == OpCode.RETURN:
            return ("return", get(q.arg1, frame) if q.arg1 is not None else None)
        if op == OpCode.LOAD:
            base = get(q.arg1, frame)
            off = int(get(q.arg2, frame))
            set_(q.result, frame, base[off // WORD_SIZE])
            return None
        if op == OpCode.STORE:
            base = get(q.arg1, frame)
            off = int(get(q.arg2, frame))
            base[off // WORD_SIZE] = get(q.result, frame)
            return None
        if op == OpCode.NEWARRAY:
            length = int(get(q.arg1, frame))
            set_(q.result, frame, [length] + [0] * length)
            return None
        if op == OpCode.LEN:
            base = get(q.arg1, frame)
            set_(q.result, frame, base[0])
            return None
        if op == OpCode.BOUNDS:
            base = get(q.arg1, frame)
            idx = int(get(q.arg2, frame))
            if not (0 <= idx < base[0]):
                raise CompiscriptRuntimeError(f"indice fuera de rango: {idx}")
            return None
        if op == OpCode.NEW:
            class_name = q.arg1.name
            size = int(get(q.arg2, frame))
            class_type = self.class_registry.get(class_name)
            n_slots = max(size // WORD_SIZE, 1)
            set_(q.result, frame, [class_type] + [0] * (n_slots - 1))
            return None
        if op == OpCode.CONCAT:
            set_(q.result, frame, self._to_str(get(q.arg1, frame)) + self._to_str(get(q.arg2, frame)))
            return None
        if op == OpCode.TOSTR:
            set_(q.result, frame, self._to_str(get(q.arg1, frame)))
            return None
        if op == OpCode.PRINT:
            self.output.append(self._to_str(get(q.arg1, frame)))
            return None
        if op == OpCode.GETEXC:
            set_(q.result, frame, self._pending_exception)
            return None
        if op == OpCode.THROW:
            raise CompiscriptRuntimeError(get(q.arg1, frame))
        if op == OpCode.UPLOAD:
            k = q.arg1.value
            off = q.arg2.value
            target = self._resolve_static_frame(frame, k)
            set_(q.result, frame, target.get(off, 0))
            return None
        if op == OpCode.UPSTORE:
            k = q.arg1.value
            off = q.arg2.value
            target = self._resolve_static_frame(frame, k)
            target[off] = get(q.result, frame)
            return None
        raise NotImplementedError(f"OpCode no soportado por el interprete: {op}")
