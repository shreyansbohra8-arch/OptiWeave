"""Dead Code Elimination (DCE) using backward liveness analysis.

Removes, repeating until nothing changes:
  1. instructions in blocks unreachable from the entry block;
  2. ``goto L`` where ``L`` immediately follows (redundant jumps);
  3. assignments whose destination is not live afterwards (liveness analysis);
  4. labels that are no longer a jump target.

Observable behaviour is preserved: ``print`` and control flow are never removed, and a
division/modulo that might fault at run time (non-constant or zero divisor) is kept.
"""
from __future__ import annotations

from compiler.cfg import CFG
from compiler.ir import CondJump, IRProgram, Jump, Label, can_fault, defs, uses

NAME = "DCE"


def _remove_unreachable(ir: IRProgram) -> tuple[list, int]:
    cfg = CFG.build(ir)
    reach = cfg.reachable()
    kept, removed = [], 0
    for b in cfg.blocks:
        if b.id in reach:
            kept.extend(b.instructions)
        else:
            removed += sum(1 for i in b.instructions if not isinstance(i, Label))
    return kept, removed


def _remove_redundant_jumps(instrs: list) -> tuple[list, int]:
    out, removed = [], 0
    for i, ins in enumerate(instrs):
        if isinstance(ins, Jump):
            j = i + 1
            redundant = False
            while j < len(instrs) and isinstance(instrs[j], Label):
                if instrs[j].name == ins.target:
                    redundant = True
                    break
                j += 1
            if redundant:
                removed += 1
                continue
        out.append(ins)
    return out, removed


def _remove_dead_assignments(ir: IRProgram) -> tuple[list, int]:
    cfg = CFG.build(ir)
    live_in = {b.id: set() for b in cfg.blocks}
    live_out = {b.id: set() for b in cfg.blocks}
    changed = True
    while changed:
        changed = False
        for b in reversed(cfg.blocks):
            out = set()
            for s in cfg.successors[b.id]:
                out |= live_in[s]
            live = set(out)
            for ins in reversed(b.instructions):
                d = defs(ins)
                if d is not None:
                    live.discard(d)
                live.update(uses(ins))
            if out != live_out[b.id] or live != live_in[b.id]:
                live_out[b.id], live_in[b.id] = out, live
                changed = True
    kept_blocks, removed = [], 0
    for b in cfg.blocks:
        live = set(live_out[b.id])
        keep = []
        for ins in reversed(b.instructions):
            d = defs(ins)
            if d is not None and d not in live and not can_fault(ins):
                removed += 1
                continue
            if d is not None:
                live.discard(d)
            live.update(uses(ins))
            keep.append(ins)
        keep.reverse()
        kept_blocks.append(keep)
    return [i for blk in kept_blocks for i in blk], removed


def _remove_unused_labels(instrs: list) -> list:
    targets = set()
    for ins in instrs:
        if isinstance(ins, Jump):
            targets.add(ins.target)
        elif isinstance(ins, CondJump):
            targets.update((ins.true_target, ins.false_target))
    return [i for i in instrs if not (isinstance(i, Label) and i.name not in targets)]


def run(ir: IRProgram) -> tuple[IRProgram, int]:
    cur, total = ir, 0
    for _ in range(100):
        instrs, r1 = _remove_unreachable(cur)
        instrs, r2 = _remove_redundant_jumps(instrs)
        nxt = cur.with_instructions(instrs)
        instrs, r3 = _remove_dead_assignments(nxt)
        instrs = _remove_unused_labels(instrs)
        removed = r1 + r2 + r3
        cur = cur.with_instructions(instrs)
        total += removed
        if removed == 0:
            break
    return cur, total
