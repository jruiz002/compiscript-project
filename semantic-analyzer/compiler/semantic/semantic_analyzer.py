# compiler/semantic/semantic_analyzer.py
"""
Semantic Analyzer for Compiscript.
Implements an ANTLR4 Visitor that traverses the parse tree, enforces
all semantic rules, builds the symbol table, and infers types for expressions.
"""
from __future__ import annotations

import sys
import os

# Ensure generated parser is importable — handle both flat and nested output dirs
_COMPILER_DIR = os.path.join(os.path.dirname(__file__), "..")
_GEN_FLAT = os.path.join(_COMPILER_DIR, "generated")
_GEN_NESTED = os.path.join(_COMPILER_DIR, "generated", "compiler")
for _p in [_GEN_FLAT, _GEN_NESTED]:
    if os.path.isfile(os.path.join(_p, "CompiscriptLexer.py")):
        sys.path.insert(0, os.path.abspath(_p))
        break

from CompiscriptVisitor import CompiscriptVisitor
from CompiscriptParser import CompiscriptParser

from .types import (
    CompiscriptType, ArrayType, FunctionType, ClassType,
    INTEGER, FLOAT, STRING, BOOLEAN, NULL, VOID, ANY, ERROR_TYPE,
    type_from_annotation, TypeKind,
)
from .symbol_table import SymbolTable, Symbol, SymbolKind
from .errors import ErrorCollector


class SemanticAnalyzer(CompiscriptVisitor):
    """
    Full semantic analysis visitor.
    After visiting the tree:
      - self.errors   → ErrorCollector with all semantic errors/warnings
      - self.symbols  → SymbolTable with all scopes and symbols
    """

    def __init__(self):
        self.errors = ErrorCollector()
        self.symbols = SymbolTable()
        self._class_registry: dict[str, ClassType] = {}
        self._in_constructor = False

    # ===================================================================
    # Helpers
    # ===================================================================

    def _loc(self, ctx) -> tuple[int, int]:
        token = getattr(ctx, "start", None)
        if token:
            return token.line, token.column
        return 0, 0

    def _err(self, ctx, msg: str):
        line, col = self._loc(ctx)
        self.errors.error(msg, line, col)

    def _warn(self, ctx, msg: str):
        line, col = self._loc(ctx)
        self.errors.warning(msg, line, col)

    def _type_from_ctx(self, type_ctx) -> CompiscriptType:
        if type_ctx is None:
            return ANY
        text = type_ctx.getText()
        return type_from_annotation(text, self._class_registry)

    def _check_boolean(self, ctx, expr_type: CompiscriptType, context_label: str):
        if expr_type.kind not in (TypeKind.BOOLEAN, TypeKind.ANY, TypeKind.ERROR):
            self._err(ctx, f"Condition in {context_label} must be boolean, got '{expr_type}'")

    def _check_property_assignment(self, ctx, obj_type: CompiscriptType, attr_name: str,
                                    rhs_type: CompiscriptType | None):
        """Validate `obj.attr_name = rhs` for both the statement and expression forms."""
        if isinstance(obj_type, ClassType):
            member = obj_type.resolve_member(attr_name)
            if member is None:
                self._err(ctx, f"Property '{attr_name}' does not exist on type '{obj_type}'")
            elif (rhs_type and member.kind not in (TypeKind.ANY, TypeKind.ERROR) and
                  rhs_type.kind not in (TypeKind.ANY, TypeKind.ERROR)):
                if not member.is_compatible_with(rhs_type):
                    self._err(ctx, f"Cannot assign '{rhs_type}' to '{attr_name}' (type '{member}')")

    # ===================================================================
    # Program Entry
    # ===================================================================

    def visitProgram(self, ctx: CompiscriptParser.ProgramContext):
        # First pass: pre-register all top-level class declarations
        for stmt in ctx.statement():
            cd = stmt.classDeclaration()
            if cd:
                self._pre_register_class(cd)
        # Second pass: full visit
        self.visitChildren(ctx)
        return None

    def _pre_register_class(self, ctx: CompiscriptParser.ClassDeclarationContext):
        name = ctx.Identifier(0).getText()
        if name not in self._class_registry:
            self._class_registry[name] = ClassType(name=name)

    # ===================================================================
    # Statements
    # ===================================================================

    def visitBlock(self, ctx: CompiscriptParser.BlockContext):
        self.symbols.enter_scope(kind="block")
        self.visitChildren(ctx)
        self.symbols.exit_scope()
        return None

    # --- Variable / Constant declarations ---

    def visitVariableDeclaration(self, ctx: CompiscriptParser.VariableDeclarationContext):
        name = ctx.Identifier().getText()
        line, col = self._loc(ctx)

        declared_type: CompiscryptType = ANY
        if ctx.typeAnnotation():
            declared_type = self._type_from_ctx(ctx.typeAnnotation().type_())

        init_type = None
        if ctx.initializer():
            init_type = self.visit(ctx.initializer().expression())

        # Determine final type (with inference)
        if declared_type.kind == TypeKind.ANY and init_type is not None:
            final_type = init_type
        elif init_type is not None and declared_type.kind != TypeKind.ANY:
            if (init_type.kind not in (TypeKind.ANY, TypeKind.ERROR) and
                    declared_type.kind not in (TypeKind.ANY, TypeKind.ERROR)):
                if not declared_type.is_compatible_with(init_type):
                    self._err(ctx,
                        f"Type mismatch in declaration of '{name}': "
                        f"declared '{declared_type}', got '{init_type}'"
                    )
            final_type = declared_type
        else:
            final_type = declared_type

        sym = Symbol(
            name=name,
            kind=SymbolKind.VARIABLE,
            data_type=final_type,
            line=line, column=col,
            scope_level=self.symbols.current_level,
            is_initialized=init_type is not None,
        )
        if not self.symbols.define(sym):
            self._err(ctx, f"Redeclaration of identifier '{name}' in the same scope")
        return None

    def visitConstantDeclaration(self, ctx: CompiscryptParser.ConstantDeclarationContext):
        name = ctx.Identifier().getText()
        line, col = self._loc(ctx)

        declared_type = ANY
        if ctx.typeAnnotation():
            declared_type = self._type_from_ctx(ctx.typeAnnotation().type_())

        init_type = self.visit(ctx.expression())

        if (declared_type.kind not in (TypeKind.ANY, TypeKind.ERROR) and
                init_type is not None and init_type.kind not in (TypeKind.ANY, TypeKind.ERROR)):
            if not declared_type.is_compatible_with(init_type):
                self._err(ctx,
                    f"Type mismatch in const '{name}': declared '{declared_type}', got '{init_type}'"
                )

        final_type = declared_type if declared_type.kind != TypeKind.ANY else (init_type or ANY)

        sym = Symbol(
            name=name,
            kind=SymbolKind.CONSTANT,
            data_type=final_type,
            line=line, column=col,
            scope_level=self.symbols.current_level,
            is_initialized=True,
            is_const=True,
        )
        if not self.symbols.define(sym):
            self._err(ctx, f"Redeclaration of identifier '{name}' in the same scope")
        return None

    def visitAssignment(self, ctx: CompiscriptParser.AssignmentContext):
        """Top-level assignment statement."""
        identifier = ctx.Identifier()
        expressions = ctx.expression()

        if identifier and len(expressions) == 1:
            # Simple: Identifier '=' expression
            name = identifier.getText()
            sym = self.symbols.lookup(name)
            if sym is None:
                self._err(ctx, f"Assignment to undeclared variable '{name}'")
                self.visit(expressions[0])
                return None
            if sym.is_const:
                self._err(ctx, f"Cannot assign to constant '{name}'")
            rhs_type = self.visit(expressions[0])
            if (rhs_type and
                    sym.data_type.kind not in (TypeKind.ANY, TypeKind.ERROR) and
                    rhs_type.kind not in (TypeKind.ANY, TypeKind.ERROR)):
                if not sym.data_type.is_compatible_with(rhs_type):
                    self._err(ctx,
                        f"Type mismatch: cannot assign '{rhs_type}' to '{name}' ({sym.data_type})"
                    )
            sym.is_initialized = True
        else:
            # Property: expr '.' Identifier '=' expr
            obj_type = self.visit(expressions[0])
            rhs_type = self.visit(expressions[1])
            attr_name = identifier.getText()
            self._check_property_assignment(ctx, obj_type, attr_name, rhs_type)
        return None

    # --- Function declaration ---

    def visitFunctionDeclaration(self, ctx: CompiscryptParser.FunctionDeclarationContext):
        name = ctx.Identifier().getText()
        line, col = self._loc(ctx)

        param_types, param_names = [], []
        if ctx.parameters():
            for param in ctx.parameters().parameter():
                pname = param.Identifier().getText()
                ptype = self._type_from_ctx(param.type_()) if param.type_() else ANY
                param_types.append(ptype)
                param_names.append(pname)

        ret_type = VOID
        if ctx.type_():
            ret_type = self._type_from_ctx(ctx.type_())

        func_type = FunctionType(param_types=param_types, return_type=ret_type, param_names=param_names)

        if self.symbols.lookup_local(name):
            self._err(ctx, f"Duplicate function declaration '{name}'")

        sym = Symbol(name=name, kind=SymbolKind.FUNCTION, data_type=func_type,
                     line=line, column=col, scope_level=self.symbols.current_level,
                     is_initialized=True)
        self.symbols.define(sym)

        is_constructor = (name == "constructor")
        prev_in_constructor = self._in_constructor
        self._in_constructor = is_constructor

        self.symbols.enter_scope(name=name, kind="function")
        self.symbols.set_return_type(ret_type)

        # Define params
        for pname, ptype in zip(param_names, param_types):
            if self.symbols.lookup_local(pname):
                self._err(ctx, f"Duplicate parameter name '{pname}' in function '{name}'")
                continue
            psym = Symbol(name=pname, kind=SymbolKind.PARAMETER, data_type=ptype,
                          line=line, column=col, scope_level=self.symbols.current_level,
                          is_initialized=True)
            self.symbols.define(psym)

        self._visit_block_dead_code(ctx.block())
        self.symbols.exit_scope()
        self._in_constructor = prev_in_constructor
        return func_type

    def _visit_block_dead_code(self, block_ctx):
        """Visit statements in a block, warn on unreachable code."""
        statements = block_ctx.statement()
        terminated = False
        for stmt in statements:
            if terminated:
                self._err(stmt, "Unreachable code after return/break/continue")
            self.visit(stmt)
            if stmt.returnStatement() or stmt.breakStatement() or stmt.continueStatement():
                terminated = True


    # --- Class declaration ---

    def visitClassDeclaration(self, ctx: CompiscryptParser.ClassDeclarationContext):
        identifiers = ctx.Identifier()
        name = identifiers[0].getText()
        line, col = self._loc(ctx)

        superclass_type = None
        if len(identifiers) > 1:
            parent_name = identifiers[1].getText()
            if parent_name not in self._class_registry:
                self._err(ctx, f"Superclass '{parent_name}' is not defined")
            else:
                superclass_type = self._class_registry[parent_name]

        ct = self._class_registry.get(name) or ClassType(name=name)
        ct.superclass = superclass_type
        self._class_registry[name] = ct

        sym = Symbol(name=name, kind=SymbolKind.CLASS, data_type=ct,
                     line=line, column=col, scope_level=self.symbols.current_level,
                     is_initialized=True)
        if not self.symbols.define(sym):
            self._err(ctx, f"Duplicate class declaration '{name}'")

        self.symbols.enter_scope(name=name, kind="class")

        # First pass inside class: collect member types for dot-access resolution
        for member in ctx.classMember():
            fn = member.functionDeclaration()
            vd = member.variableDeclaration()
            cd = member.constantDeclaration()

            if fn:
                mname = fn.Identifier().getText()
                pt, pn = [], []
                if fn.parameters():
                    for p in fn.parameters().parameter():
                        pt.append(self._type_from_ctx(p.type_()) if p.type_() else ANY)
                        pn.append(p.Identifier().getText())
                rtype = self._type_from_ctx(fn.type_()) if fn.type_() else VOID
                ct.methods[mname] = FunctionType(param_types=pt, return_type=rtype, param_names=pn)
            elif vd:
                aname = vd.Identifier().getText()
                atype = self._type_from_ctx(vd.typeAnnotation().type_()) if vd.typeAnnotation() else ANY
                ct.attributes[aname] = atype
            elif cd:
                aname = cd.Identifier().getText()
                atype = self._type_from_ctx(cd.typeAnnotation().type_()) if cd.typeAnnotation() else ANY
                ct.attributes[aname] = atype

        # Second pass: full semantic analysis of each member
        for member in ctx.classMember():
            self.visit(member)

        self.symbols.exit_scope()
        return ct

    # --- Control flow ---

    def visitIfStatement(self, ctx: CompiscryptParser.IfStatementContext):
        cond = self.visit(ctx.expression())
        self._check_boolean(ctx, cond, "'if'")
        for block in ctx.block():
            self.symbols.enter_scope(kind="block")
            self._visit_block_dead_code(block)
            self.symbols.exit_scope()
        return None

    def visitWhileStatement(self, ctx: CompiscryptParser.WhileStatementContext):
        cond = self.visit(ctx.expression())
        self._check_boolean(ctx, cond, "'while'")
        self.symbols.enter_scope(kind="loop")
        self._visit_block_dead_code(ctx.block())
        self.symbols.exit_scope()
        return None

    def visitDoWhileStatement(self, ctx: CompiscryptParser.DoWhileStatementContext):
        self.symbols.enter_scope(kind="loop")
        self._visit_block_dead_code(ctx.block())
        self.symbols.exit_scope()
        cond = self.visit(ctx.expression())
        self._check_boolean(ctx, cond, "'do-while'")
        return None

    def visitForStatement(self, ctx: CompiscryptParser.ForStatementContext):
        self.symbols.enter_scope(kind="loop")
        if ctx.variableDeclaration():
            self.visit(ctx.variableDeclaration())
        elif ctx.assignment():
            self.visit(ctx.assignment())
        expressions = ctx.expression()
        if expressions:
            cond = self.visit(expressions[0])
            self._check_boolean(ctx, cond, "'for'")
        if len(expressions) > 1:
            self.visit(expressions[1])
        self._visit_block_dead_code(ctx.block())
        self.symbols.exit_scope()
        return None

    def visitForeachStatement(self, ctx: CompiscryptParser.ForeachStatementContext):
        iter_name = ctx.Identifier().getText()
        line, col = self._loc(ctx)
        collection_type = self.visit(ctx.expression())

        elem_type = ANY
        if collection_type.kind == TypeKind.ARRAY:
            elem_type = collection_type.element_type
        elif collection_type.kind not in (TypeKind.ANY, TypeKind.ERROR):
            self._err(ctx, f"'foreach' requires an array, got '{collection_type}'")

        self.symbols.enter_scope(kind="loop")
        iter_sym = Symbol(name=iter_name, kind=SymbolKind.LOOP_VAR, data_type=elem_type,
                          line=line, column=col, scope_level=self.symbols.current_level,
                          is_initialized=True)
        self.symbols.define(iter_sym)
        self._visit_block_dead_code(ctx.block())
        self.symbols.exit_scope()
        return None

    def visitBreakStatement(self, ctx: CompiscryptParser.BreakStatementContext):
        if not self.symbols.is_break_allowed():
            self._err(ctx, "'break' used outside of a loop or switch")
        return None

    def visitContinueStatement(self, ctx: CompiscryptParser.ContinueStatementContext):
        if not self.symbols.is_inside_loop():
            self._err(ctx, "'continue' used outside of a loop")
        return None

    def visitReturnStatement(self, ctx: CompiscryptParser.ReturnStatementContext):
        if not self.symbols.is_inside_function():
            self._err(ctx, "'return' used outside of a function")
            return None

        declared_ret = VOID
        for scope in reversed(self.symbols._scope_stack):
            if scope.scope_kind == "function":
                rt_sym = scope._symbols.get("__return_type__")
                if rt_sym:
                    declared_ret = rt_sym.data_type
                break

        if ctx.expression():
            actual_ret = self.visit(ctx.expression())
            if self._in_constructor:
                self._err(ctx, "Constructor cannot return a value")
            elif declared_ret.kind == TypeKind.VOID:
                self._err(ctx, "Void function cannot return a value")
            elif (actual_ret and
                    actual_ret.kind not in (TypeKind.ANY, TypeKind.ERROR) and
                    declared_ret.kind not in (TypeKind.ANY, TypeKind.ERROR)):
                if not declared_ret.is_compatible_with(actual_ret):
                    self._err(ctx, f"Return type mismatch: expected '{declared_ret}', got '{actual_ret}'")
        else:
            if declared_ret.kind not in (TypeKind.VOID, TypeKind.ANY, TypeKind.ERROR):
                self._warn(ctx, f"Function expects return type '{declared_ret}' but got empty return")
        return None

    def visitTryCatchStatement(self, ctx: CompiscryptParser.TryCatchStatementContext):
        self.symbols.enter_scope(kind="block")
        self._visit_block_dead_code(ctx.block(0))
        self.symbols.exit_scope()

        catch_var = ctx.Identifier().getText()
        line, col = self._loc(ctx)
        self.symbols.enter_scope(kind="block")
        catch_sym = Symbol(name=catch_var, kind=SymbolKind.VARIABLE, data_type=ANY,
                           line=line, column=col, scope_level=self.symbols.current_level,
                           is_initialized=True)
        self.symbols.define(catch_sym)
        self._visit_block_dead_code(ctx.block(1))
        self.symbols.exit_scope()
        return None

    def visitSwitchStatement(self, ctx: CompiscryptParser.SwitchStatementContext):
        switch_type = self.visit(ctx.expression())
        for case in ctx.switchCase():
            case_type = self.visit(case.expression())
            if (switch_type.kind not in (TypeKind.ANY, TypeKind.ERROR) and
                    case_type.kind not in (TypeKind.ANY, TypeKind.ERROR)):
                if not switch_type.is_compatible_with(case_type):
                    self._err(case, f"Case type '{case_type}' incompatible with switch type '{switch_type}'")
            self.symbols.enter_scope(kind="switch")
            for stmt in case.statement():
                self.visit(stmt)
            self.symbols.exit_scope()
        if ctx.defaultCase():
            self.symbols.enter_scope(kind="switch")
            for stmt in ctx.defaultCase().statement():
                self.visit(stmt)
            self.symbols.exit_scope()
        return None

    def visitPrintStatement(self, ctx: CompiscryptParser.PrintStatementContext):
        self.visit(ctx.expression())
        return None

    def visitExpressionStatement(self, ctx: CompiscryptParser.ExpressionStatementContext):
        return self.visit(ctx.expression())

    # ===================================================================
    # Expressions — each returns the inferred CompiscryptType
    # ===================================================================

    def visitExpression(self, ctx: CompiscryptParser.ExpressionContext):
        return self.visit(ctx.assignmentExpr())

    def visitAssignExpr(self, ctx: CompiscryptParser.AssignExprContext):
        rhs_type = self.visit(ctx.assignmentExpr())
        lhs_type = self.visit(ctx.lhs)
        if (lhs_type and rhs_type and
                lhs_type.kind not in (TypeKind.ANY, TypeKind.ERROR) and
                rhs_type.kind not in (TypeKind.ANY, TypeKind.ERROR)):
            if not lhs_type.is_compatible_with(rhs_type):
                self._err(ctx, f"Cannot assign '{rhs_type}' to '{lhs_type}'")
        # Check if lhs is a const
        atom = ctx.lhs.primaryAtom() if hasattr(ctx.lhs, 'primaryAtom') else None
        if atom and isinstance(atom, CompiscriptParser.IdentifierExprContext):
            name = atom.Identifier().getText()
            sym = self.symbols.lookup(name)
            if sym and sym.is_const:
                self._err(ctx, f"Cannot assign to constant '{name}'")
        return rhs_type

    def visitPropertyAssignExpr(self, ctx: CompiscryptParser.PropertyAssignExprContext):
        obj_type = self.visit(ctx.lhs)
        rhs_type = self.visit(ctx.assignmentExpr())
        attr_name = ctx.Identifier().getText()
        if isinstance(obj_type, ClassType):
            member = obj_type.resolve_member(attr_name)
            if member is None:
                self._err(ctx, f"Property '{attr_name}' does not exist on type '{obj_type}'")
            elif (rhs_type and member.kind not in (TypeKind.ANY, TypeKind.ERROR) and
                  rhs_type.kind not in (TypeKind.ANY, TypeKind.ERROR)):
                if not member.is_compatible_with(rhs_type):
                    self._err(ctx, f"Cannot assign '{rhs_type}' to '{attr_name}' (type '{member}')")
        return rhs_type

    def visitExprNoAssign(self, ctx: CompiscryptParser.ExprNoAssignContext):
        return self.visit(ctx.conditionalExpr())

    def visitTernaryExpr(self, ctx: CompiscryptParser.TernaryExprContext):
        cond_type = self.visit(ctx.logicalOrExpr())
        expressions = ctx.expression()
        if expressions:
            self._check_boolean(ctx, cond_type, "ternary")
            t = self.visit(expressions[0])
            f = self.visit(expressions[1])
            return t if t == f else ANY
        return cond_type

    def visitLogicalOrExpr(self, ctx: CompiscryptParser.LogicalOrExprContext):
        operands = ctx.logicalAndExpr()
        result = self.visit(operands[0])
        for op in operands[1:]:
            r = self.visit(op)
            if result.kind not in (TypeKind.BOOLEAN, TypeKind.ANY, TypeKind.ERROR):
                self._err(ctx, f"Operands of '||' must be boolean, got '{result}'")
            if r.kind not in (TypeKind.BOOLEAN, TypeKind.ANY, TypeKind.ERROR):
                self._err(ctx, f"Operands of '||' must be boolean, got '{r}'")
            result = BOOLEAN
        return result

    def visitLogicalAndExpr(self, ctx: CompiscryptParser.LogicalAndExprContext):
        operands = ctx.equalityExpr()
        result = self.visit(operands[0])
        for op in operands[1:]:
            r = self.visit(op)
            if result.kind not in (TypeKind.BOOLEAN, TypeKind.ANY, TypeKind.ERROR):
                self._err(ctx, f"Operands of '&&' must be boolean, got '{result}'")
            if r.kind not in (TypeKind.BOOLEAN, TypeKind.ANY, TypeKind.ERROR):
                self._err(ctx, f"Operands of '&&' must be boolean, got '{r}'")
            result = BOOLEAN
        return result

    def visitEqualityExpr(self, ctx: CompiscryptParser.EqualityExprContext):
        operands = ctx.relationalExpr()
        result = self.visit(operands[0])
        ops = [t for t in ctx.getChildren()
               if hasattr(t, 'getText') and t.getText() in ('==', '!=')]
        for op_tok, operand in zip(ops, operands[1:]):
            r = self.visit(operand)
            if (result.kind not in (TypeKind.ANY, TypeKind.ERROR) and
                    r.kind not in (TypeKind.ANY, TypeKind.ERROR)):
                if not (result.is_compatible_with(r) or r.is_compatible_with(result)):
                    self._err(ctx, f"Cannot compare '{result}' and '{r}' with '{op_tok.getText()}'")
            result = BOOLEAN
        return result

    def visitRelationalExpr(self, ctx: CompiscryptParser.RelationalExprContext):
        operands = ctx.additiveExpr()
        result = self.visit(operands[0])
        ops = [t for t in ctx.getChildren()
               if hasattr(t, 'getText') and t.getText() in ('<', '<=', '>', '>=')]
        for op_tok, operand in zip(ops, operands[1:]):
            r = self.visit(operand)
            if not result.is_numeric() and result.kind not in (TypeKind.ANY, TypeKind.ERROR):
                self._err(ctx, f"Operands of '{op_tok.getText()}' must be numeric, got '{result}'")
            if not r.is_numeric() and r.kind not in (TypeKind.ANY, TypeKind.ERROR):
                self._err(ctx, f"Operands of '{op_tok.getText()}' must be numeric, got '{r}'")
            result = BOOLEAN
        return result

    def visitAdditiveExpr(self, ctx: CompiscryptParser.AdditiveExprContext):
        operands = ctx.multiplicativeExpr()
        ops = [t for t in ctx.getChildren()
               if hasattr(t, 'getText') and t.getText() in ('+', '-')]
        result = self.visit(operands[0])
        for op_tok, operand in zip(ops, operands[1:]):
            r = self.visit(operand)
            op = op_tok.getText()
            if op == '+':
                if result.kind == TypeKind.STRING and r.kind == TypeKind.STRING:
                    result = STRING
                elif result.is_numeric() and r.is_numeric():
                    result = FLOAT if (result.kind == TypeKind.FLOAT or r.kind == TypeKind.FLOAT) else INTEGER
                elif result.kind in (TypeKind.ANY, TypeKind.ERROR) or r.kind in (TypeKind.ANY, TypeKind.ERROR):
                    result = ANY
                else:
                    self._err(ctx, f"Operator '+' cannot be applied to '{result}' and '{r}'")
                    result = ERROR_TYPE
            else:
                if result.is_numeric() and r.is_numeric():
                    result = FLOAT if (result.kind == TypeKind.FLOAT or r.kind == TypeKind.FLOAT) else INTEGER
                elif result.kind in (TypeKind.ANY, TypeKind.ERROR) or r.kind in (TypeKind.ANY, TypeKind.ERROR):
                    result = ANY
                else:
                    self._err(ctx, f"Operator '-' cannot be applied to '{result}' and '{r}'")
                    result = ERROR_TYPE
        return result

    def visitMultiplicativeExpr(self, ctx: CompiscryptParser.MultiplicativeExprContext):
        operands = ctx.unaryExpr()
        ops = [t for t in ctx.getChildren()
               if hasattr(t, 'getText') and t.getText() in ('*', '/', '%')]
        result = self.visit(operands[0])
        for op_tok, operand in zip(ops, operands[1:]):
            r = self.visit(operand)
            if result.is_numeric() and r.is_numeric():
                result = FLOAT if (result.kind == TypeKind.FLOAT or r.kind == TypeKind.FLOAT) else INTEGER
            elif result.kind in (TypeKind.ANY, TypeKind.ERROR) or r.kind in (TypeKind.ANY, TypeKind.ERROR):
                result = ANY
            else:
                self._err(ctx, f"Operator '{op_tok.getText()}' cannot be applied to '{result}' and '{r}'")
                result = ERROR_TYPE
        return result

    def visitUnaryExpr(self, ctx: CompiscryptParser.UnaryExprContext):
        if ctx.primaryExpr():
            return self.visit(ctx.primaryExpr())
        op = ctx.getChild(0).getText()
        operand_type = self.visit(ctx.unaryExpr())
        if op == '!':
            if operand_type.kind not in (TypeKind.BOOLEAN, TypeKind.ANY, TypeKind.ERROR):
                self._err(ctx, f"Operator '!' requires boolean operand, got '{operand_type}'")
            return BOOLEAN
        elif op == '-':
            if not operand_type.is_numeric() and operand_type.kind not in (TypeKind.ANY, TypeKind.ERROR):
                self._err(ctx, f"Unary '-' requires numeric operand, got '{operand_type}'")
            return operand_type
        return ANY

    def visitPrimaryExpr(self, ctx: CompiscryptParser.PrimaryExprContext):
        if ctx.literalExpr():
            return self.visit(ctx.literalExpr())
        if ctx.leftHandSide():
            return self.visit(ctx.leftHandSide())
        if ctx.expression():
            return self.visit(ctx.expression())
        return ANY

    def visitLiteralExpr(self, ctx: CompiscryptParser.LiteralExprContext):
        if ctx.Literal():
            text = ctx.Literal().getText()
            if text.startswith('"'):
                return STRING
            if '.' in text:
                return FLOAT
            return INTEGER
        if ctx.arrayLiteral():
            return self.visit(ctx.arrayLiteral())
        t = ctx.getText()
        if t == 'null':
            return NULL
        if t in ('true', 'false'):
            return BOOLEAN
        return ANY

    def visitArrayLiteral(self, ctx: CompiscriptParser.ArrayLiteralContext):
        exprs = ctx.expression()
        if not exprs:
            return ArrayType(element_type=ANY, dimensions=1)
        elem_types = [self.visit(e) for e in exprs]
        first = elem_types[0]
        for i, et in enumerate(elem_types[1:], 1):
            if (first.kind not in (TypeKind.ANY, TypeKind.ERROR) and
                    et.kind not in (TypeKind.ANY, TypeKind.ERROR) and first != et):
                self._err(ctx,
                    f"Mixed array types: expected '{first}', got '{et}' at index {i}"
                )
        if isinstance(first, ArrayType):
            return ArrayType(element_type=first.element_type, dimensions=first.dimensions + 1)
        return ArrayType(element_type=first, dimensions=1)

    # --- LeftHandSide ---

    def visitLeftHandSide(self, ctx: CompiscryptParser.LeftHandSideContext):
        current_type = self.visit(ctx.primaryAtom())
        for suffix in ctx.suffixOp():
            current_type = self._apply_suffix(suffix, current_type)
        return current_type

    def _apply_suffix(self, suffix, obj_type) -> CompiscryptType:
        if isinstance(suffix, CompiscriptParser.CallExprContext):
            if isinstance(obj_type, FunctionType):
                args = suffix.arguments()
                arg_types = [self.visit(e) for e in args.expression()] if args else []
                if len(arg_types) != len(obj_type.param_types):
                    self._err(suffix,
                        f"Function expects {len(obj_type.param_types)} arg(s), got {len(arg_types)}"
                    )
                else:
                    for i, (exp, act) in enumerate(zip(obj_type.param_types, arg_types)):
                        if (exp.kind not in (TypeKind.ANY, TypeKind.ERROR) and
                                act.kind not in (TypeKind.ANY, TypeKind.ERROR)):
                            if not exp.is_compatible_with(act):
                                self._err(suffix, f"Arg {i+1}: expected '{exp}', got '{act}'")
                return obj_type.return_type or VOID
            elif obj_type.kind in (TypeKind.ANY, TypeKind.ERROR):
                if suffix.arguments():
                    for e in suffix.arguments().expression():
                        self.visit(e)
                return ANY
            else:
                self._err(suffix, f"'{obj_type}' is not callable")
                return ERROR_TYPE

        elif isinstance(suffix, CompiscriptParser.IndexExprContext):
            idx_type = self.visit(suffix.expression())
            if idx_type.kind not in (TypeKind.INTEGER, TypeKind.ANY, TypeKind.ERROR):
                self._err(suffix, f"Array index must be integer, got '{idx_type}'")
            if isinstance(obj_type, ArrayType):
                if obj_type.dimensions > 1:
                    return ArrayType(element_type=obj_type.element_type, dimensions=obj_type.dimensions - 1)
                return obj_type.element_type
            elif obj_type.kind in (TypeKind.ANY, TypeKind.ERROR):
                return ANY
            else:
                self._err(suffix, f"'{obj_type}' is not an array")
                return ERROR_TYPE

        elif isinstance(suffix, CompiscriptParser.PropertyAccessExprContext):
            attr_name = suffix.Identifier().getText()
            if isinstance(obj_type, ClassType):
                member = obj_type.resolve_member(attr_name)
                if member is None:
                    self._err(suffix, f"'{obj_type}' has no member '{attr_name}'")
                    return ERROR_TYPE
                return member
            elif obj_type.kind in (TypeKind.ANY, TypeKind.ERROR):
                return ANY
            else:
                self._err(suffix, f"Cannot access '{attr_name}' on non-object type '{obj_type}'")
                return ERROR_TYPE

        return ANY

    def visitIdentifierExpr(self, ctx: CompiscryptParser.IdentifierExprContext):
        name = ctx.Identifier().getText()
        sym = self.symbols.lookup(name)
        if sym is None:
            self._err(ctx, f"Use of undeclared identifier '{name}'")
            return ERROR_TYPE
        return sym.data_type

    def visitNewExpr(self, ctx: CompiscryptParser.NewExprContext):
        class_name = ctx.Identifier().getText()
        if class_name not in self._class_registry:
            self._err(ctx, f"Unknown class '{class_name}'")
            return ERROR_TYPE
        ct = self._class_registry[class_name]
        args = ctx.arguments()
        arg_types = [self.visit(e) for e in args.expression()] if args else []
        constructor = ct.methods.get("constructor")
        if constructor:
            if len(arg_types) != len(constructor.param_types):
                self._err(ctx,
                    f"Constructor of '{class_name}' expects {len(constructor.param_types)} arg(s), got {len(arg_types)}"
                )
            else:
                for i, (exp, act) in enumerate(zip(constructor.param_types, arg_types)):
                    if (exp.kind not in (TypeKind.ANY, TypeKind.ERROR) and
                            act.kind not in (TypeKind.ANY, TypeKind.ERROR)):
                        if not exp.is_compatible_with(act):
                            self._err(ctx, f"Constructor arg {i+1}: expected '{exp}', got '{act}'")
        elif arg_types:
            self._warn(ctx, f"Class '{class_name}' has no constructor but arguments were provided")
        return ct

    def visitThisExpr(self, ctx: CompiscryptParser.ThisExprContext):
        if not self.symbols.is_inside_class():
            self._err(ctx, "'this' used outside of a class method")
            return ERROR_TYPE
        ct = self.symbols.current_class_type()
        return ct if ct else ANY
