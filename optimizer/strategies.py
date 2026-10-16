"""Central strategy registry: the single source of truth for S1..S6."""
from __future__ import annotations

from dataclasses import dataclass

from optimizer import (common_subexpression, constant_folding, constant_propagation,
                       dead_code_elimination)

# Canonical execution order: CF -> CSE -> CP -> DCE
PASS_ORDER = ("CF", "CSE", "CP", "DCE")

PASS_FUNCTIONS = {
    "CF": constant_folding.run,
    "CSE": common_subexpression.run,
    "CP": constant_propagation.run,
    "DCE": dead_code_elimination.run,
}

PASS_FULL_NAMES = {
    "CF": "Constant Folding",
    "CSE": "Common Subexpression Elimination",
    "CP": "Constant Propagation",
    "DCE": "Dead Code Elimination",
}


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


STRATEGIES: dict[str, Strategy] = {
    "S1": Strategy("S1", frozenset({"CF"})),
    "S2": Strategy("S2", frozenset({"CF", "CP"})),
    "S3": Strategy("S3", frozenset({"CF", "DCE"})),
    "S4": Strategy("S4", frozenset({"CF", "CP", "DCE"})),
    "S5": Strategy("S5", frozenset({"CF", "CP", "CSE"})),
    "S6": Strategy("S6", frozenset({"CF", "CP", "DCE", "CSE"})),
}
STRATEGY_IDS = tuple(STRATEGIES)
FIXED_STRATEGY = "S6"


def get_strategy(strategy_id: str) -> Strategy:
    try:
        return STRATEGIES[strategy_id]
    except KeyError:
        raise ValueError(f"Unknown strategy {strategy_id!r}; valid: {', '.join(STRATEGY_IDS)}")
