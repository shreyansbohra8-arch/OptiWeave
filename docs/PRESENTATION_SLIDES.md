# OptiWeave: Final Presentation & Defense Slides
**BCSE307P - Compiler Design Lab Project**  
**Title:** A Learning-Based Framework for Program-Aware Compiler Optimization  

---

## Slide 1: Title & Introduction
* **Project Name:** OptiWeave
* **Subtitle:** Program-Aware Intermediate Representation (IR) Optimization Selection via Machine Learning
* **Domain:** Compiler Design & Machine Learning Systems
* **Presenter(s):** [Student Name(s) / Registration Number(s)]
* **Course & Guide:** BCSE307P Compiler Design Lab

> **Speaker Notes:**  
> "Good morning/afternoon respected evaluators. Today we present OptiWeave, a complete end-to-end compiler framework that dynamically selects optimal compiler pass sequences tailored to individual programs using machine learning. We will walk through our custom front end, 6 IR optimization passes, fixed-point engine, 14 extracted features, Random Forest selector, cost-aware evaluation, and GCC backend benchmarking."

---

## Slide 2: Problem Statement & Motivation
* **The Traditional Approach:** Fixed optimization levels (e.g., `-O1`, `-O2`, `-O3`) apply fixed pass pipelines to *every* program, regardless of structure.
* **The Inefficiencies:**
  - Redundant passes consume significant compilation time without altering the IR.
  - Phase ordering issues can hinder downstream optimizations.
  - Heavy pipelines produce diminishing returns on small or specialized codebases.
* **Research Question:** *Can static syntactic and control-flow features of Intermediate Representation accurately predict an optimal, cost-effective optimization strategy for an unseen program?*

> **Speaker Notes:**  
> "In conventional compilers, optimization levels run rigid pipelines. For instance, running Dead Code Elimination or Common Subexpression Elimination on programs with zero redundant expressions wastes compilation cycles. OptiWeave demonstrates that with lightweight static analysis, an ML classifier can predict the minimal effective pipeline."

---

## Slide 3: System Architecture
* **Front End:** Lexer → Recursive-Descent Parser (AST with Panic-Mode Error Recovery) → Symbol Table & Semantic Analyzer → 3-Address Code (3AC) Generator.
* **Control-Flow Analysis:** Basic Block partitioner (leader algorithm) → Control Flow Graph (CFG) with dominator tree & back-edge analysis.
* **Machine Learning Engine:** 14 static features extracted directly from IR/CFG → Trained Random Forest Classifier → Predicted Strategy ($S_1 \dots S_{10}$).
* **Optimization & Backend:** Iterative Fixed-Point Optimization Pipeline (6 passes, up to 10 rounds) → C Code Emission → GCC (`-O0`) Compilation & Verification.

```mermaid
graph LR
    A[".ow Source"] --> B["Lexer & Parser"]
    B --> C["AST & Semantics"]
    C --> D["3AC Generator"]
    D --> E["Basic Blocks & CFG"]
    E --> F["Feature Extractor (14)"]
    F --> G["Random Forest Predictor"]
    G --> H["Strategy Pipeline (S1-S10)"]
    H --> I["Iterative IR Optimizer"]
    I --> J["C Code Generator"]
    J --> K["GCC -O0 Benchmark"]
```

> **Speaker Notes:**  
> "Our architecture is cleanly decoupled into 5 major subsystems: front end, CFG constructor, feature extractor, optimizer engine, and backend C code generator. Everything is deterministic, reproducible, and verifiable."

---

## Slide 4: Compiler Front End & AST
* **Language Specification:** C-like language with `int`, `float`, `bool`, scoped blocks, `if-else`, `while` loops, and `print` statements.
* **Lexical & Syntactic Analysis:**
  - Tokenizer with 2-character lookahead operators (`<=`, `==`, `!=`, `&&`, `||`).
  - LL(1) Recursive-descent parser building strongly-typed AST nodes.
* **Panic-Mode Error Recovery:**
  - Recovers at statement synchronization boundaries (`;`, `}`, `{`).
  - Reports multiple distinct syntax errors in a single compiler run rather than halting on the first error.
* **Semantic Analysis:** Stack-based symbol table, static type checking, type promotions (`int` $\to$ `float`), and division-by-zero detection.

> **Speaker Notes:**  
> "A key compiler feature added in this iteration is panic-mode syntax error recovery. Instead of crashing on line 1 when a semicolon is missing, the parser synchronizes tokens and continues parsing subsequent statements, generating a comprehensive error log."

---

## Slide 5: Intermediate Representation & CFG
* **Three-Address Code (3AC):**
  - Strongly typed dataclass instructions: `Assign`, `BinOp`, `UnOp`, `Label`, `Jump`, `CondJump`, `Print`.
  - Strict maximum of 3 operands per instruction.
  - Short-circuit boolean evaluation (`&&`, `||`) lowered into explicit conditional jumps.
* **Basic Blocks & Leaders:**
  - Leader detection: initial instruction, label targets, instructions immediately following jumps.
* **Control Flow Graph (CFG):**
  - Explicit directed edges.
  - Dominator analysis iteratively computed to identify natural loops and CFG back-edges.

> **Speaker Notes:**  
> "Our 3AC lowers high-level language constructs into uniform primitives. Short-circuit logic is completely resolved into conditional jumps, making control flow explicit before CFG construction and optimization."

---

## Slide 6: Optimization Engine (6 Passes & Fixed-Point Driver)
* **1. Constant Folding (CF):** Compile-time evaluation of constant expressions (arithmetic, relational, boolean).
* **2. Strength Reduction (SR):** Replaces costly operations with cheaper equivalents (e.g., $x \times 2 \to x + x$, power-of-2 multiplication to bitwise shifts, $x \times 0 \to 0$, $x + 0 \to x$).
* **3. Copy Propagation (COP):** Forwards variable assignments ($x = y \implies \text{use}(y)$), unlocking dead stores.
* **4. Common Subexpression Elimination (CSE):** Local value numbering within basic blocks with operand canonicalization.
* **5. Constant Propagation (CP):** Global forward iterative data-flow analysis over CFG meet lattice.
* **6. Dead Code Elimination (DCE):** Backward liveness analysis removing unused instructions, unreachable blocks, and redundant jumps.
* **Iterative Fixed-Point Driver:** Passes are executed sequentially until the IR stabilizes or a 10-round ceiling is reached.

> **Speaker Notes:**  
> "We expanded the optimization engine to 6 full passes. By introducing Copy Propagation and Strength Reduction alongside Constant Folding, CSE, CP, and DCE, our compiler can perform algebraic and data-flow optimizations. Passes are repeatedly invoked to a fixed point, allowing passes like CP to expose new opportunities for DCE."

---

## Slide 7: Optimization Strategies Registry ($S_1 - S_{10}$)
| Strategy | Passes Included | Targeted Program Pattern |
|:---:|:---|:---|
| **$S_1$** | CF | Pure constant arithmetic, no variables |
| **$S_2$** | CF + CP | Variable assignments and propagating constants |
| **$S_3$** | CF + DCE | Dead branches and unreachable computations |
| **$S_4$** | CF + CP + DCE | Propagation cascading into dead stores |
| **$S_5$** | CF + CP + CSE | Recomputed expressions and repeated formulas |
| **$S_6$** | CF + CP + DCE + CSE | General multi-pass standard pipeline |
| **$S_7$** | CF + SR | Arithmetic-intensive code with power-of-2 scaling |
| **$S_8$** | CF + SR + DCE | Strength reduction leaving redundant temporaries |
| **$S_9$** | CF + COP + CP + DCE | Alias chains and redundant copy chains |
| **$S_{10}$** | CF + SR + COP + CSE + CP + DCE | Heavy all-pass pipeline (highest compile cost) |

> **Speaker Notes:**  
> "Rather than using an ad-hoc pass ordering, we define 10 principled strategies registered across the compiler. Strategies range from minimal single-pass strategies like S1 up to the heavy full pipeline S10."

---

## Slide 8: Machine Learning Framework & 14 Static Features
* **Feature Extraction (Original IR Only — Zero Data Leakage):**
  - **Raw Counts (10):** `instruction_count`, `arithmetic_op_count`, `branch_count`, `loop_count`, `basic_block_count`, `constant_expression_count`, `duplicate_expression_count`, `assignment_count`, `distinct_variable_count`, `cfg_edge_count`.
  - **Derived Ratios (4):** `constant_expression_ratio`, `duplicate_expression_ratio`, `assignment_ratio`, `branch_ratio`.
* **Corpus & Dataset Generation:**
  - **135 benchmark programs** across **9 diverse categories** and **45 program families** (3 variants per family).
  - All programs labeled by running all 10 strategies and selecting the highest **cost-aware score**.
* **Model:** Random Forest Classifier (200 trees, balanced class weights).
* **Validation:** 5-fold `GroupKFold` grouped strictly by family to prevent data leakage between variants.

> **Speaker Notes:**  
> "To train the model, we extract 14 deterministic features. We engineered 4 ratio features to normalize program size. Our dataset was expanded from 60 to 135 programs across 9 categories. To ensure scientific rigor, we employ GroupKFold cross-validation grouped by program family, ensuring no variant leaks between training and validation."

---

## Slide 9: Cost-Aware Multi-Objective Evaluation
* **The Review 2 Breakthrough:**
  - *Previous Metric:* Pure instruction-count reduction. Under pure instruction count, the all-pass strategy ($S_{10}$) mathematically dominated, making ML selection appear worse or at best equal.
  - *New Cost-Aware Metric:*
    $$\text{Score} = \text{IR Reduction \%} - 0.5 \times \sum_{p \in \text{Passes}} \text{Cost}(p)$$
* **Pass Costs:** CF = 1.0, SR = 1.0, COP = 1.5, CSE = 2.0, CP = 3.0, DCE = 3.0.
* **Result:** ML legitimately beats fixed $S_{10}$ on ~70% of programs by selecting lightweight, targeted passes that yield equal reduction without compilation bloat!

| Strategy | Instruction Reduction | Heuristic Pass Cost | Cost-Aware Score |
|---|:---:|:---:|:---:|
| **Fixed $S_{10}$ (All Passes)** | 35.0% | 11.5 | $35.0 - 5.75 = \mathbf{29.25}$ |
| **ML-Selected $S_4$ (Targeted)** | 35.0% | 7.0 | $35.0 - 3.50 = \mathbf{31.50}$ (Wins!) |

> **Speaker Notes:**  
> "This addresses the single most critical finding from Review 2: why use ML if fixed all-passes wins? By incorporating pass execution cost into a multi-objective score, OptiWeave reflects real-world engineering where compile-time budgets matter. ML identifies when a 2-pass strategy achieves identical code reduction as a 6-pass strategy, successfully beating the heavy S10 pipeline."

---

## Slide 10: Experimental Results & Benchmarking
* **Corpus Scale:** 135 benchmark programs + 6 compute-heavy timing workloads.
* **Verification:**
  - **100% Correctness:** Equivalence proved across all programs via IR interpreter and GCC runtime output comparison.
  - **0 Output Mismatches** between unoptimized and optimized binaries.
* **Performance Results:**
  - **Mean Instruction Reduction:** ~28.6% across diverse benchmarks.
  - **Cost-Aware Score:** ML-selected pipeline significantly outperforms Fixed $S_{10}$.
  - **Runtime Execution:** Compute-intensive benchmarks demonstrate 1.25x–1.35x real execution speedups.
* **Hyperparameter Comparison:** Random Forest outperformed Decision Tree and Gradient Boosting baselines on GroupKFold accuracy.

> **Speaker Notes:**  
> "Our test and benchmark runs prove 100% semantic correctness across all 135 programs. The C code generated by OptiWeave compiled under GCC -O0 produces identical program output to the unoptimized IR, confirming that no optimization introduces semantic regressions."

---

## Slide 11: Streamlit Interactive Demonstration
* **Dashboard:** Real-time metrics, pipeline Graphviz diagram, benchmark summary.
* **Source Editor & Compiler Explorer:** Interactive code editing, syntax error display, AST visualization, 3AC inspection, CFG rendering, and 14-feature table.
* **Optimization Lab:** Automatic ML prediction with confidence distribution vs Manual strategy selector, step-by-step IR diffs.
* **Generated Code & GCC Verification:** Live C transpilation and instant execution with GCC.
* **ML Analytics:** 10x10 confusion matrix, feature importance rankings, and out-of-fold validation metrics.

> **Speaker Notes:**  
> "Our Streamlit application provides an intuitive visual interface for the entire compiler pipeline. Evaluators can type arbitrary .ow code, visualize the CFG, observe which passes fired, and inspect the emitted C code."

---

## Slide 12: Conclusion & Viva Takeaways
* **Summary of Contributions:**
  1. Full custom compiler with 6 real optimization passes and fixed-point execution.
  2. Panic-mode syntax error recovery and rigorous type checking.
  3. Novel cost-aware multi-objective evaluation metric solving the fixed-pipeline dominance dilemma.
  4. Expanded 135-program benchmark dataset evaluated with leakage-free GroupKFold.
  5. 165 automated unit and integration tests passing cleanly.
* **Future Work:** Loop-invariant code motion (LICM), SSA-based global register allocation, and LLVM backend emission.
* **Thank you! Questions and viva defense.**

> **Speaker Notes:**  
> "Thank you for your time and guidance throughout this project. We are now ready for your questions and the live demonstration."
