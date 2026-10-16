import pytest

from benchmarking.equivalence import check_equivalence
from optimizer import strategies
from optimizer.optimization_pipeline import instruction_reduction_pct, run_strategy
from tests.conftest import compile_ir


def test_registry_matches_specification():
    expected = {"S1": {"CF"}, "S2": {"CF", "CP"}, "S3": {"CF", "DCE"}, "S4": {"CF", "CP", "DCE"},
                "S5": {"CF", "CP", "CSE"}, "S6": {"CF", "CP", "DCE", "CSE"}}
    assert {k: set(v.passes) for k, v in strategies.STRATEGIES.items()} == expected


def test_canonical_pass_order():
    assert strategies.PASS_ORDER == ("CF", "CSE", "CP", "DCE")
    assert strategies.STRATEGIES["S6"].ordered_passes == ("CF", "CSE", "CP", "DCE")
    assert strategies.STRATEGIES["S5"].ordered_passes == ("CF", "CSE", "CP")


@pytest.mark.parametrize("sid", list(strategies.STRATEGY_IDS))
def test_only_strategy_passes_are_executed(sid):
    ir = compile_ir("int a = 1; int b = a + 2; int c = a + 2; print(b + c);")
    res = run_strategy(ir, sid)
    assert {r.pass_name for r in res.records} == set(strategies.STRATEGIES[sid].passes)


def test_s6_at_least_as_good_as_others_and_preserves_behaviour():
    src = ("int a = 4; int b = 6; int i = 0; int s = 0; int dead = 0; "
           "while (i < 5) { int p = a * b + i; int q = a * b + i; dead = i; s = s + p + q; i = i + 1; } print(s);")
    ir = compile_ir(src)
    counts = {}
    for sid in strategies.STRATEGY_IDS:
        res = run_strategy(ir, sid)
        assert check_equivalence(ir, res.optimized).equivalent
        counts[sid] = res.optimized_count
    assert counts["S6"] == min(counts.values())
    assert counts["S4"] < counts["S1"]


def test_input_program_not_mutated():
    ir = compile_ir("int a = 1 + 2; print(a);")
    snapshot = list(ir.instructions)
    run_strategy(ir, "S6")
    assert ir.instructions == snapshot


def test_fixed_point_iteration_is_bounded():
    ir = compile_ir("int a = 1; print(a);")
    assert run_strategy(ir, "S6", max_iterations=3).iterations <= 3


def test_reduction_percentage_and_zero_division():
    assert instruction_reduction_pct(10, 7) == pytest.approx(30.0)
    assert instruction_reduction_pct(0, 0) == 0.0


def test_unknown_strategy():
    with pytest.raises(ValueError):
        strategies.get_strategy("S9")


def test_tie_breaking_rule():
    from ml.dataset_generator import choose_best_strategy
    assert choose_best_strategy({"S1": 5, "S2": 5, "S3": 5, "S4": 5, "S5": 5, "S6": 5}) == "S1"
    assert choose_best_strategy({"S1": 9, "S2": 9, "S3": 7, "S4": 7, "S5": 9, "S6": 7}) == "S3"
    assert choose_best_strategy({"S1": 9, "S2": 9, "S3": 7, "S4": 6, "S5": 9, "S6": 6}) == "S4"
