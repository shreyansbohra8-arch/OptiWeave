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
from ui.components import code_panel, features_table, get_predictor, show_badge
from utils.exceptions import IncompatibleModelError, ModelNotFoundError
from utils.file_utils import write_inside
from utils.validation import safe_stem

DEFAULT_SOURCE = (settings.EXAMPLES_DIR / "mixed.ow")
# Persistent store. Must NOT be a widget key: Streamlit deletes widget keys when
# the widget is not rendered, which previously reset the program to mixed.ow
# every time the user left Source Editor.
PROGRAM_SOURCE_KEY = "program_source"
SOURCE_WIDGET_KEY = "_source_editor"


def init_state() -> None:
    if PROGRAM_SOURCE_KEY not in st.session_state:
        fe = st.session_state.get("frontend")
        inherited = getattr(fe, "source", None) if fe is not None else None
        if inherited:
            st.session_state[PROGRAM_SOURCE_KEY] = inherited
        else:
            st.session_state[PROGRAM_SOURCE_KEY] = (
                DEFAULT_SOURCE.read_text(encoding="utf-8") if DEFAULT_SOURCE.exists() else ""
            )
            st.session_state["program_name"] = (
                DEFAULT_SOURCE.name if DEFAULT_SOURCE.exists() else "untitled.ow"
            )
    st.session_state.setdefault("program_name", "untitled.ow")
    st.session_state.setdefault("frontend", None)
    st.session_state.setdefault("opt_result", None)
    st.session_state.setdefault("opt_source", None)
    st.session_state.setdefault("lab_mode", "Automatic (ML Random Forest)")
    st.session_state.setdefault("lab_manual_strategy", "S6")


def current_source() -> str:
    return st.session_state.get(PROGRAM_SOURCE_KEY, "")


def _set_source(text: str, name: str | None = None) -> None:
    st.session_state[PROGRAM_SOURCE_KEY] = text
    if SOURCE_WIDGET_KEY in st.session_state:
        st.session_state[SOURCE_WIDGET_KEY] = text
    if name:
        st.session_state["program_name"] = name
    st.session_state["frontend"] = None
    st.session_state["opt_result"] = None
    st.session_state["opt_source"] = None


def _sync_editor() -> None:
    st.session_state[PROGRAM_SOURCE_KEY] = st.session_state[SOURCE_WIDGET_KEY]


def _load_example(name: str) -> None:
    _set_source((settings.EXAMPLES_DIR / name).read_text(encoding="utf-8"), name)


def current_frontend():
    """Return the compiled front end for the active source, or None if stale/missing."""
    fe = st.session_state.get("frontend")
    if fe is None or fe.source != current_source():
        return None
    return fe


def current_opt_result():
    """Optimization result for the currently compiled program, or None if stale."""
    fe = current_frontend()
    opt = st.session_state.get("opt_result")
    if fe is None or opt is None:
        return None
    if st.session_state.get("opt_source") != fe.source:
        return None
    return opt


def _apply_ml_optimization(fe) -> None:
    if not fe.ok or fe.ir is None or fe.cfg is None:
        st.session_state["opt_result"] = None
        st.session_state["opt_source"] = None
        return
    try:
        pred = get_predictor().predict(extract_features(fe.ir, fe.cfg))
        st.session_state["opt_result"] = run_strategy(fe.ir, pred.strategy_id)
        st.session_state["opt_source"] = fe.source
    except (ModelNotFoundError, IncompatibleModelError):
        st.session_state["opt_result"] = None
        st.session_state["opt_source"] = None


def store_opt_result(result, source: str) -> None:
    st.session_state["opt_result"] = result
    st.session_state["opt_source"] = source


def render_active_program_banner() -> None:
    name = st.session_state.get("program_name", "untitled.ow")
    fe = current_frontend()
    if fe is None:
        st.caption(f"Active source: **{name}** — compile it in **Source Editor** to use it on this page.")
        return
    opt = current_opt_result()
    extra = f" · strategy **{opt.strategy_id}**" if opt is not None else ""
    st.caption(f"Active program: **{name}** · {fe.ir.instruction_count} IR instructions{extra}")


def _report_errors(fe) -> None:
    show_badge(f"Compilation stopped at the {fe.failed_stage} stage", "err")
    for e in fe.errors:
        st.error(e)
    st.caption("Invalid programs never reach optimization or code generation.")


def render_source_editor() -> None:
    st.header("Source Editor")
    init_state()
    if SOURCE_WIDGET_KEY not in st.session_state:
        st.session_state[SOURCE_WIDGET_KEY] = current_source()
    examples = sorted(p.name for p in settings.EXAMPLES_DIR.glob("*.ow"))
    if "example_choice" not in st.session_state:
        name = st.session_state.get("program_name", "-")
        st.session_state["example_choice"] = name if name in examples else "-"
        if st.session_state["example_choice"] != "-":
            st.session_state["_last_example"] = st.session_state["example_choice"]
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
                _set_source(text, up.name)
                st.rerun()
    st.text_area("OptiWeave source", key=SOURCE_WIDGET_KEY, height=340, on_change=_sync_editor)
    _sync_editor()
    b1, b2, _ = st.columns([1, 1, 3])
    run = b1.button("Compile", type="primary")
    b2.download_button("Download .ow", current_source(), file_name=st.session_state.get("program_name", "program.ow"))
    if run:
        fe = compile_front_end(current_source())
        st.session_state["frontend"] = fe
        st.session_state["opt_result"] = None
        st.session_state["opt_source"] = None
        if fe.ok:
            _apply_ml_optimization(fe)
    fe = current_frontend()
    if fe is None:
        st.info("Press **Compile** to run lexical analysis, parsing, semantic analysis and IR generation.")
    elif not fe.ok:
        _report_errors(fe)
    else:
        show_badge("Compiled successfully", "ok")
        opt = current_opt_result()
        strategy_note = f" ML strategy {opt.strategy_id}." if opt is not None else ""
        st.write(f"{len(fe.tokens)} tokens - {len(fe.symbols.all_symbols())} variables - "
                 f"{fe.ir.instruction_count} IR instructions - {len(fe.cfg.blocks)} basic blocks."
                 f"{strategy_note} Open **Compiler Explorer** for details.")


def render_compiler_explorer() -> None:
    st.header("Compiler Explorer")
    init_state()
    render_active_program_banner()
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
    render_active_program_banner()
    fe = current_frontend()
    if fe is None or not fe.ok:
        st.info("Compile a valid program in **Source Editor** first.")
        return
    opt = current_opt_result()
    choices: list[tuple[str, str]] = []
    if opt is not None:
        choices.append(("lab", f"Optimization Lab / ML ({opt.strategy_id})"))
    choices.append(("unopt", "Unoptimized IR"))
    choices.append(("fixed", f"Fixed {FIXED_STRATEGY}"))
    labels = [label for _, label in choices]
    sig = (current_source(), tuple(labels))
    if st.session_state.get("_codegen_sig") != sig:
        st.session_state["_codegen_sig"] = sig
        st.session_state.pop("codegen_ir_choice", None)
    which = st.radio("Which IR to translate to C?", labels, horizontal=True, key="codegen_ir_choice")
    selected = next(key for key, label in choices if label == which)
    if selected == "unopt":
        ir = fe.ir
    elif selected == "fixed":
        ir = run_strategy(fe.ir, FIXED_STRATEGY).optimized
    else:
        ir = opt.optimized
    c_src = generate_c(ir)
    code_panel(c_src, "c")
    stem = safe_stem(st.session_state.get("program_name", "program").rsplit(".", 1)[0])
    if selected == "lab" and opt is not None:
        stem = f"{stem}_{opt.strategy_id}"
    elif selected == "fixed":
        stem = f"{stem}_{FIXED_STRATEGY}"
    else:
        stem = f"{stem}_unopt"
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
