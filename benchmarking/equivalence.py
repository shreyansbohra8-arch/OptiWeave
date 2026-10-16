"""IR interpreter and semantic-equivalence checks."""
from __future__ import annotations

from dataclasses import dataclass, field

from compiler.ir import (Assign, BinOp, CondJump, Const, IRProgram, Jump, Label, Print, UnOp,
                         coerce, evaluate_binop, evaluate_unop, value_type)
from config import settings
from utils.exceptions import ExecutionError, ExecutionLimitError

_DEFAULTS = {"int": 0, "float": 0.0, "bool": False}


@dataclass
class ExecResult:
    output: list[str] = field(default_factory=list)
    error: str | None = None
    steps: int = 0
    limit_exceeded: bool = False

    @property
    def ok(self) -> bool:
        return self.error is None


def format_output(v: object) -> str:
    t = value_type(v)
    if t == "bool":
        return "true" if v else "false"
    if t == "float":
        return f"{v:.6f}"
    return str(v)


def run_ir(ir: IRProgram, max_steps: int = settings.INTERPRETER_MAX_STEPS) -> ExecResult:
    """Interpret an IR program. Mirrors the semantics of the generated C code."""
    labels = {i.name: n for n, i in enumerate(ir.instructions) if isinstance(i, Label)}
    env = {n: _DEFAULTS[t] for n, t in ir.var_types.items()}
    res = ExecResult()

    def val(op):
        return op.value if isinstance(op, Const) else env[op.name]

    pc, n = 0, len(ir.instructions)
    try:
        while pc < n:
            res.steps += 1
            if res.steps > max_steps:
                raise ExecutionLimitError("step limit exceeded")
            ins = ir.instructions[pc]
            pc += 1
            if isinstance(ins, Assign):
                env[ins.dst] = coerce(val(ins.src), ir.var_types.get(ins.dst))
            elif isinstance(ins, BinOp):
                env[ins.dst] = coerce(evaluate_binop(ins.op, val(ins.left), val(ins.right)),
                                      ir.var_types.get(ins.dst))
            elif isinstance(ins, UnOp):
                env[ins.dst] = coerce(evaluate_unop(ins.op, val(ins.src)), ir.var_types.get(ins.dst))
            elif isinstance(ins, Jump):
                pc = labels[ins.target]
            elif isinstance(ins, CondJump):
                pc = labels[ins.true_target if val(ins.cond) else ins.false_target]
            elif isinstance(ins, Print):
                res.output.append(format_output(val(ins.src)))
    except ExecutionLimitError as exc:
        res.error, res.limit_exceeded = str(exc), True
    except ExecutionError as exc:
        res.error = f"runtime error: {exc}"
    return res


@dataclass
class EquivalenceReport:
    equivalent: bool
    checked: bool
    detail: str = ""


def check_equivalence(original: IRProgram, optimized: IRProgram,
                      max_steps: int = settings.INTERPRETER_MAX_STEPS) -> EquivalenceReport:
    """Compare observable behaviour (printed output + success/runtime-error status)."""
    a, b = run_ir(original, max_steps), run_ir(optimized, max_steps)
    if a.limit_exceeded:
        return EquivalenceReport(True, False, "skipped: original exceeded interpreter step limit")
    if b.limit_exceeded:
        return EquivalenceReport(False, True, "optimized program exceeded step limit but original did not")
    if a.output != b.output or a.error != b.error:
        return EquivalenceReport(False, True,
                                 f"original={a.output[:5]}.. err={a.error}; "
                                 f"optimized={b.output[:5]}.. err={b.error}")
    return EquivalenceReport(True, True, "identical output")


def compare_outputs(a: str, b: str) -> bool:
    """Compare two program stdout strings."""
    return a.strip().splitlines() == b.strip().splitlines()
