# ML Methodology

**Task**: given the 10 IR/CFG features of a program, predict which of S1..S6 gives the largest instruction reduction.

## Features (exact order)
`instruction_count, arithmetic_op_count, branch_count, loop_count, basic_block_count, constant_expression_count,
duplicate_expression_count, assignment_count, distinct_variable_count, cfg_edge_count` - defined precisely in
`ml/feature_extractor.py` and computed from the original IR only. Model inputs are pandas DataFrames with these named
columns; metadata stores the order and inference refuses a model with a different feature set.

## Dataset
60 programs = 6 categories x 5 families x 2 variants (`ml/program_templates.py`, seeded, deterministic). Each program is
compiled, interpreted, and optimised with all six strategies; behaviour preservation is asserted for every strategy.
Label = strategy with the fewest optimised instructions; ties -> fewer passes -> lower strategy number. Category is never used to pick labels.
Files: `data/datasets/optiweave_dataset.csv` (one row per program: ids, 10 features, `reduction_S1..S6`, label, counts)
and `data/datasets/strategy_results.csv` (long format: program, strategy, counts, reduction, equivalence).
`program_id` joins them. The `reduction_*` columns are **never** model inputs (leakage).

## Evaluation
* `GroupKFold` (5 splits) with the **program family** as group, so the two variants of a family never straddle train/test.
  The code asserts no family appears on both sides. Metrics use out-of-fold predictions.
* Reported: accuracy, balanced accuracy, macro/weighted F1, confusion matrix (all six labels), classification report.
* Baselines: majority class of the training fold; fixed S6; oracle (best strategy per program, an upper bound).
* Because accuracy and optimisation quality differ (predicting S6 for an S4-labelled program still achieves the same reduction),
  the **mean instruction reduction** of each selector is reported separately.
* In-sample accuracy of the final model is stored but explicitly labelled as not a generalisation measure.

## Honest limitations
* 60 programs / 30 families from templates written by the same author: results describe this synthetic corpus, not real software.
* Folds contain only six families each; accuracy has high variance.
* S6 dominates every strategy on the objective, so the classifier can only tie S6. Its practical value would appear with a
  cost-aware objective (compile time, code size trade-offs), which this project does not model.
* Classes with no winning programs (S2) are absent from the training labels.
