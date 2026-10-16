"""Run a strategy's passes (with bounded fixed-point iteration) over an IR program."""
from __future__ import annotations

from dataclasses import dataclass, field

from compiler.ir import IRProgram
from config import settings
from optimizer.strategies import PASS_FUNCTIONS, PASS_FULL_NAMES, get_strategy


def instruction_reduction_pct(original: int, optimized: int) -> float:
    """(orig - opt) / orig * 100, defined as 0.0 when the original has no instructions."""
    if original <= 0:
        return 0.0
    return (original - optimized) / original * 100.0


@dataclass
class PassRecord:
    iteration: int
    pass_name: str
    instructions_before: int
    instructions_after: int
    rewrites: int
    changed: bool

    @property
    def delta(self) -> int:
        return self.instructions_before - self.instructions_after


@dataclass
class OptimizationResult:
    strategy_id: str
    original: IRProgram
    optimized: IRProgram
    records: list[PassRecord] = field(default_factory=list)
    iterations: int = 0

    @property
    def original_count(self) -> int:
        return self.original.instruction_count

    @property
    def optimized_count(self) -> int:
        return self.optimized.instruction_count

    @property
    def reduction_pct(self) -> float:
        return instruction_reduction_pct(self.original_count, self.optimized_count)

    @property
    def passes_applied(self) -> list[str]:
        """Distinct passes that actually changed the IR, in order of first effect."""
        seen = []
        for r in self.records:
            if r.changed and r.pass_name not in seen:
                seen.append(r.pass_name)
        return seen


def run_strategy(ir: IRProgram, strategy_id: str,
                 max_iterations: int = settings.MAX_OPT_ITERATIONS) -> OptimizationResult:
    """Apply strategy ``strategy_id`` to ``ir`` (input is never mutated)."""
    strategy = get_strategy(strategy_id)
    cur = ir.copy()
    result = OptimizationResult(strategy_id, ir, cur)
    for it in range(1, max_iterations + 1):
        round_start = cur
        for name in strategy.ordered_passes:
            before = cur.instruction_count
            nxt, rewrites = PASS_FUNCTIONS[name](cur)
            result.records.append(PassRecord(it, name, before, nxt.instruction_count,
                                             rewrites, nxt != cur))
            cur = nxt
        result.iterations = it
        if cur == round_start:
            break
    result.optimized = cur
    return result


def describe_passes(strategy_id: str) -> str:
    s = get_strategy(strategy_id)
    return " -> ".join(PASS_FULL_NAMES[p] for p in s.ordered_passes)
