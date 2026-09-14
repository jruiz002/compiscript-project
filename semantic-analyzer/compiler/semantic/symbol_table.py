# compiler/semantic/symbol_table.py
"""
Symbol Table with scope/environment management for Compiscript.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional

from .types import ANY, CompiscriptType


class SymbolKind(Enum):
    VARIABLE = "variable"
    CONSTANT = "constant"
    FUNCTION = "function"
    PARAMETER = "parameter"
    CLASS = "class"
    LOOP_VAR = "loop_variable"   # foreach loop variable


@dataclass
class Symbol:
    name: str
    kind: SymbolKind
    data_type: CompiscriptType
    line: int
    column: int
    scope_level: int
    is_initialized: bool = False
    is_const: bool = False
    # Extra metadata stored for IDE / documentation
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "kind": self.kind.value,
            "type": str(self.data_type),
            "line": self.line,
            "column": self.column,
            "scope_level": self.scope_level,
            "is_initialized": self.is_initialized,
            "is_const": self.is_const,
        }


class Scope:
    """
    A single environment frame (block, function body, class body, global).
    """

    def __init__(
        self,
        name: str,
        parent: Optional["Scope"] = None,
        level: int = 0,
        scope_kind: str = "block",
    ):
        self.name = name
        self.parent = parent
        self.level = level
        self.scope_kind = scope_kind  # 'global' | 'function' | 'class' | 'block' | 'loop'
        self._symbols: Dict[str, Symbol] = {}
        self.children: List["Scope"] = []

    # ------------------------------------------------------------------
    # Symbol operations
    # ------------------------------------------------------------------

    def define(self, symbol: Symbol) -> bool:
        """
        Define a symbol in this scope.
        Returns False if already defined (caller should emit error).
        """
        if symbol.name in self._symbols:
            return False
        self._symbols[symbol.name] = symbol
        return True

    def lookup_local(self, name: str) -> Optional[Symbol]:
        return self._symbols.get(name)

    def lookup(self, name: str) -> Optional[Symbol]:
        """Walk up the scope chain."""
        sym = self._symbols.get(name)
        if sym is not None:
            return sym
        if self.parent is not None:
            return self.parent.lookup(name)
        return None

    def symbols(self) -> Dict[str, Symbol]:
        return dict(self._symbols)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "kind": self.scope_kind,
            "level": self.level,
            "symbols": [s.to_dict() for s in self._symbols.values()],
            "children": [c.to_dict() for c in self.children],
        }

    def __repr__(self) -> str:
        return f"<Scope '{self.name}' level={self.level} symbols={list(self._symbols.keys())}>"


class SymbolTable:
    """
    Full symbol table managing a stack of scopes.
    Provides helpers for semantic analysis phases.
    """

    def __init__(self):
        self._global = Scope("global", parent=None, level=0, scope_kind="global")
        self._scope_stack: List[Scope] = [self._global]
        self._scope_counter = 0

    # ------------------------------------------------------------------
    # Scope management
    # ------------------------------------------------------------------

    @property
    def current_scope(self) -> Scope:
        return self._scope_stack[-1]

    @property
    def current_level(self) -> int:
        return len(self._scope_stack) - 1

    def enter_scope(self, name: str = None, kind: str = "block") -> Scope:
        self._scope_counter += 1
        label = name or f"block_{self._scope_counter}"
        new_scope = Scope(
            name=label,
            parent=self.current_scope,
            level=self.current_level + 1,
            scope_kind=kind,
        )
        self.current_scope.children.append(new_scope)
        self._scope_stack.append(new_scope)
        return new_scope

    def exit_scope(self) -> Scope:
        if len(self._scope_stack) <= 1:
            raise RuntimeError("Cannot exit global scope")
        return self._scope_stack.pop()

    # ------------------------------------------------------------------
    # Symbol operations (delegates to current scope)
    # ------------------------------------------------------------------

    def define(self, symbol: Symbol) -> bool:
        return self.current_scope.define(symbol)

    def lookup(self, name: str) -> Optional[Symbol]:
        return self.current_scope.lookup(name)

    def lookup_local(self, name: str) -> Optional[Symbol]:
        return self.current_scope.lookup_local(name)

    # ------------------------------------------------------------------
    # Context helpers (used by the semantic analyzer)
    # ------------------------------------------------------------------

    def current_function(self) -> Optional[Symbol]:
        """Walk back through scopes to find the nearest enclosing function."""
        for scope in reversed(self._scope_stack):
            if scope.scope_kind == "function":
                # The function symbol is in the *parent* scope
                if scope.parent:
                    sym = scope.parent.lookup_local(scope.name.split("_body")[0])
                    if sym and sym.kind == SymbolKind.FUNCTION:
                        return sym
        return None

    def is_inside_loop(self) -> bool:
        for scope in reversed(self._scope_stack):
            if scope.scope_kind == "loop":
                return True
            if scope.scope_kind in ("function", "global"):
                return False  # hit function boundary, stop looking
        return False

    def is_break_allowed(self) -> bool:
        """`break` is valid inside a loop OR a switch (unlike `continue`)."""
        for scope in reversed(self._scope_stack):
            if scope.scope_kind in ("loop", "switch"):
                return True
            if scope.scope_kind in ("function", "global"):
                return False  # hit function boundary, stop looking
        return False

    def is_inside_function(self) -> bool:
        for scope in reversed(self._scope_stack):
            if scope.scope_kind == "function":
                return True
        return False

    def is_inside_class(self) -> bool:
        for scope in reversed(self._scope_stack):
            if scope.scope_kind == "class":
                return True
        return False

    def current_class_type(self):
        """Return the ClassType of the nearest enclosing class, or None."""
        for scope in reversed(self._scope_stack):
            if scope.scope_kind == "class":
                sym = self._global.lookup(scope.name)
                if sym:
                    return sym.data_type
        return None

    def current_return_type(self):
        """Return the declared return type of the nearest enclosing function."""
        for scope in reversed(self._scope_stack):
            if scope.scope_kind == "function":
                # stored in scope.extra when entering
                sym = scope._symbols.get("__return_type__")
                return sym.data_type if sym else None
        return None

    def set_return_type(self, t: CompiscriptType):
        """Store the return type in the current function scope."""
        for scope in reversed(self._scope_stack):
            if scope.scope_kind == "function":
                scope._symbols["__return_type__"] = Symbol(
                    name="__return_type__", 
                    kind=SymbolKind.VARIABLE, 
                    data_type=t, 
                    line=0, column=0, 
                    scope_level=0
                )
                return

    # ------------------------------------------------------------------
    # Serialization (for IDE display)
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return self._global.to_dict()

    def flat_symbols(self) -> List[Symbol]:
        """Return all symbols defined across all scopes."""
        result = []
        self._collect(self._global, result)
        return result

    def _collect(self, scope: Scope, result: list):
        for sym in scope.symbols().values():
            if not sym.name.startswith("__"):
                result.append(sym)
        for child in scope.children:
            self._collect(child, result)
