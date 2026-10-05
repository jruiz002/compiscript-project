"""Visitor principal que recorre el AST (hereda CompiscriptVisitor) y emite TAC.

No vuelve a hacer análisis semántico: solo lee de `node_types` / `scope_of` / `symbol_of` y de
la `SymbolTable`, ya llenadas por `SemanticAnalyzer` (CLAUDE.md §4). Cubre expresiones/
variables/print (B-4, B-5), funciones y llamadas (B-6), control de flujo (C-1, C-2), arreglos
y strings (B-7, B-8), clases/this/new/vcall (A-3), funciones anidadas (A-5) y try/catch (C-3).

Reglas de reciclaje de temporales (docs/TAC_LANGUAGE.md §5): cada `_gen_*` libera los
operandos que ya no necesita ANTES de pedir un temporal destino, así el destino puede reusar
el índice recién liberado. Cada sentencia de nivel superior termina con `temps.live == 0`
(verificado por un assert en `_gen_statement`).

Supuestos documentados en docs/TAC_LANGUAGE.md §6: solo se soporta invocar una función
anidada directamente desde su padre léxico inmediato (se le pasa siempre el `fp` actual como
static link); no hay funciones de primera clase (no se puede llamar a través de una variable).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from ..semantic.generated_imports import CompiscriptParser
from ..semantic.symbol_table import ActivationRecord, Symbol, SymbolKind, WORD_SIZE
from ..semantic.types import ClassType, FunctionType, TypeKind, CompiscriptType, STRING, INTEGER
from .instructions import NEGATED_RELATIONAL, OpCode, Quad
from .labels import LabelGenerator
from .memory_layout import ARRAY_HEADER_SIZE
from .operands import FP, Const, Label, Operand, StrConst, Temp, VarRef
from .program import TACFunction, TACProgram
from .temp_allocator import TempAllocator

_MULT_OPS = {"*": OpCode.MUL, "/": OpCode.DIV, "%": OpCode.MOD}
_REL_OPS = {"<": OpCode.LT, "<=": OpCode.LE, ">": OpCode.GT, ">=": OpCode.GE}
_EQ_OPS = {"==": OpCode.EQ, "!=": OpCode.NE}
_REL_JUMPS = {"<": OpCode.IF_LT, "<=": OpCode.IF_LE, ">": OpCode.IF_GT, ">=": OpCode.IF_GE}
_EQ_JUMPS = {"==": OpCode.IF_EQ, "!=": OpCode.IF_NE}


@dataclass
class LoopContext:
    break_label: str
    continue_label: Optional[str]


def _is_string_type(t: Optional[CompiscriptType]) -> bool:
    return t is not None and t.kind == TypeKind.STRING


def _is_bool_type(t: Optional[CompiscriptType]) -> bool:
    return t is not None and t.kind == TypeKind.BOOLEAN


class TACGenerator:
    def __init__(self, analyzer) -> None:
        self.types = analyzer.node_types
        self.scope_of = analyzer.scope_of
        self.symbol_of = analyzer.symbol_of
        self.class_registry = analyzer.class_registry
        self.program = TACProgram()
        self.labels = LabelGenerator()
        self.loop_stack: List[LoopContext] = []
        self.current_function: TACFunction
        self.temps: TempAllocator
        self._function_stack: list = []
        self._ar_chain: List[ActivationRecord] = []

    # ------------------------------------------------------------------
    # Entrada
    # ------------------------------------------------------------------

    def generate(self, tree) -> TACProgram:
        self.current_function = self.program.add_function(TACFunction(name="main"))
        self.temps = TempAllocator()
        main_ar = ActivationRecord(function_name="main", has_static_link=False)
        self._ar_chain = [main_ar]
        self.loop_stack = []

        for stmt in tree.statement():
            self._gen_statement(stmt)

        self._emit(OpCode.RETURN)
        main_ar.finalize(self.temps.max_used)
        self.current_function.frame_size = main_ar.frame_size
        return self.program

    # ------------------------------------------------------------------
    # Helpers de emisión
    # ------------------------------------------------------------------

    def _emit(self, op: OpCode, arg1: Operand = None, arg2: Operand = None,
              result: Operand = None, comment: Optional[str] = None) -> Quad:
        return self.current_function.emit(Quad(op, arg1, arg2, result, comment))

    def _leaf(self, value: Operand, dest: Optional[Operand]) -> Operand:
        """Un operando ya calculado (literal/variable) que opcionalmente debe copiarse a
        `dest` (optimización de destino: si no hay dest, no se emite ninguna instrucción)."""
        if dest is None or value == dest:
            return dest if dest is not None else value
        self._emit(OpCode.ASSIGN, value, None, dest)
        self.temps.release(value)
        return dest

    def _static_link_depth(self, symbol: Symbol) -> int:
        for depth, ar in enumerate(reversed(self._ar_chain)):
            if any(s is symbol for s in ar.params) or any(s is symbol for s in ar.locals):
                return depth
        return 0

    def _read_var(self, symbol: Symbol) -> Operand:
        if symbol.storage in ("local", "param"):
            depth = self._static_link_depth(symbol)
            if depth > 0:
                t = self.temps.new_temp()
                self._emit(OpCode.UPLOAD, Const(depth), Const(symbol.offset), t,
                           comment=f"up {symbol.name}")
                return t
        return VarRef(symbol)

    def _write_var(self, symbol: Symbol, value: Operand) -> None:
        if symbol.storage in ("local", "param"):
            depth = self._static_link_depth(symbol)
            if depth > 0:
                self._emit(OpCode.UPSTORE, Const(depth), Const(symbol.offset), value,
                           comment=f"up {symbol.name} =")
                return
        self._emit(OpCode.ASSIGN, value, None, VarRef(symbol))

    # ==================================================================
    # Sentencias
    # ==================================================================

    def _gen_statement(self, ctx: CompiscriptParser.StatementContext) -> None:
        self._dispatch_statement(ctx)
        assert self.temps.live == 0, (
            f"quedaron {self.temps.live} temporales vivos tras la sentencia en linea "
            f"{getattr(ctx.start, 'line', '?')}"
        )

    def _dispatch_statement(self, ctx: CompiscriptParser.StatementContext) -> None:
        if ctx.variableDeclaration():
            self._gen_variable_declaration(ctx.variableDeclaration())
        elif ctx.constantDeclaration():
            self._gen_variable_declaration(ctx.constantDeclaration())
        elif ctx.assignment():
            self._gen_assignment_statement(ctx.assignment())
        elif ctx.functionDeclaration():
            self._gen_function(ctx.functionDeclaration())
        elif ctx.classDeclaration():
            self._gen_class(ctx.classDeclaration())
        elif ctx.printStatement():
            self._gen_print(ctx.printStatement())
        elif ctx.block():
            self._gen_block(ctx.block())
        elif ctx.ifStatement():
            self._gen_if(ctx.ifStatement())
        elif ctx.whileStatement():
            self._gen_while(ctx.whileStatement())
        elif ctx.doWhileStatement():
            self._gen_do_while(ctx.doWhileStatement())
        elif ctx.forStatement():
            self._gen_for(ctx.forStatement())
        elif ctx.foreachStatement():
            self._gen_foreach(ctx.foreachStatement())
        elif ctx.tryCatchStatement():
            self._gen_try_catch(ctx.tryCatchStatement())
        elif ctx.switchStatement():
            self._gen_switch(ctx.switchStatement())
        elif ctx.breakStatement():
            self._gen_break()
        elif ctx.continueStatement():
            self._gen_continue()
        elif ctx.returnStatement():
            self._gen_return(ctx.returnStatement())
        elif ctx.expressionStatement():
            value = self._gen_expr(ctx.expressionStatement().expression())
            self.temps.release(value)

    def _gen_variable_declaration(self, ctx) -> None:
        sym = self.symbol_of.get(ctx)
        if sym is None or sym.storage == "field":
            return
        if isinstance(ctx, CompiscriptParser.ConstantDeclarationContext):
            self._gen_expr(ctx.expression(), dest=VarRef(sym))
        elif ctx.initializer():
            self._gen_expr(ctx.initializer().expression(), dest=VarRef(sym))

    def _gen_assignment_statement(self, ctx: CompiscriptParser.AssignmentContext) -> None:
        identifier = ctx.Identifier()
        expressions = ctx.expression()
        if identifier and len(expressions) == 1:
            sym = self.symbol_of.get(ctx)
            if sym is None:
                value = self._gen_expr(expressions[0])
                self.temps.release(value)
                return
            if sym.storage in ("local", "param") and self._static_link_depth(sym) > 0:
                value = self._gen_expr(expressions[0])
                self._write_var(sym, value)
                self.temps.release(value)
            else:
                self._gen_expr(expressions[0], dest=VarRef(sym))
        else:
            obj = self._gen_expr(expressions[0])
            obj_type = self.types.get(expressions[0])
            value = self._gen_expr(expressions[1])
            attr = identifier.getText()
            offset = obj_type.field_offset(attr) if isinstance(obj_type, ClassType) else 0
            self._emit(OpCode.STORE, obj, Const(offset or 0), value, comment=f".{attr}")
            self.temps.release(obj)
            self.temps.release(value)

    def _gen_print(self, ctx: CompiscriptParser.PrintStatementContext) -> None:
        value = self._gen_expr(ctx.expression())
        if _is_bool_type(self.types.get(ctx.expression())):
            value = self._bool_to_str(value)
        self._emit(OpCode.PRINT, value)
        self.temps.release(value)

    def _gen_block(self, ctx: CompiscriptParser.BlockContext) -> None:
        for stmt in ctx.statement():
            self._gen_statement(stmt)

    def _gen_if(self, ctx: CompiscriptParser.IfStatementContext) -> None:
        blocks = ctx.block()
        l_false = self.labels.new_label()
        has_else = len(blocks) > 1
        l_end = self.labels.new_label() if has_else else None
        self._gen_cond(ctx.expression(), None, l_false)
        self._gen_block(blocks[0])
        if has_else:
            self._emit(OpCode.GOTO, None, None, Label(l_end))
        self._emit(OpCode.LABEL, None, None, Label(l_false))
        if has_else:
            self._gen_block(blocks[1])
            self._emit(OpCode.LABEL, None, None, Label(l_end))

    def _gen_while(self, ctx: CompiscriptParser.WhileStatementContext) -> None:
        l_cond = self.labels.new_label()
        l_end = self.labels.new_label()
        self._emit(OpCode.LABEL, None, None, Label(l_cond))
        self._gen_cond(ctx.expression(), None, l_end)
        self.loop_stack.append(LoopContext(l_end, l_cond))
        self._gen_block(ctx.block())
        self.loop_stack.pop()
        self._emit(OpCode.GOTO, None, None, Label(l_cond))
        self._emit(OpCode.LABEL, None, None, Label(l_end))

    def _gen_do_while(self, ctx: CompiscriptParser.DoWhileStatementContext) -> None:
        l_start = self.labels.new_label()
        l_cond = self.labels.new_label()
        l_end = self.labels.new_label()
        self._emit(OpCode.LABEL, None, None, Label(l_start))
        self.loop_stack.append(LoopContext(l_end, l_cond))
        self._gen_block(ctx.block())
        self.loop_stack.pop()
        self._emit(OpCode.LABEL, None, None, Label(l_cond))
        self._gen_cond(ctx.expression(), l_start, None)
        self._emit(OpCode.LABEL, None, None, Label(l_end))

    def _gen_for(self, ctx: CompiscriptParser.ForStatementContext) -> None:
        if ctx.variableDeclaration():
            self._gen_variable_declaration(ctx.variableDeclaration())
        elif ctx.assignment():
            self._gen_assignment_statement(ctx.assignment())
        expressions = ctx.expression()
        l_cond = self.labels.new_label()
        l_update = self.labels.new_label()
        l_end = self.labels.new_label()
        self._emit(OpCode.LABEL, None, None, Label(l_cond))
        if expressions:
            self._gen_cond(expressions[0], None, l_end)
        self.loop_stack.append(LoopContext(l_end, l_update))
        self._gen_block(ctx.block())
        self.loop_stack.pop()
        self._emit(OpCode.LABEL, None, None, Label(l_update))
        if len(expressions) > 1:
            value = self._gen_expr(expressions[1])
            self.temps.release(value)
        self._emit(OpCode.GOTO, None, None, Label(l_cond))
        self._emit(OpCode.LABEL, None, None, Label(l_end))

    def _new_hidden_local(self, name_hint: str) -> "VarRef":
        """Local oculto (no declarado por el usuario) para estado que debe sobrevivir toda
        la duración de un ciclo (p.ej. índice/longitud/base de un foreach). A diferencia de
        un Temp, una variable local NO dispara el assert de `temps.live == 0` por sentencia,
        que solo vigila temporales de expresión de vida corta (docs/TAC_LANGUAGE.md §5)."""
        ar = self._ar_chain[-1]
        sym = Symbol(name=name_hint, kind=SymbolKind.VARIABLE, data_type=INTEGER,
                     line=0, column=0, scope_level=0)
        ar.allocate_local(sym)
        return VarRef(sym)

    def _gen_foreach(self, ctx: CompiscriptParser.ForeachStatementContext) -> None:
        array_value = self._gen_expr(ctx.expression())
        ar = self._ar_chain[-1]
        cursor = ar.save_cursor()

        array_local = self._new_hidden_local("__arr")
        self._emit(OpCode.ASSIGN, array_value, None, array_local)
        self.temps.release(array_value)

        index = self._new_hidden_local("__idx")
        length = self._new_hidden_local("__len")
        self._emit(OpCode.ASSIGN, Const(0), None, index)
        self._emit(OpCode.LEN, array_local, None, length)

        l_cond = self.labels.new_label()
        l_update = self.labels.new_label()
        l_end = self.labels.new_label()

        item_sym = self.symbol_of.get(ctx)
        item_target = VarRef(item_sym) if item_sym is not None else self._new_hidden_local("__item")

        self._emit(OpCode.LABEL, None, None, Label(l_cond))
        self._emit(OpCode.IF_GE, index, length, Label(l_end))

        byte_off = self.temps.new_temp()
        self._emit(OpCode.MUL, index, Const(WORD_SIZE), byte_off)
        self._emit(OpCode.ADD, byte_off, Const(ARRAY_HEADER_SIZE), byte_off)
        self._emit(OpCode.LOAD, array_local, byte_off, item_target)
        self.temps.release(byte_off)

        self.loop_stack.append(LoopContext(l_end, l_update))
        self._gen_block(ctx.block())
        self.loop_stack.pop()

        self._emit(OpCode.LABEL, None, None, Label(l_update))
        self._emit(OpCode.ADD, index, Const(1), index)
        self._emit(OpCode.GOTO, None, None, Label(l_cond))
        self._emit(OpCode.LABEL, None, None, Label(l_end))

        ar.restore_cursor(cursor)

    def _gen_break(self) -> None:
        if self.loop_stack:
            self._emit(OpCode.GOTO, None, None, Label(self.loop_stack[-1].break_label))

    def _gen_continue(self) -> None:
        for lc in reversed(self.loop_stack):
            if lc.continue_label is not None:
                self._emit(OpCode.GOTO, None, None, Label(lc.continue_label))
                return

    def _gen_return(self, ctx: CompiscriptParser.ReturnStatementContext) -> None:
        if ctx.expression():
            value = self._gen_expr(ctx.expression())
            self._emit(OpCode.RETURN, value)
            self.temps.release(value)
        else:
            self._emit(OpCode.RETURN)

    def _gen_try_catch(self, ctx: CompiscriptParser.TryCatchStatementContext) -> None:
        l_catch = self.labels.new_label()
        l_end = self.labels.new_label()
        self._emit(OpCode.TRY_BEGIN, None, None, Label(l_catch))
        self._gen_block(ctx.block(0))
        self._emit(OpCode.TRY_END)
        self._emit(OpCode.GOTO, None, None, Label(l_end))
        self._emit(OpCode.LABEL, None, None, Label(l_catch))
        catch_sym = self.symbol_of.get(ctx)
        if catch_sym is not None:
            self._emit(OpCode.GETEXC, None, None, VarRef(catch_sym))
        self._gen_block(ctx.block(1))
        self._emit(OpCode.LABEL, None, None, Label(l_end))

    def _gen_switch(self, ctx: CompiscriptParser.SwitchStatementContext) -> None:
        value = self._gen_expr(ctx.expression())
        l_end = self.labels.new_label()
        cases = ctx.switchCase()
        case_labels = [self.labels.new_label() for _ in cases]
        l_default = self.labels.new_label() if ctx.defaultCase() else l_end

        for case_ctx, l_case in zip(cases, case_labels):
            case_value = self._gen_expr(case_ctx.expression())
            self._emit(OpCode.IF_EQ, value, case_value, Label(l_case))
            self.temps.release(case_value)
        self.temps.release(value)
        self._emit(OpCode.GOTO, None, None, Label(l_default))

        self.loop_stack.append(LoopContext(l_end, None))
        for case_ctx, l_case in zip(cases, case_labels):
            self._emit(OpCode.LABEL, None, None, Label(l_case))
            for stmt in case_ctx.statement():
                self._gen_statement(stmt)
        if ctx.defaultCase():
            self._emit(OpCode.LABEL, None, None, Label(l_default))
            for stmt in ctx.defaultCase().statement():
                self._gen_statement(stmt)
        self.loop_stack.pop()
        self._emit(OpCode.LABEL, None, None, Label(l_end))

    # ==================================================================
    # Funciones y clases
    # ==================================================================

    def _gen_function(self, ctx: CompiscriptParser.FunctionDeclarationContext) -> None:
        sym = self.symbol_of.get(ctx)
        func_scope = self.scope_of.get(ctx)
        ar = func_scope.activation_record if func_scope is not None else None
        if sym is None or ar is None:
            return

        tac_func = TACFunction(name=sym.label, has_static_link=ar.has_static_link)
        self.program.add_function(tac_func)

        self._function_stack.append((self.current_function, self.temps, self._ar_chain))
        self.current_function = tac_func
        self.temps = TempAllocator()
        self._ar_chain = self._ar_chain + [ar]

        for stmt in ctx.block().statement():
            self._gen_statement(stmt)
        if not tac_func.quads or tac_func.quads[-1].op != OpCode.RETURN:
            self._emit(OpCode.RETURN)

        tac_func.frame_size = ar.finalize(self.temps.max_used)
        self.current_function, self.temps, self._ar_chain = self._function_stack.pop()

    def _gen_class(self, ctx: CompiscriptParser.ClassDeclarationContext) -> None:
        for member in ctx.classMember():
            fn = member.functionDeclaration()
            if fn:
                self._gen_function(fn)

    # ==================================================================
    # Expresiones
    # ==================================================================

    def _gen_expr(self, ctx, dest: Optional[Operand] = None) -> Operand:
        if isinstance(ctx, CompiscriptParser.ExpressionContext):
            return self._gen_expr(ctx.assignmentExpr(), dest)
        if isinstance(ctx, CompiscriptParser.ExprNoAssignContext):
            return self._gen_expr(ctx.conditionalExpr(), dest)
        if isinstance(ctx, CompiscriptParser.AssignExprContext):
            return self._gen_assign_expr(ctx, dest)
        if isinstance(ctx, CompiscriptParser.PropertyAssignExprContext):
            return self._gen_property_assign_expr(ctx, dest)
        if isinstance(ctx, CompiscriptParser.TernaryExprContext):
            return self._gen_ternary(ctx, dest)
        if isinstance(ctx, CompiscriptParser.LogicalOrExprContext):
            operands = ctx.logicalAndExpr()
            if len(operands) == 1:
                return self._gen_expr(operands[0], dest)
            return self._gen_bool_value(ctx, dest)
        if isinstance(ctx, CompiscriptParser.LogicalAndExprContext):
            operands = ctx.equalityExpr()
            if len(operands) == 1:
                return self._gen_expr(operands[0], dest)
            return self._gen_bool_value(ctx, dest)
        if isinstance(ctx, CompiscriptParser.EqualityExprContext):
            return self._gen_left_assoc_chain(ctx, ctx.relationalExpr(), _EQ_OPS, dest)
        if isinstance(ctx, CompiscriptParser.RelationalExprContext):
            return self._gen_left_assoc_chain(ctx, ctx.additiveExpr(), _REL_OPS, dest)
        if isinstance(ctx, CompiscriptParser.AdditiveExprContext):
            return self._gen_additive_chain(ctx, dest)
        if isinstance(ctx, CompiscriptParser.MultiplicativeExprContext):
            return self._gen_left_assoc_chain(ctx, ctx.unaryExpr(), _MULT_OPS, dest)
        if isinstance(ctx, CompiscriptParser.UnaryExprContext):
            return self._gen_unary(ctx, dest)
        if isinstance(ctx, CompiscriptParser.PrimaryExprContext):
            return self._gen_primary_expr(ctx, dest)
        if isinstance(ctx, CompiscriptParser.LiteralExprContext):
            return self._gen_literal(ctx, dest)
        if isinstance(ctx, CompiscriptParser.LeftHandSideContext):
            return self._gen_left_hand_side(ctx, dest)
        if isinstance(ctx, CompiscriptParser.ArrayLiteralContext):
            return self._gen_array_literal(ctx, dest)
        raise AssertionError(f"nodo de expresion no soportado: {type(ctx).__name__}")

    def _gen_left_assoc_chain(self, ctx, operand_ctxs, opcode_map: dict, dest) -> Operand:
        op_symbols = set(opcode_map)
        ops = [t.getText() for t in ctx.getChildren()
               if hasattr(t, "getText") and t.getText() in op_symbols]
        if not ops:
            return self._gen_expr(operand_ctxs[0], dest)
        result = self._gen_expr(operand_ctxs[0])
        last = len(ops) - 1
        for i, (op_text, operand_ctx) in enumerate(zip(ops, operand_ctxs[1:])):
            right = self._gen_expr(operand_ctx)
            self.temps.release(result)
            self.temps.release(right)
            target = dest if (dest is not None and i == last) else self.temps.new_temp()
            self._emit(opcode_map[op_text], result, right, target)
            result = target
        return result

    def _gen_additive_chain(self, ctx: CompiscriptParser.AdditiveExprContext, dest) -> Operand:
        operand_ctxs = ctx.multiplicativeExpr()
        ops = [t.getText() for t in ctx.getChildren()
               if hasattr(t, "getText") and t.getText() in ("+", "-")]
        if not ops:
            return self._gen_expr(operand_ctxs[0], dest)
        result = self._gen_expr(operand_ctxs[0])
        result_type = self.types.get(operand_ctxs[0])
        last = len(ops) - 1
        for i, (op_text, operand_ctx) in enumerate(zip(ops, operand_ctxs[1:])):
            right = self._gen_expr(operand_ctx)
            right_type = self.types.get(operand_ctx)
            hint = dest if (dest is not None and i == last) else None
            if op_text == "+" and (_is_string_type(result_type) or _is_string_type(right_type)):
                result = self._emit_concat(result, result_type, right, right_type, hint)
                result_type = STRING
            else:
                self.temps.release(result)
                self.temps.release(right)
                target = hint if hint is not None else self.temps.new_temp()
                self._emit(OpCode.ADD if op_text == "+" else OpCode.SUB, result, right, target)
                result = target
        return result

    def _emit_concat(self, left, left_type, right, right_type, dest) -> Operand:
        if not _is_string_type(left_type):
            left = self._bool_to_str(left) if _is_bool_type(left_type) else self._emit_tostr(left)
        if not _is_string_type(right_type):
            right = self._bool_to_str(right) if _is_bool_type(right_type) else self._emit_tostr(right)
        self.temps.release(left)
        self.temps.release(right)
        target = dest if dest is not None else self.temps.new_temp()
        self._emit(OpCode.CONCAT, left, right, target)
        return target

    def _emit_tostr(self, value: Operand) -> Operand:
        self.temps.release(value)
        t = self.temps.new_temp()
        self._emit(OpCode.TOSTR, value, None, t)
        return t

    def _bool_to_str(self, value: Operand) -> Operand:
        """Booleanos son 1/0 en TAC; al imprimirlos o concatenarlos se muestran como
        "true"/"false" (semántica TS) con un salto, sin opcode extra."""
        self.temps.release(value)
        t = self.temps.new_temp()
        l_false = self.labels.new_label()
        l_end = self.labels.new_label()
        self._emit(OpCode.IFFALSE, value, None, Label(l_false))
        self._emit(OpCode.ASSIGN, StrConst(self.program.intern_string("true")), None, t)
        self._emit(OpCode.GOTO, None, None, Label(l_end))
        self._emit(OpCode.LABEL, None, None, Label(l_false))
        self._emit(OpCode.ASSIGN, StrConst(self.program.intern_string("false")), None, t)
        self._emit(OpCode.LABEL, None, None, Label(l_end))
        return t

    def _gen_unary(self, ctx: CompiscriptParser.UnaryExprContext, dest) -> Operand:
        if ctx.primaryExpr():
            return self._gen_expr(ctx.primaryExpr(), dest)
        op_text = ctx.getChild(0).getText()
        operand = self._gen_expr(ctx.unaryExpr())
        self.temps.release(operand)
        target = dest if dest is not None else self.temps.new_temp()
        self._emit(OpCode.NOT if op_text == "!" else OpCode.NEG, operand, None, target)
        return target

    def _gen_ternary(self, ctx: CompiscriptParser.TernaryExprContext, dest) -> Operand:
        expressions = ctx.expression()
        if not expressions:
            return self._gen_expr(ctx.logicalOrExpr(), dest)
        target = dest if dest is not None else self.temps.new_temp()
        l_false = self.labels.new_label()
        l_end = self.labels.new_label()
        self._gen_cond(ctx.logicalOrExpr(), None, l_false)
        self._gen_expr(expressions[0], dest=target)
        self._emit(OpCode.GOTO, None, None, Label(l_end))
        self._emit(OpCode.LABEL, None, None, Label(l_false))
        self._gen_expr(expressions[1], dest=target)
        self._emit(OpCode.LABEL, None, None, Label(l_end))
        return target

    def _gen_bool_value(self, ctx, dest) -> Operand:
        target = dest if dest is not None else self.temps.new_temp()
        l_true = self.labels.new_label()
        l_false = self.labels.new_label()
        l_end = self.labels.new_label()
        self._gen_cond(ctx, l_true, l_false)
        self._emit(OpCode.LABEL, None, None, Label(l_true))
        self._emit(OpCode.ASSIGN, Const(1), None, target)
        self._emit(OpCode.GOTO, None, None, Label(l_end))
        self._emit(OpCode.LABEL, None, None, Label(l_false))
        self._emit(OpCode.ASSIGN, Const(0), None, target)
        self._emit(OpCode.LABEL, None, None, Label(l_end))
        return target

    def _gen_primary_expr(self, ctx: CompiscriptParser.PrimaryExprContext, dest) -> Operand:
        if ctx.literalExpr():
            return self._gen_expr(ctx.literalExpr(), dest)
        if ctx.leftHandSide():
            return self._gen_expr(ctx.leftHandSide(), dest)
        if ctx.expression():
            return self._gen_expr(ctx.expression(), dest)
        return self._leaf(Const(0), dest)

    def _gen_literal(self, ctx: CompiscriptParser.LiteralExprContext, dest) -> Operand:
        if ctx.Literal():
            text = ctx.Literal().getText()
            if text.startswith('"'):
                operand = StrConst(self.program.intern_string(text[1:-1]))
            elif "." in text:
                operand = Const(float(text))
            else:
                operand = Const(int(text))
            return self._leaf(operand, dest)
        if ctx.arrayLiteral():
            return self._gen_expr(ctx.arrayLiteral(), dest)
        text = ctx.getText()
        if text in ("true", "false"):
            return self._leaf(Const(1 if text == "true" else 0), dest)
        return self._leaf(Const(0), dest)  # null

    def _gen_array_literal(self, ctx: CompiscriptParser.ArrayLiteralContext, dest) -> Operand:
        exprs = ctx.expression()
        arr = dest if dest is not None else self.temps.new_temp()
        self._emit(OpCode.NEWARRAY, Const(len(exprs)), None, arr)
        for i, e in enumerate(exprs):
            value = self._gen_expr(e)
            offset = ARRAY_HEADER_SIZE + i * WORD_SIZE
            self._emit(OpCode.STORE, arr, Const(offset), value)
            self.temps.release(value)
        return arr

    # --- Asignaciones como expresión ---

    def _gen_assign_expr(self, ctx: CompiscriptParser.AssignExprContext, dest) -> Operand:
        lhs = ctx.lhs
        suffixes = lhs.suffixOp()
        if not suffixes:
            sym = self.symbol_of.get(lhs.primaryAtom())
            if sym is None:
                value = self._gen_expr(ctx.assignmentExpr())
                return self._leaf(value, dest)
            if sym.storage in ("local", "param") and self._static_link_depth(sym) > 0:
                value = self._gen_expr(ctx.assignmentExpr())
                self._write_var(sym, value)
            else:
                value = self._gen_expr(ctx.assignmentExpr(), dest=VarRef(sym))
            return self._leaf(value, dest)
        value = self._gen_expr(ctx.assignmentExpr())
        written = self._gen_assign_target_chain(lhs, value)
        return self._leaf(written, dest)

    def _gen_property_assign_expr(self, ctx: CompiscriptParser.PropertyAssignExprContext, dest) -> Operand:
        obj = self._gen_expr(ctx.lhs)
        obj_type = self.types.get(ctx.lhs)
        value = self._gen_expr(ctx.assignmentExpr())
        attr = ctx.Identifier().getText()
        offset = obj_type.field_offset(attr) if isinstance(obj_type, ClassType) else 0
        self._emit(OpCode.STORE, obj, Const(offset or 0), value, comment=f".{attr}")
        self.temps.release(obj)
        return self._leaf(value, dest)

    def _gen_assign_target_chain(self, lhs_ctx, value: Operand) -> Operand:
        suffixes = lhs_ctx.suffixOp()
        current = self._gen_primary_atom(lhs_ctx.primaryAtom())
        current_type = self.types.get(lhs_ctx.primaryAtom())
        for suffix in suffixes[:-1]:
            current, current_type = self._gen_suffix_read(suffix, current, current_type, None)
        last = suffixes[-1]
        if isinstance(last, CompiscriptParser.IndexExprContext):
            index = self._gen_expr(last.expression())
            self._emit(OpCode.BOUNDS, current, index, None, comment="boundscheck")
            offset_t = self.temps.new_temp()
            self._emit(OpCode.MUL, index, Const(WORD_SIZE), offset_t)
            self.temps.release(index)
            self._emit(OpCode.ADD, offset_t, Const(ARRAY_HEADER_SIZE), offset_t)
            self._emit(OpCode.STORE, current, offset_t, value)
            self.temps.release(offset_t)
        elif isinstance(last, CompiscriptParser.PropertyAccessExprContext):
            attr = last.Identifier().getText()
            offset = current_type.field_offset(attr) if isinstance(current_type, ClassType) else 0
            self._emit(OpCode.STORE, current, Const(offset or 0), value, comment=f".{attr}")
        self.temps.release(current)
        return value

    # --- leftHandSide (lecturas, llamadas) ---

    def _gen_left_hand_side(self, ctx: CompiscriptParser.LeftHandSideContext, dest) -> Operand:
        atom = ctx.primaryAtom()
        suffixes = ctx.suffixOp()
        i = 0
        if (suffixes and isinstance(suffixes[0], CompiscriptParser.CallExprContext)
                and isinstance(atom, CompiscriptParser.IdentifierExprContext)):
            sym = self.symbol_of.get(atom)
            if sym is not None and sym.kind == SymbolKind.FUNCTION:
                is_last0 = len(suffixes) == 1
                current = self._gen_static_call(sym, suffixes[0], dest if is_last0 else None)
                current_type = self.types.get(suffixes[0])
                i = 1
            else:
                current = self._gen_primary_atom(atom)
                current_type = self.types.get(atom)
        else:
            current = self._gen_primary_atom(atom)
            current_type = self.types.get(atom)

        if not suffixes:
            return self._leaf(current, dest)

        n = len(suffixes)
        while i < n:
            suffix = suffixes[i]
            is_last = i == n - 1
            if (isinstance(suffix, CompiscriptParser.PropertyAccessExprContext) and not is_last
                    and isinstance(suffixes[i + 1], CompiscriptParser.CallExprContext)
                    and isinstance(current_type, ClassType)
                    and current_type.method_slot(suffix.Identifier().getText()) is not None):
                method_name = suffix.Identifier().getText()
                call_suffix = suffixes[i + 1]
                is_last_pair = i + 1 == n - 1
                result = self._gen_method_call(current, current_type, method_name, call_suffix,
                                                dest if is_last_pair else None)
                self.temps.release(current)
                current, current_type = result, self.types.get(call_suffix)
                i += 2
                continue
            next_dest = dest if is_last else None
            result, next_type = self._gen_suffix_read(suffix, current, current_type, next_dest)
            self.temps.release(current)
            current, current_type = result, next_type
            i += 1
        return current

    def _gen_suffix_read(self, suffix, base, base_type, dest):
        if isinstance(suffix, CompiscriptParser.IndexExprContext):
            index = self._gen_expr(suffix.expression())
            self._emit(OpCode.BOUNDS, base, index, None, comment="boundscheck")
            offset_t = self.temps.new_temp()
            self._emit(OpCode.MUL, index, Const(WORD_SIZE), offset_t)
            self.temps.release(index)
            self._emit(OpCode.ADD, offset_t, Const(ARRAY_HEADER_SIZE), offset_t)
            result = dest if dest is not None else self.temps.new_temp()
            self._emit(OpCode.LOAD, base, offset_t, result)
            self.temps.release(offset_t)
            return result, self.types.get(suffix)
        if isinstance(suffix, CompiscriptParser.PropertyAccessExprContext):
            attr = suffix.Identifier().getText()
            offset = base_type.field_offset(attr) if isinstance(base_type, ClassType) else 0
            result = dest if dest is not None else self.temps.new_temp()
            self._emit(OpCode.LOAD, base, Const(offset or 0), result, comment=f".{attr}")
            return result, self.types.get(suffix)
        if isinstance(suffix, CompiscriptParser.CallExprContext):
            raise NotImplementedError(
                "Llamadas indirectas (a través de una variable/valor) no están soportadas; "
                "ver docs/TAC_LANGUAGE.md §6."
            )
        raise AssertionError("suffixOp desconocido")

    def _gen_primary_atom(self, ctx) -> Operand:
        if isinstance(ctx, CompiscriptParser.IdentifierExprContext):
            sym = self.symbol_of.get(ctx)
            return self._read_var(sym) if sym is not None else Const(0)
        if isinstance(ctx, CompiscriptParser.ThisExprContext):
            sym = self.symbol_of.get(ctx)
            return self._read_var(sym) if sym is not None else Const(0)
        if isinstance(ctx, CompiscriptParser.NewExprContext):
            return self._gen_new(ctx)
        return Const(0)

    def _gen_new(self, ctx: CompiscriptParser.NewExprContext) -> Operand:
        class_name = ctx.Identifier().getText()
        class_type = self.class_registry.get(class_name)
        obj = self.temps.new_temp()
        size = class_type.instance_size if class_type else WORD_SIZE
        self._emit(OpCode.NEW, Label(class_name), Const(size), obj)
        ctor_label = class_type.method_label("constructor") if class_type else None
        if ctor_label:
            args_ctx = ctx.arguments()
            arg_exprs = list(args_ctx.expression()) if args_ctx else []
            arg_operands = [self._gen_expr(e) for e in arg_exprs]
            self._emit(OpCode.PARAM, obj)
            for a in arg_operands:
                self._emit(OpCode.PARAM, a)
            for a in arg_operands:
                self.temps.release(a)
            self._emit(OpCode.CALL, Label(ctor_label), Const(len(arg_operands) + 1), None,
                       comment=f"n={len(arg_operands) + 1}")
        return obj

    def _gen_static_call(self, sym: Symbol, call_suffix, dest) -> Operand:
        args_ctx = call_suffix.arguments()
        arg_exprs = list(args_ctx.expression()) if args_ctx else []
        arg_operands = [self._gen_expr(e) for e in arg_exprs]
        needs_link = bool(sym.extra.get("has_static_link"))
        n = len(arg_operands) + (1 if needs_link else 0)
        if needs_link:
            self._emit(OpCode.PARAM, FP)
        for a in arg_operands:
            self._emit(OpCode.PARAM, a)
        for a in arg_operands:
            self.temps.release(a)
        ret_type = sym.data_type.return_type if isinstance(sym.data_type, FunctionType) else None
        result = None
        if ret_type is None or ret_type.kind != TypeKind.VOID:
            result = dest if dest is not None else self.temps.new_temp()
        self._emit(OpCode.CALL, Label(sym.label), Const(n), result, comment=f"{sym.name} n={n}")
        return result if result is not None else Const(0)

    def _gen_method_call(self, obj: Operand, class_type: ClassType, method_name: str,
                          call_suffix, dest) -> Operand:
        args_ctx = call_suffix.arguments()
        arg_exprs = list(args_ctx.expression()) if args_ctx else []
        arg_operands = [self._gen_expr(e) for e in arg_exprs]
        self._emit(OpCode.PARAM, obj)
        for a in arg_operands:
            self._emit(OpCode.PARAM, a)
        for a in arg_operands:
            self.temps.release(a)
        slot = class_type.method_slot(method_name)
        method_type = class_type.resolve_member(method_name)
        ret_type = method_type.return_type if isinstance(method_type, FunctionType) else None
        n = len(arg_operands) + 1
        result = None
        if ret_type is None or ret_type.kind != TypeKind.VOID:
            result = dest if dest is not None else self.temps.new_temp()
        self._emit(OpCode.VCALL, obj, Const(slot), result, comment=f".{method_name} n={n}")
        return result if result is not None else Const(0)

    # --- Condiciones con cortocircuito (ticket C-1) ---

    def _gen_cond(self, ctx, l_true: Optional[str], l_false: Optional[str]) -> None:
        if isinstance(ctx, CompiscriptParser.ExpressionContext):
            return self._gen_cond(ctx.assignmentExpr(), l_true, l_false)
        if isinstance(ctx, CompiscriptParser.ExprNoAssignContext):
            return self._gen_cond(ctx.conditionalExpr(), l_true, l_false)
        if isinstance(ctx, CompiscriptParser.TernaryExprContext) and not ctx.expression():
            return self._gen_cond(ctx.logicalOrExpr(), l_true, l_false)
        if isinstance(ctx, CompiscriptParser.LogicalOrExprContext) and len(ctx.logicalAndExpr()) > 1:
            operands = ctx.logicalAndExpr()
            for operand in operands[:-1]:
                l_next = self.labels.new_label()
                self._gen_cond(operand, l_true, l_next)
                self._emit(OpCode.LABEL, None, None, Label(l_next))
            return self._gen_cond(operands[-1], l_true, l_false)
        if isinstance(ctx, CompiscriptParser.LogicalAndExprContext) and len(ctx.equalityExpr()) > 1:
            operands = ctx.equalityExpr()
            for operand in operands[:-1]:
                l_next = self.labels.new_label()
                self._gen_cond(operand, l_next, l_false)
                self._emit(OpCode.LABEL, None, None, Label(l_next))
            return self._gen_cond(operands[-1], l_true, l_false)
        if isinstance(ctx, CompiscriptParser.UnaryExprContext) and not ctx.primaryExpr() \
                and ctx.getChild(0).getText() == "!":
            return self._gen_cond(ctx.unaryExpr(), l_false, l_true)
        if isinstance(ctx, CompiscriptParser.RelationalExprContext) and len(ctx.additiveExpr()) == 2:
            return self._gen_relational_cond(ctx, l_true, l_false)
        if isinstance(ctx, CompiscriptParser.EqualityExprContext) and len(ctx.relationalExpr()) == 2:
            return self._gen_equality_cond(ctx, l_true, l_false)

        value = self._gen_expr(ctx)
        self.temps.release(value)
        if l_true is not None:
            self._emit(OpCode.IF, value, None, Label(l_true))
            if l_false is not None:
                self._emit(OpCode.GOTO, None, None, Label(l_false))
        elif l_false is not None:
            self._emit(OpCode.IFFALSE, value, None, Label(l_false))

    def _gen_relational_cond(self, ctx, l_true, l_false) -> None:
        operands = ctx.additiveExpr()
        op_text = next(t.getText() for t in ctx.getChildren()
                        if hasattr(t, "getText") and t.getText() in _REL_JUMPS)
        left = self._gen_expr(operands[0])
        right = self._gen_expr(operands[1])
        self.temps.release(left)
        self.temps.release(right)
        self._emit_relational_jump(_REL_JUMPS[op_text], left, right, l_true, l_false)

    def _gen_equality_cond(self, ctx, l_true, l_false) -> None:
        operands = ctx.relationalExpr()
        op_text = next(t.getText() for t in ctx.getChildren()
                        if hasattr(t, "getText") and t.getText() in _EQ_JUMPS)
        left = self._gen_expr(operands[0])
        right = self._gen_expr(operands[1])
        self.temps.release(left)
        self.temps.release(right)
        self._emit_relational_jump(_EQ_JUMPS[op_text], left, right, l_true, l_false)

    def _emit_relational_jump(self, jump_op: OpCode, left, right, l_true, l_false) -> None:
        if l_true is not None:
            self._emit(jump_op, left, right, Label(l_true))
            if l_false is not None:
                self._emit(OpCode.GOTO, None, None, Label(l_false))
        elif l_false is not None:
            self._emit(NEGATED_RELATIONAL[jump_op], left, right, Label(l_false))
