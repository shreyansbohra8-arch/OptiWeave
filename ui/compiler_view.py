"""Source Editor, Compiler Explorer and Generated Code pages."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from compiler.ast_nodes import format_ast
from compiler.code_generator import GCC_INSTALL_HELP, compile_and_run, find_gcc, generate_c
from compiler.pipeline import compile_front_end
from config import settings
from ml.feature_extractor import extract_features
from optimizer.optimization_pipeline import run_strategy
from optimizer.strategies import FIXED_STRATEGY
from ui.components import code_panel, features_table, show_badge
from utils.file_utils import write_inside
from utils.validation import safe_stem

DEFAULT_SOURCE = (settings.EXAMPLES_DIR / "mixed.ow")


def init_state() -> None:
    if "source" not in st.session_state:
        st.session_state["source"] = DEFAULT_SOURCE.read_text(encoding="utf-8") if DEFAULT_SOURCE.exists() else ""
    st.session_state.setdefault("frontend", None)
    st.session_state.setdefault("opt_result", None)


def _load_example(name: str) -> None:
    st.session_state["source"] = (settings.EXAMPLES_DIR / name).read_text(encoding="utf-8")
    st.session_state["frontend"] = None
    st.session_state["opt_result"] = None


def current_frontend():
    """Compile the current source if needed; returns FrontEndResult or None."""
    fe = st.session_state.get("frontend")
    if fe is None or fe.source != st.session_state["source"]:
        return None
    return fe


def _report_errors(fe) -> None:
    show_badge(f"Compilation stopped at the {fe.failed_stage} stage", "err")
    for e in fe.errors:
        st.error(e)
    st.caption("Invalid programs never reach optimization or code generation.")


def render_source_editor() -> None:
    st.header("Source Editor")
    init_state()
    examples = sorted(p.name for p in settings.EXAMPLES_DIR.glob("*.ow"))
    c1, c2 = st.columns([2, 2])
    with c1:
        choice = st.selectbox("Load an example", ["-"] + examples, key="example_choice")
        if choice != "-" and st.session_state.get("_last_example") != choice:
            st.session_state["_last_example"] = choice
            _load_example(choice)
            st.rerun()
    with c2:
        up = st.file_uploader("...or upload a .ow file", type=["ow"])
        if up is not None and st.session_state.get("_last_upload") != (up.name, up.size):
            try:
                text = up.getvalue().decode("utf-8")
            except UnicodeDecodeError:
                st.error("Uploaded file is not valid UTF-8 text.")
            else:
                st.session_state["_last_upload"] = (up.name, up.size)
                st.session_state["source"] = text
                st.session_state["frontend"] = None
                st.rerun()
    st.text_area("OptiWeave source", key="source", height=340)
    b1, b2, _ = st.columns([1, 1, 3])
    run = b1.button("Compile", type="primary")
    b2.download_button("Download .ow", st.session_state["source"], file_name="program.ow")
    if run:
        st.session_state["frontend"] = compile_front_end(st.session_state["source"])
        st.session_state["opt_result"] = None
    fe = current_frontend()
    if fe is None:
        st.info("Press **Compile** to run lexical analysis, parsing, semantic analysis and IR generation.")
    elif not fe.ok:
        _report_errors(fe)
    else:
        show_badge("Compiled successfully", "ok")
        st.write(f"{len(fe.tokens)} tokens - {len(fe.symbols.all_symbols())} variables - "
                 f"{fe.ir.instruction_count} IR instructions - {len(fe.cfg.blocks)} basic blocks. "
                 "Open **Compiler Explorer** for details.")


def render_compiler_explorer() -> None:
    st.header("Compiler Explorer")
    init_state()
    fe = current_frontend()
    if fe is None:
        st.info("Compile a program in **Source Editor** first.")
        return
    if not fe.ok:
        _report_errors(fe)
        return
    tabs = st.tabs(["Tokens", "AST", "Symbol table", "Original 3AC", "Basic blocks", "CFG", "Features"])
    with tabs[0]:
        st.dataframe(pd.DataFrame([{"type": t.type.name, "lexeme": t.lexeme, "line": t.line, "column": t.column}
                                   for t in fe.tokens]), hide_index=True)
    with tabs[1]:
        code_panel(format_ast(fe.ast))
    with tabs[2]:
        st.dataframe(pd.DataFrame([{"name": s.name, "type": s.type, "declared at line": s.line,
                                    "scope depth": s.scope_level} for s in fe.symbols.all_symbols()]),
                     hide_index=True)
    with tabs[3]:
        code_panel(fe.ir.to_text(numbered=True))
        st.caption(f"{fe.ir.instruction_count} instructions (labels are markers and are not counted).")
    with tabs[4]:
        for b in fe.cfg.blocks:
            succ = ", ".join(f"B{s}" for s in fe.cfg.successors[b.id]) or "-"
            pred = ", ".join(f"B{p}" for p in fe.cfg.predecessors[b.id]) or "-"
            with st.expander(f"{b.name}   preds: {pred}   succs: {succ}", expanded=False):
                code_panel(b.to_text())
    with tabs[5]:
        st.graphviz_chart(fe.cfg.to_dot())
        st.caption(f"Edges: {fe.cfg.edge_count}. Red edges are loop back-edges "
                   f"({len(fe.cfg.back_edges())} found via dominators). DOT source below.")
        with st.expander("DOT source"):
            code_panel(fe.cfg.to_dot())
    with tabs[6]:
        st.dataframe(features_table(extract_features(fe.ir, fe.cfg)))


def render_generated_code() -> None:
    st.header("Generated Code")
    init_state()
    fe = current_frontend()
    if fe is None or not fe.ok:
        st.info("Compile a valid program in **Source Editor** first.")
        return
    opt = st.session_state.get("opt_result")
    options = ["Unoptimized IR", f"Fixed {FIXED_STRATEGY}"]
    if opt is not None and opt.original == fe.ir:
        options.append(f"Last Optimization Lab result ({opt.strategy_id})")
    which = st.radio("Which IR to translate to C?", options, horizontal=True)
    if which.startswith("Unoptimized"):
        ir = fe.ir
    elif which.startswith("Fixed"):
        ir = run_strategy(fe.ir, FIXED_STRATEGY).optimized
    else:
        ir = opt.optimized
    c_src = generate_c(ir)
    code_panel(c_src, "c")
    stem = safe_stem(which.split("(")[-1].strip(") ") or "program")
    st.download_button("Download C file", c_src, file_name=f"{stem}.c")
    if st.button("Save to outputs/generated_c"):
        path = write_inside(settings.GENERATED_C_DIR, f"{stem}.c", c_src)
        st.success(f"Saved {path}")
    st.subheader("GCC compilation (-O0)")
    if find_gcc() is None:
        show_badge("GCC not available", "warn")
        st.warning(GCC_INSTALL_HELP)
        return
    if st.button("Compile and run with GCC"):
        comp, run = compile_and_run(c_src)
        if not comp.ok:
            show_badge("GCC compilation failed", "err")
            st.code(comp.stderr or comp.message)
        else:
            show_badge("GCC compilation succeeded", "ok")
            if run is not None and run.ok:
                st.write("Program output:")
                code_panel(run.stdout)
            elif run is not None:
                show_badge("Program exited with an error", "err")
                st.code(run.stderr)
