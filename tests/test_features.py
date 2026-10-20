from compiler.cfg import CFG
from ml.feature_extractor import FEATURE_NAMES, extract_features, feature_vector
from tests.conftest import compile_ir


def test_exactly_fourteen_features_in_order():
    assert len(FEATURE_NAMES) == 14
    assert FEATURE_NAMES[0] == "instruction_count" and FEATURE_NAMES[-1] == "branch_ratio"
    f = extract_features(compile_ir("int a = 1; print(a);"))
    assert list(f) == FEATURE_NAMES


def test_empty_program():
    f = extract_features(compile_ir(""))
    assert all(v == 0 for v in f.values())


def test_values_for_known_program():
    ir = compile_ir("int a = 1; int b = 2; int c = a + b; int d = a + b; int e = 2 * 3; "
                    "int i = 0; while (i < 2) { i = i + 1; }")
    f = extract_features(ir)
    assert f["duplicate_expression_count"] == 1
    assert f["constant_expression_count"] == 1
    assert f["loop_count"] == 1 and f["branch_count"] == 1
    assert f["distinct_variable_count"] == 6  # a b c d e i
    assert f["basic_block_count"] == len(CFG.build(ir).blocks)
    assert f["cfg_edge_count"] == CFG.build(ir).edge_count
    assert f["instruction_count"] == ir.instruction_count


def test_ratio_features():
    ir = compile_ir("int a = 1; int b = 2; int c = a + b; int d = a + b; int e = 2 * 3; "
                    "int i = 0; while (i < 2) { i = i + 1; }")
    f = extract_features(ir)
    ic = f["instruction_count"]
    if ic > 0:
        assert f["constant_expression_ratio"] == round(f["constant_expression_count"] / ic, 6)
        assert f["duplicate_expression_ratio"] == round(f["duplicate_expression_count"] / ic, 6)
        assert f["assignment_ratio"] == round(f["assignment_count"] / ic, 6)
        assert f["branch_ratio"] == round(f["branch_count"] / ic, 6)


def test_redefinition_prevents_duplicate_count():
    f = extract_features(compile_ir("int a = 1; int b = 2; int c = a + b; a = 5; int d = a + b;"))
    assert f["duplicate_expression_count"] == 0


def test_deterministic_and_vector_order():
    ir = compile_ir("int a = 1; int b = a * 2; print(b);")
    f1, f2 = extract_features(ir), extract_features(ir)
    assert f1 == f2 and feature_vector(f1) == list(f1.values())


def test_features_independent_of_optimisation_labels():
    # features are computed from the original IR; optimising must not change them
    from optimizer.optimization_pipeline import run_strategy
    ir = compile_ir("int a = 1 + 2; print(a);")
    before = extract_features(ir)
    run_strategy(ir, "S6")
    assert extract_features(ir) == before
