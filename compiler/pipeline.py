"""Front-end facade: source text -> tokens, AST, symbols, IR, blocks, CFG, features."""
from __future__ import annotations

from dataclasses import dataclass, field

from compiler.ast_nodes import Program
from compiler.cfg import CFG
from compiler.ir import IRProgram
from compiler.ir_generator import generate_ir
from compiler.lexer import tokenize
from compiler.parser import parse
from compiler.semantic_analyzer import SemanticResult, analyze
from compiler.symbol_table import SymbolTable
from compiler.tokens import Token
from utils.exceptions import (OptiWeaveError, SemanticErrors, SourceError)
from utils.validation import validate_source_text


@dataclass
class FrontEndResult:
    source: str
    tokens: list[Token] = field(default_factory=list)
    ast: Program | None = None
    symbols: SymbolTable | None = None
    ir: IRProgram | None = None
    cfg: CFG | None = None
    errors: list[str] = field(default_factory=list)
    failed_stage: str | None = None

    @property
    def ok(self) -> bool:
        return not self.errors and self.ir is not None


def compile_front_end(source: str) -> FrontEndResult:
    """Run lexing, parsing, semantic analysis, IR generation and CFG construction.

    Never raises for bad *source programs*: failures are reported in ``errors`` and
    ``failed_stage``; invalid programs never reach IR generation.
    """
    res = FrontEndResult(source=source)
    try:
        validate_source_text(source)
    except OptiWeaveError as exc:
        res.errors, res.failed_stage = [str(exc)], "input"
        return res
    try:
        res.tokens = tokenize(source)
    except SourceError as exc:
        res.errors, res.failed_stage = [str(exc)], "lexer"
        return res
    try:
        res.ast = parse(res.tokens)
    except SourceError as exc:
        res.errors, res.failed_stage = [str(exc)], "parser"
        return res
    sem: SemanticResult = analyze(res.ast)
    res.symbols = sem.symbols
    if not sem.ok:
        res.errors = [str(e) for e in sem.errors]
        res.failed_stage = "semantic"
        return res
    user_names = {s.name for s in sem.symbols.all_symbols()}
    res.ir = generate_ir(res.ast, user_names)
    res.cfg = CFG.build(res.ir)
    return res


def compile_or_raise(source: str) -> FrontEndResult:
    """Like :func:`compile_front_end` but raises on failure (useful in scripts/tests)."""
    res = compile_front_end(source)
    if not res.ok:
        raise OptiWeaveError(f"[{res.failed_stage}] " + "; ".join(res.errors))
    return res
