"""Central strategy registry: the single source of truth for S1..S10."""
from __future__ import annotations

from dataclasses import dataclass

from optimizer import (common_subexpression, constant_folding, constant_propagation,
                       copy_propagation, dead_code_elimination, strength_reduction)

# Canonical execution order: CF -> SR -> COP -> CSE -> CP -> DCE
PASS_ORDER = ("CF", "SR", "COP", "CSE", "CP", "DCE")

PASS_FUNCTIONS = {
    "CF": constant_folding.run,
    "SR": strength_reduction.run,
    "COP": copy_propagation.run,
    "CSE": common_subexpression.run,
    "CP": constant_propagation.run,
    "DCE": dead_code_elimination.run,
}

PASS_FULL_NAMES = {
    "CF": "Constant Folding",
    "SR": "Strength Reduction",
    "COP": "Copy Propagation",
    "CSE": "Common Subexpression Elimination",
    "CP": "Constant Propagation",
    "DCE": "Dead Code Elimination",
}

# Per-pass compile-time costs (relative units). Used by the cost-aware
# evaluation metric so that lighter strategies can beat heavier ones
# when the additional passes produce little extra benefit.
PASS_COSTS: dict[str, float] = {
    "CF": 1.0,   # simple linear scan
    "SR": 1.0,   # simple linear scan
    "COP": 1.5,  # per-block copy tracking
    "CSE": 2.0,  # per-block value numbering
    "CP": 3.0,   # global data-flow fixed point
    "DCE": 3.0,  # liveness analysis + multiple sub-passes
}

# Weight applied to total pass cost when computing cost-aware scores.
# score = instruction_reduction_pct - COST_WEIGHT * sum(pass_costs)
COST_WEIGHT: float = 0.5


@dataclass(frozen=True)
class Strategy:
    id: str
    passes: frozenset

    @property
    def ordered_passes(self) -> tuple[str, ...]:
        """Passes in canonical order."""
        return tuple(p for p in PASS_ORDER if p in self.passes)

    @property
    def label(self) -> str:
        return " + ".join(sorted(self.passes, key=PASS_ORDER.index))

    @property
    def number(self) -> int:
        return int(self.id[1:])

    @property
    def cost(self) -> float:
        """Sum of per-pass compile-time costs."""
        return sum(PASS_COSTS[p] for p in self.passes)


STRATEGIES: dict[str, Strategy] = {
    "S1":  Strategy("S1",  frozenset({"CF"})),
    "S2":  Strategy("S2",  frozenset({"CF", "CP"})),
    "S3":  Strategy("S3",  frozenset({"CF", "DCE"})),
    "S4":  Strategy("S4",  frozenset({"CF", "CP", "DCE"})),
    "S5":  Strategy("S5",  frozenset({"CF", "CP", "CSE"})),
    "S6":  Strategy("S6",  frozenset({"CF", "CP", "DCE", "CSE"})),
    "S7":  Strategy("S7",  frozenset({"CF", "SR"})),
    "S8":  Strategy("S8",  frozenset({"CF", "SR", "DCE"})),
    "S9":  Strategy("S9",  frozenset({"CF", "COP", "CP", "DCE"})),
    "S10": Strategy("S10", frozenset({"CF", "SR", "COP", "CP", "DCE", "CSE"})),
}
STRATEGY_IDS = tuple(STRATEGIES)
FIXED_STRATEGY = "S10"


def strategy_cost(strategy_id: str) -> float:
    """Total compile-time cost of a strategy's passes."""
    return get_strategy(strategy_id).cost


def cost_aware_score(reduction_pct: float, strategy_id: str) -> float:
    """Instruction-count reduction penalised by compile-time cost."""
    return reduction_pct - COST_WEIGHT * strategy_cost(strategy_id)


def get_strategy(strategy_id: str) -> Strategy:
    try:
        return STRATEGIES[strategy_id]
    except KeyError:
        raise ValueError(f"Unknown strategy {strategy_id!r}; valid: {', '.join(STRATEGY_IDS)}")
