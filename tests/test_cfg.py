from compiler.basic_blocks import build_basic_blocks, find_leaders
from compiler.cfg import CFG
from compiler.ir import CondJump, Jump, Label
from tests.conftest import compile_ir


def test_straight_line_single_block():
    cfg = CFG.build(compile_ir("int a = 1; int b = a + 2; print(b);"))
    assert len(cfg.blocks) == 1 and cfg.edge_count == 0 and cfg.back_edges() == []


def test_leaders_include_labels_and_post_branch():
    ir = compile_ir("int a = 1; if (a > 0) { print(a); } print(2);")
    leaders = find_leaders(ir)
    assert leaders[0] == 0
    for i in leaders:
        assert i == 0 or isinstance(ir.instructions[i], Label) or isinstance(ir.instructions[i - 1], (Jump, CondJump))


def test_if_else_diamond_edges():
    cfg = CFG.build(compile_ir("int a = 1; if (a > 0) { print(1); } else { print(2); } print(3);"))
    entry = cfg.blocks[0].id
    assert len(cfg.successors[entry]) == 2
    join = [b.id for b in cfg.blocks if len(cfg.predecessors[b.id]) == 2]
    assert join, "join block with two predecessors expected"
    for s, d in cfg.edges:
        assert s in cfg.predecessors[d] and d in cfg.successors[s]


def test_while_has_one_back_edge():
    cfg = CFG.build(compile_ir("int i = 0; while (i < 3) { i = i + 1; }"))
    assert len(cfg.back_edges()) == 1
    tail, head = cfg.back_edges()[0]
    assert head < tail


def test_nested_loops_two_back_edges():
    cfg = CFG.build(compile_ir("int i = 0; while (i < 3) { int j = 0; while (j < 2) { j = j + 1; } i = i + 1; }"))
    assert len(cfg.back_edges()) == 2


def test_if_inside_loop_is_not_a_back_edge():
    cfg = CFG.build(compile_ir("int i = 0; while (i < 5) { if (i == 2) { print(i); } i = i + 1; }"))
    assert len(cfg.back_edges()) == 1


def test_blocks_partition_instructions():
    ir = compile_ir("int i = 0; while (i < 3) { if (i == 1) { print(i); } i = i + 1; }")
    blocks = build_basic_blocks(ir)
    assert [i for b in blocks for i in b.instructions] == ir.instructions


def test_serialisation_and_dot():
    cfg = CFG.build(compile_ir("int i = 0; while (i < 3) { i = i + 1; }"))
    d = cfg.to_dict()
    assert d["edges"] and d["back_edges"]
    assert "digraph" in cfg.to_dot()


def test_empty_program():
    cfg = CFG.build(compile_ir(""))
    assert cfg.blocks == [] and cfg.edge_count == 0
