# Architecture

```
.ow source -> Lexer -> Parser (AST, error recovery) -> Semantic analyzer (symbol table, types)
          -> 3AC generator -> Basic blocks -> CFG -> Feature extraction (14 features)
          -> Random Forest -> strategy S1..S10 -> Optimization pipeline (CF, SR, COP, CSE, CP, DCE)
          -> C code generator -> GCC -O0 -> Benchmark / reports / Streamlit UI
```

| Package | Responsibility |
|---|---|
| `compiler/` | `tokens`, `lexer`, `ast_nodes`, `parser`, `symbol_table`, `semantic_analyzer`, `ir`, `ir_generator`, `basic_blocks`, `cfg`, `code_generator` (C + GCC), `pipeline` (front-end facade), `cli` |
| `optimizer/` | one module per pass (6 passes: CF, SR, COP, CSE, CP, DCE), `strategies` (single registry of S1..S10), `optimization_pipeline` (fixed-point/iterative driver) |
| `ml/` | `feature_extractor`, `program_templates` + `dataset_generator`, `evaluation`, `train_model`, `predictor`, `model_metadata` |
| `benchmarking/` | `equivalence` (IR interpreter), `benchmark_runner`, `metrics`, `report_generator` |
| `ui/`, `app.py` | Streamlit pages; no compiler logic lives in the UI |
| `config/`, `utils/` | paths and limits; exceptions, validation, atomic file writes, logging |

## Key design decisions
* **IR**: typed dataclasses (`Assign`, `BinOp`, `UnOp`, `Label`, `Jump`, `CondJump`, `Print`) with `Var`/`Const` operands.
  `CondJump` always names both targets, so CFG construction never relies on implicit fall-through for branches.
* **Instruction count** = every instruction except `Label` (labels are markers). This is the optimisation objective.
* **Short-circuit** `&&`/`||` is lowered to control flow, so the CFG reflects real evaluation order.
* **One registry**: `optimizer/strategies.py` is imported by dataset generation, training, inference,
  benchmarking and the UI, so definitions cannot drift apart.
* **Shared semantics**: `compiler/ir.py` defines `evaluate_binop`, used by constant folding, constant propagation and the
  IR interpreter, so compile-time and run-time arithmetic agree (including 64-bit wrap-around and C-style division).
* **Interpreter + GCC**: the IR interpreter gives a fast deterministic equivalence oracle; GCC output is compared as a second check.
* **No leakage**: features are computed from the *original* IR only; the model never sees reduction columns.
