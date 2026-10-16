"""AST node classes and a readable tree printer."""
from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from typing import Optional


@dataclass
class Node:
    line: int = 0
    column: int = 0


# -- expressions ------------------------------------------------------------
@dataclass
class Expr(Node):
    type: Optional[str] = field(default=None, kw_only=True)  # set by semantic analysis


@dataclass
class Literal(Expr):
    value: object = None
    literal_type: str = "int"


@dataclass
class Variable(Expr):
    name: str = ""


@dataclass
class Unary(Expr):
    op: str = ""
    operand: Expr = None  # type: ignore[assignment]


@dataclass
class Binary(Expr):
    op: str = ""
    left: Expr = None  # type: ignore[assignment]
    right: Expr = None  # type: ignore[assignment]


# -- statements ---------------------------------------------------------------
@dataclass
class Stmt(Node):
    """Base class of all statements."""


@dataclass
class VarDecl(Stmt):
    var_type: str = "int"
    name: str = ""
    init: Optional[Expr] = None


@dataclass
class Assign(Stmt):
    name: str = ""
    value: Expr = None  # type: ignore[assignment]


@dataclass
class Print(Stmt):
    value: Expr = None  # type: ignore[assignment]


@dataclass
class Block(Stmt):
    statements: list = field(default_factory=list)


@dataclass
class If(Stmt):
    condition: Expr = None  # type: ignore[assignment]
    then_block: Block = None  # type: ignore[assignment]
    else_block: Optional[Block] = None


@dataclass
class While(Stmt):
    condition: Expr = None  # type: ignore[assignment]
    body: Block = None  # type: ignore[assignment]


@dataclass
class Program(Node):
    statements: list = field(default_factory=list)


def format_ast(node: object, indent: int = 0) -> str:
    """Render an AST as an indented tree."""
    pad = "  " * indent
    if isinstance(node, list):
        return "\n".join(format_ast(n, indent) for n in node)
    if not is_dataclass(node):
        return f"{pad}{node!r}"
    name = type(node).__name__
    scalars = []
    children = []
    for f in fields(node):
        if f.name in ("line", "column"):
            continue
        val = getattr(node, f.name)
        if f.name == "type" and val is not None:
            scalars.append(f"type={val}")
        elif isinstance(val, Node) or isinstance(val, list):
            children.append((f.name, val))
        elif val is not None and f.name != "type":
            scalars.append(f"{f.name}={val!r}")
    lines = [f"{pad}{name}({', '.join(scalars)})"]
    for fname, child in children:
        if isinstance(child, list):
            for c in child:
                lines.append(format_ast(c, indent + 1))
        else:
            lines.append(f"{pad}  .{fname}:")
            lines.append(format_ast(child, indent + 2))
    return "\n".join(lines)
