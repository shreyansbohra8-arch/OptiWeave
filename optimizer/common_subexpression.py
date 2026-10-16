"""Common Subexpression Elimination (CSE): local value numbering per basic block.

Available expressions are tracked inside each basic block. An expression stays
available until one of its operands (or the variable holding its value) is redefined.
When ``t2 = b + c`` repeats an available expression held in ``h``:
  * if ``t2`` is a compiler temporary defined once and used only in this block, the
    instruction is deleted and later uses of ``t2`` read ``h`` instead (copy forwarding);
    if ``h`` is redefined before ``t2``'s last use, ``t2 = h`` is re-materialised first;
  * otherwise the instruction becomes the copy ``dst = h``.
Commutative operators (+ * == !=) are normalised so ``a*b`` and ``b*a`` match.
Scope is deliberately local (one basic block); see docs/OPTIMIZATION_PASSES.md.
"""
from __future__ import annotations

from collections import Counter, defaultdict

from compiler.cfg import CFG
from compiler.ir import Assign, BinOp, IRProgram, Var, defs, expr_key, uses
from optimizer._common import map_operands

NAME = "CSE"


def run(ir: IRProgram) -> tuple[IRProgram, int]:
    cfg = CFG.build(ir)
    types = ir.var_types
    def_count: Counter = Counter()
    use_blocks: dict[str, set] = defaultdict(set)
    for b in cfg.blocks:
        for ins in b.instructions:
            d = defs(ins)
            if d is not None:
                def_count[d] += 1
            for u in uses(ins):
                use_blocks[u].add(b.id)

    out, changes = [], 0
    for b in cfg.blocks:
        avail: dict[tuple, str] = {}
        alias: dict[str, Var] = {}
        for ins in b.instructions:
            if alias:
                ins = map_operands(ins, lambda o: alias.get(o.name, o) if isinstance(o, Var) else o)
            d = defs(ins)
            key = expr_key(ins) if isinstance(ins, BinOp) else None
            replaced = False
            if key is not None:
                holder = avail.get(key)
                if holder is not None and holder != d and types.get(holder) == types.get(d):
                    if d in ir.temps and def_count[d] == 1 and use_blocks[d] <= {b.id}:
                        alias[d] = Var(holder)
                        changes += 1
                        continue  # instruction deleted
                    ins = Assign(d, Var(holder))
                    changes += 1
                    replaced = True
            if d is not None:
                # re-materialise aliases that point at a variable about to be redefined
                for t, h in list(alias.items()):
                    if h.name == d:
                        out.append(Assign(t, Var(d)))
                        del alias[t]
                for k in [k for k, h in avail.items()
                          if h == d or any(isinstance(o, Var) and o.name == d for o in k[1:])]:
                    del avail[k]
            out.append(ins)
            if key is not None and not replaced and d is not None:
                if not any(isinstance(o, Var) and o.name == d for o in key[1:]):
                    avail[key] = d
    return ir.with_instructions(out), changes
