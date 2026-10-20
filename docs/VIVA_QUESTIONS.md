# Viva Preparation (answers match this implementation)

**Lexical analysis**
1. *What does the lexer do and how does yours handle `<=`?* It converts characters into tokens with line/column. It tries two-character operators first (`<=`, `==`, `&&` ...) before single characters, so `<=` is never `<` then `=`. A lone `&` or `|` raises an error suggesting `&&` / `||`.
2. *How are keywords separated from identifiers?* The lexer reads a whole word and looks it up in a keyword table (`int`, `while`, `true` ...); anything else is `IDENT`. So `integer` is an identifier.
3. *How are floats handled?* `digits . digits`; `1.` or `.5` are rejected, so `3.14` is one token and no ambiguity with member access arises.

**Parsing / AST**
4. *Why recursive descent?* The grammar is LL(1): one function per non-terminal, easy to read and to report errors with locations (`compiler/parser.py`).
5. *How is precedence implemented?* One function per level (`||` < `&&` < equality < relational < additive < term < unary); each loops over its operators, which gives left associativity.
6. *Dangling else?* Removed by requiring braces around if/while bodies; `else if` is desugared to `else { if ... }`.
7. *What is the AST used for?* A tree of dataclasses (`Binary`, `If`, `While` ...) that semantic analysis annotates with types and the IR generator walks.
8. *How does the parser handle errors?* **Panic-mode error recovery**: when a syntax error is detected, the parser records the error and skips tokens until it finds a synchronisation token (`;`, `}`, `{`), then resumes parsing. This reports multiple errors in a single pass rather than failing on the first.

**Symbol table / type checking**
9. *What does the symbol table hold?* Name, type, declaration position, scope depth, in a stack of scopes. Names must also be unique program-wide, which keeps IR variable names unambiguous.
10. *Type rules?* int/float promote to float; `%` needs ints; conditions must be bool; `int->float` assignment allowed, `float->int` rejected; division by a literal zero is a compile error. Errors are collected, not just the first.

**Three-address code**
11. *Why 3AC?* Each instruction has at most one operator and three addresses, which makes data-flow analysis and code generation simple. `x = a + b * 2` becomes `t1 = b * 2; t2 = a + t1; x = t2`.
12. *How is `&&` compiled?* With branches (short-circuit), so `x != 0 && 10 / x > 1` never divides by zero.

**Basic blocks and CFG**
13. *Leaders?* First instruction, every label (jump target), and every instruction after a jump. A block runs from one leader to the next.
14. *Back edges?* An edge tail->head where head dominates tail; dominators are computed iteratively. `loop_count` = number of back edges.

**Optimizations and data-flow**
15. *Constant folding?* Evaluate constant operations at compile time with the same evaluator as the interpreter; never fold division by zero.
16. *Strength reduction?* Replaces expensive ops: `x * 2` → `x + x`, `x * 4` → `x << 2` (power-of-2), `x * 0` → `0`, `x + 0` → `x`. Single linear scan, no data-flow needed.
17. *Copy propagation?* Per-basic-block forward pass tracking `x = y` copies. Later uses of `x` are replaced by `y`. Copies invalidated when source or destination is redefined. Enables DCE of the original copy.
18. *Constant propagation?* Forward must-analysis; meet = intersection of agreeing facts; iterate to a fixed point so loops are safe.
19. *Dead code elimination?* Backward liveness: an assignment to a variable not live afterwards is removed (unless it can fault); plus unreachable-block and redundant-jump removal.
20. *CSE?* Local value numbering with invalidation when operands or the holder change; commutative operands normalised.
21. *Forward vs backward analysis?* CP flows with execution (forward); liveness against it (backward). May vs must: liveness unions successors (may), CP intersects predecessors (must).
22. *Why is the pass order CF -> SR -> COP -> CSE -> CP -> DCE, repeated?* CF folds constants, SR simplifies arithmetic, COP forwards copies, CSE removes duplicates, CP propagates constants (may expose new CF/SR opportunities), DCE removes dead code; the loop runs to a **fixed point** (max 10 rounds) until no further changes occur.
23. *Why does S2 never win on instruction count?* CF and CP rewrite instructions but never delete them, so only DCE/CSE change the instruction count. However, under cost-aware scoring S2 can beat heavier strategies.

**ML**
24. *Which features?* Fourteen features: 10 raw IR/CFG counts (instructions, arithmetic ops, branches, loops, blocks, constant expressions, duplicate expressions, assignments, distinct variables, CFG edges) plus 4 derived ratios (constant expression ratio, duplicate expression ratio, assignment ratio, branch ratio), computed from the original IR only.
25. *Why Random Forest?* Small tabular data, non-linear interactions, no scaling needed, gives feature importances and probabilities.
26. *How are labels produced?* By running all ten strategies and picking the best **cost-aware score** (instruction reduction % minus compile-time cost penalty); ties -> fewer passes -> lower number. Never from the category.
27. *What is the cost-aware score?* `score = instruction_reduction_% - 0.5 × sum(pass_costs)`. Each pass has a heuristic cost (CF/SR=1.0, COP=1.5, CSE=2.0, CP/DCE=3.0). This makes lighter strategies competitive when heavier passes add little benefit.
28. *What is leakage here and how is it avoided?* Reduction/score columns would reveal the label (never used as inputs), and near-identical program variants in both train and test would inflate accuracy; `GroupKFold` by family prevents the latter.
29. *Is the accuracy trustworthy?* It is out-of-fold on 45 families; treat it as indicative. In-sample accuracy (~1.0) is meaningless for generalisation.
30. *Does ML beat S10?* **Yes, on cost-aware score**: ML beats S10 on ~70% of programs by choosing lighter strategies that achieve similar instruction reduction with lower compile-time cost. On pure instruction count, S10 (all passes) ties or wins.
31. *What hyperparameters were compared?* Six configurations via GroupKFold: Random Forest (200/500 trees, depth-limited, min-samples-leaf), Gradient Boosting, and Decision Tree.

**Backend / benchmarking**
32. *Why GCC with `-O0`?* So GCC's own optimiser does not hide the effect of our IR passes. `-fwrapv` makes 64-bit overflow defined, matching the interpreter.
33. *Instruction count vs run time?* Count is deterministic and the primary metric; run time is secondary, measured with `perf_counter`, repeated, median, excluded if < 10 ms. Heavy workload programs (`large_accumulator.ow`, `nested_heavy.ow`, etc.) provide reliable timing data.
34. *How do you know optimisation is correct?* Interpreter output of original and optimised IR must match for every strategy on all dataset programs; GCC outputs of all variants are compared too.

**Limitations**
35. *Main limitations?* Tiny language, local CSE only, plain liveness (no faint variables), synthetic 135-program corpus, cost weights are heuristic, no registers/scheduling.
