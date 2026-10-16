# Optimization Passes

Canonical order: **CF -> CSE -> CP -> DCE**, repeated until the IR stops changing (maximum 10 rounds).
A strategy runs only its own passes, still in this order.

| Strategy | Passes |
|---|---|
| S1 | CF |
| S2 | CF + CP |
| S3 | CF + DCE |
| S4 | CF + CP + DCE |
| S5 | CF + CP + CSE |
| S6 | CF + CP + DCE + CSE |

## Constant Folding (CF) - `optimizer/constant_folding.py`
Replaces `BinOp`/`UnOp` whose operands are all constants by `dst = value`, using the same evaluator as the interpreter
(types, truncating division, 64-bit wrap). A `CondJump` with a constant condition becomes a `Jump`. It never folds a
division/modulo by zero (that is a run-time error to preserve) or a non-finite float result.

## Constant Propagation (CP) - `optimizer/constant_propagation.py`
Global forward data-flow analysis over the CFG. State = map variable -> known constant. Transfer functions evaluate
assignments; the meet at joins keeps a fact only when **all** processed predecessors agree on value and type. The analysis
starts optimistic (unvisited predecessors are ignored) and iterates to a fixed point, so loop-invariant constants flow
into loops while loop-carried variables are correctly left alone. Constants are coerced to the destination type, so
`float f = 5; f / 2` stays a floating division.

## Dead Code Elimination (DCE) - `optimizer/dead_code_elimination.py`
Repeats until stable: (1) delete blocks unreachable from the entry, (2) delete `goto L` immediately followed by `L:`,
(3) delete assignments whose destination is not live afterwards (backward **liveness** data-flow), (4) delete labels no jump targets.
`print` and control flow are never removed. A division/modulo that can fault is kept even if its result is unused.
*Limitation*: plain liveness keeps self-feeding dead accumulators (`d = d + i` where `d` is never read elsewhere); faint-variable analysis would remove them.

## Common Subexpression Elimination (CSE) - `optimizer/common_subexpression.py`
Local (per basic block) value numbering. Available expressions are keyed by `(op, left, right)` with commutative operators
normalised. An expression is invalidated when an operand **or the variable holding it** is redefined. A redundant temporary
`t2 = b + c` is deleted and its later uses forwarded to the holder; if the holder is about to be overwritten, `t2 = holder`
is re-materialised first. Non-temporary destinations become copies (`d = holder`) and holders must have the same type.
*Limitation*: expressions are not tracked across basic blocks (no global available-expressions analysis).

## Why CF and CP alone never change the instruction count
They replace an instruction by a cheaper one (`t = 10 + 20` -> `t = 30`) rather than deleting it. Their value is *enabling* DCE
(and CSE). Hence, under the instruction-count objective, S2 can never beat S1 and is never the label; S6 contains every other
strategy and can never be worse.
