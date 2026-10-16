"""Scoped symbol table."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Symbol:
    name: str
    type: str
    line: int
    column: int
    scope_level: int


class SymbolTable:
    """Stack of scopes. Names are also globally unique (no shadowing / reuse)."""

    def __init__(self) -> None:
        self._scopes: list[dict[str, Symbol]] = [{}]
        self._history: list[Symbol] = []

    @property
    def depth(self) -> int:
        return len(self._scopes) - 1

    def enter_scope(self) -> None:
        self._scopes.append({})

    def exit_scope(self) -> None:
        if len(self._scopes) > 1:
            self._scopes.pop()

    def lookup(self, name: str) -> Symbol | None:
        for scope in reversed(self._scopes):
            if name in scope:
                return scope[name]
        return None

    def declared_before(self, name: str) -> Symbol | None:
        """Return an earlier declaration of ``name`` anywhere in the program."""
        for sym in self._history:
            if sym.name == name:
                return sym
        return None

    def declare(self, name: str, type_: str, line: int, column: int) -> Symbol:
        sym = Symbol(name, type_, line, column, self.depth)
        self._scopes[-1][name] = sym
        self._history.append(sym)
        return sym

    def all_symbols(self) -> list[Symbol]:
        """Every symbol declared in the program, in declaration order."""
        return list(self._history)
