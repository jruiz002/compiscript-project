# compiler/semantic/symbol_table.py
"""
Symbol Table with scope/environment management for Compiscript.

Copiado y extendido de semantic-analyzer/compiler/semantic/symbol_table.py (Fase 1) — ver
FEATURES.md ticket A-0. Extensiones de la Fase 2 (ticket A-2, CLAUDE.md §6):
  - Symbol: offset, size, storage, label, address().
  - Scope: activation_record (en scopes de función).
  - ActivationRecord: registro de activación con asignación de offsets para params/locales.
  - GlobalAllocator: offsets de variables globales (sección de datos, gp[off]).
  - SymbolTable.dump(): árbol de scopes con offsets y frames, para IDE/docs.

Diseño del frame: docs/TAC_LANGUAGE.md §3. Las variables de bloques internos se aplanan en el
frame de la función: ActivationRecord.allocate_local() avanza un cursor; save_cursor()/
restore_cursor() (llamado al entrar/salir de cada bloque) permite que bloques hermanos reusen
el mismo espacio de offsets, mientras que el "punto más profundo" alcanzado (peak) determina el
tamaño final de la zona de locales.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Literal, Optional

from .types import ANY, CompiscriptType

WORD_SIZE = 4  # bytes por valor (todo — enteros, floats, booleanos, referencias — ocupa 1 word)


class SymbolKind(Enum):
    VARIABLE = "variable"
    CONSTANT = "constant"
    FUNCTION = "function"
    PARAMETER = "parameter"
    CLASS = "class"
    LOOP_VAR = "loop_variable"   # foreach loop variable


Storage = Literal["global", "local", "param", "field", None]


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
    # --- Fase 2: dirección/tamaño/etiqueta (CLAUDE.md §6) ---
    offset: Optional[int] = None
    size: int = WORD_SIZE
    storage: Storage = None
    label: Optional[str] = None  # etiqueta de función/método (f_nombre, Clase_metodo)
    # Extra metadata stored for IDE / documentation
    extra: Dict[str, Any] = field(default_factory=dict)

    def address(self) -> str:
        """Dirección simbólica de memoria: 'gp[4]', 'fp[-8]', '[8]' (campo, relativo a objeto)."""
        if self.storage == "global":
            return f"gp[{self.offset}]"
        if self.storage in ("local", "param"):
            return f"fp[{self.offset}]"
        if self.storage == "field":
            return f"[{self.offset}]"
        return f"<{self.name}>"

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
            "storage": self.storage,
            "offset": self.offset,
            "size": self.size,
            "address": self.address() if self.storage else None,
            "label": self.label,
        }


@dataclass
class ActivationRecord:
    """Registro de activación de una función/método (CLAUDE.md §5.3, §6)."""

    function_name: str
    has_static_link: bool = False
    params: List[Symbol] = field(default_factory=list)
    locals: List[Symbol] = field(default_factory=list)
    temp_count: int = 0
    frame_size: int = 0

    _next_param_offset: int = field(default=8, repr=False)
    _next_local_offset: int = field(default=-8, repr=False)
    _max_local_bytes: int = field(default=0, repr=False)

    def allocate_param(self, symbol: Symbol) -> int:
        offset = self._next_param_offset
        symbol.offset = offset
        symbol.storage = "param"
        symbol.size = WORD_SIZE
        self._next_param_offset += WORD_SIZE
        self.params.append(symbol)
        return offset

    def allocate_local(self, symbol: Symbol) -> int:
        offset = self._next_local_offset
        symbol.offset = offset
        symbol.storage = "local"
        symbol.size = WORD_SIZE
        self._next_local_offset -= WORD_SIZE
        self._max_local_bytes = max(self._max_local_bytes, -offset - 4)
        self.locals.append(symbol)
        return offset

    def save_cursor(self) -> int:
        """Snapshot del cursor de locales, para restaurarlo al salir de un bloque hijo."""
        return self._next_local_offset

    def restore_cursor(self, saved: int) -> None:
        """Bloques hermanos reusan el mismo rango de offsets (CLAUDE.md §5.3)."""
        self._next_local_offset = saved

    def finalize(self, temp_count: int) -> int:
        """Se llama cuando ya se conoce max_temps (al terminar de generar TAC de la función)."""
        self.temp_count = temp_count
        # fp-4 (slot del static link) se reserva siempre, aunque la función no lo use: los
        # locales empiezan en fp-8 en todos los frames, así que sin contarlo el último local
        # quedaría fuera de los `frame_size` bytes bajo fp.
        self.frame_size = WORD_SIZE + self._max_local_bytes + WORD_SIZE * temp_count
        return self.frame_size

    def describe(self) -> str:
        lines = [f"ActivationRecord({self.function_name}) frame_size={self.frame_size}"]
        lines.append("  fp-4          static link" if self.has_static_link
                     else "  fp-4          (reservado: sin static link)")
        for p in self.params:
            lines.append(f"  fp+{p.offset:<9} param {p.name}: {p.data_type}")
        for l in self.locals:
            lines.append(f"  fp{l.offset:<10} local {l.name}: {l.data_type}")
        lines.append(f"  temporales    max_temps={self.temp_count} ({WORD_SIZE * self.temp_count} bytes)")
        return "\n".join(lines)


class GlobalAllocator:
    """Asigna offsets en la sección de datos globales (gp[off])."""

    def __init__(self):
        self._next_offset = 0

    def allocate(self, symbol: Symbol) -> int:
        offset = self._next_offset
        symbol.offset = offset
        symbol.storage = "global"
        symbol.size = WORD_SIZE
        self._next_offset += WORD_SIZE
        return offset

    @property
    def total_size(self) -> int:
        return self._next_offset


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
        self.scope_kind = scope_kind  # 'global' | 'function' | 'class' | 'block' | 'loop' | 'switch'
        self._symbols: Dict[str, Symbol] = {}
        self.children: List["Scope"] = []
        # Fase 2: solo los scopes de función tienen un registro de activación propio.
        self.activation_record: Optional[ActivationRecord] = None
        # Fase 2: Symbol de la función/método que abrió este scope (para encadenar labels de
        # funciones anidadas, p.ej. f_externa__interna). None salvo en scopes 'function'.
        self.defining_symbol: Optional[Symbol] = None

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

    def enclosing_activation_record(self) -> Optional["ActivationRecord"]:
        """Walk up to find the ActivationRecord of the nearest enclosing function scope."""
        scope: Optional[Scope] = self
        while scope is not None:
            if scope.activation_record is not None:
                return scope.activation_record
            scope = scope.parent
        return None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "kind": self.scope_kind,
            "level": self.level,
            "symbols": [s.to_dict() for s in self._symbols.values() if not s.name.startswith("__")],
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
        self.globals = GlobalAllocator()

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

    def current_function_scope(self) -> Optional[Scope]:
        for scope in reversed(self._scope_stack):
            if scope.scope_kind == "function":
                return scope
        return None

    def enclosing_activation_record(self) -> Optional[ActivationRecord]:
        return self.current_scope.enclosing_activation_record()

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

    def dump(self) -> str:
        """Árbol legible de scopes con offsets/direcciones y registros de activación
        (usado por el CLI --dump-symbols y el panel de símbolos del IDE)."""
        lines: List[str] = [f"globals: {self.globals.total_size} bytes"]
        self._dump_scope(self._global, 0, lines)
        return "\n".join(lines)

    def _dump_scope(self, scope: Scope, indent: int, lines: List[str]) -> None:
        pad = "  " * indent
        lines.append(f"{pad}[{scope.scope_kind}] {scope.name} (level={scope.level})")
        for sym in scope.symbols().values():
            if sym.name.startswith("__"):
                continue
            addr = sym.address() if sym.storage else "-"
            lines.append(f"{pad}  {sym.kind.value:<9} {sym.name}: {sym.data_type} @ {addr}")
        if scope.activation_record is not None:
            for line in scope.activation_record.describe().splitlines():
                lines.append(f"{pad}  {line}")
        for child in scope.children:
            self._dump_scope(child, indent + 1, lines)
