# ML Methodology

**Task**: given the 14 IR/CFG features of a program, predict which of S1..S10 gives the best **cost-aware score**
(instruction reduction penalised by compile-time cost of the passes).

## Features (14 in exact order)
**Raw features (10):**
`instruction_count, arithmetic_op_count, branch_count, loop_count, basic_block_count, constant_expression_count,
duplicate_expression_count, assignment_count, distinct_variable_count, cfg_edge_count`

**Derived ratio features (4):**
`constant_expression_ratio, duplicate_expression_ratio, assignment_ratio, branch_ratio`

Defined precisely in `ml/feature_extractor.py` and computed from the original IR only (no label leakage). Model inputs
are pandas DataFrames with these named columns; metadata stores the order and inference refuses a model with a different
feature set.

## Dataset
135 programs = 9 categories × 5 families × 3 variants (`ml/program_templates.py`, seeded, deterministic). Categories:
arithmetic-heavy, loop-heavy, branch-heavy, constant-heavy, redundant-expression-heavy, mixed, algebraic-heavy,
copy-heavy, propagation-only. Each program is compiled, interpreted, and optimised with all ten strategies; behaviour
preservation is asserted for every strategy.

**Label selection**: cost-aware score = `instruction_reduction_% - 0.5 × strategy_cost`. Ties → fewer passes → lower
strategy number. Category is never used to pick labels.

Files: `data/benchmarks/datasets/optiweave_dataset.csv` (one row per program: ids, 14 features, `reduction_S1..S10`,
`score_S1..S10`, label, counts) and `data/benchmarks/datasets/results.csv` (long format: program, strategy, counts,
reduction, cost-aware score, equivalence). The `reduction_*` and `score_*` columns are **never** model inputs (leakage).

## Evaluation
* `GroupKFold` (5 splits) with the **program family** as group, so the three variants of a family never straddle
  train/test. The code asserts no family appears on both sides. Metrics use out-of-fold predictions.
* Reported: accuracy, balanced accuracy, macro/weighted F1, confusion matrix (all ten labels), classification report.
* Baselines: majority class of the training fold; fixed S10; oracle (best strategy per program, an upper bound); fixed S1.
* Both **instruction reduction %** and **cost-aware score** are reported for each selector.
* In-sample accuracy of the final model is stored but explicitly labelled as not a generalisation measure.

## Hyperparameter Comparison
Six model configurations are compared via GroupKFold:
- Random Forest (200 trees, 500 trees, depth-limited, min-samples-leaf)
- Gradient Boosting (200 trees)
- Decision Tree (for interpretability comparison)

Results stored in `data/results/ml_evaluation.json` under `hyperparameter_search`.

## Key Result: ML Beats S10
Under the cost-aware objective, ML-selected strategies **outperform** fixed S10 on the majority of programs.
This is because ML can choose lighter strategies (e.g., S1, S3, S4) when the heavier passes in S10 provide
negligible additional reduction, avoiding their compile-time cost penalty.

## Honest limitations
* 135 programs / 45 families from templates written by the same author: results describe this synthetic corpus, not real software.
* Folds contain only nine families each; accuracy has moderate variance.
* Classes with very few winning programs may be underrepresented in training labels.
* The cost-aware weight (0.5) and per-pass costs are heuristic; a different weighting could change strategy rankings.
