"""Shared Streamlit UI helpers (styling, badges, cached loaders)."""
from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from config import settings
from ml.predictor import StrategyPredictor

CSS = """
<style>
.block-container {padding-top: 2rem; max-width: 1200px;}
h1, h2, h3 {letter-spacing: -0.01em;}
.ow-badge {display:inline-block; padding:2px 10px; border-radius:999px; font-size:0.8rem; font-weight:600;}
.ow-ok {background:#e3f6ec; color:#14683f;}
.ow-warn {background:#fff3d6; color:#8a5a00;}
.ow-err {background:#fde4e4; color:#9b1c1c;}
.ow-info {background:#e6efff; color:#1e429f;}
.ow-card {border:1px solid rgba(128,128,128,0.25); border-radius:10px; padding:0.9rem 1.1rem; margin-bottom:0.6rem;}
code, pre {font-family: 'JetBrains Mono','Consolas','Menlo',monospace !important; font-size: 0.86rem;}
</style>
"""

PIPELINE_DOT = """
digraph P { rankdir=LR; node [shape=box, style="rounded,filled", fillcolor="#eef3ff", fontname="Helvetica", fontsize=10];
 src [label=".ow source"]; lex [label="Lexer"]; par [label="Parser\\n(AST)"]; sem [label="Semantic\\nAnalyzer"];
 ir [label="3AC IR"]; cfg [label="Basic blocks\\n+ CFG"]; feat [label="14 features"]; rf [label="Random Forest\\nstrategy S1-S10"];
 opt [label="Optimizer\\nCF/SR/COP/CSE/CP/DCE"]; cg [label="C codegen"]; gcc [label="GCC -O0"]; bm [label="Benchmark\\n+ reports"];
 src->lex->par->sem->ir->cfg->feat->rf->opt->cg->gcc->bm; }
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def badge(text: str, kind: str = "info") -> str:
    return f'<span class="ow-badge ow-{kind}">{text}</span>'


def show_badge(text: str, kind: str = "info") -> None:
    st.markdown(badge(text, kind), unsafe_allow_html=True)


def code_panel(text: str, language: str = "text") -> None:
    st.code(text if text else "(empty)", language=language, line_numbers=False)


@st.cache_resource(show_spinner=False)
def _load_predictor() -> StrategyPredictor:
    return StrategyPredictor.load()


def get_predictor() -> StrategyPredictor:
    """Cached predictor; raises ModelNotFoundError / IncompatibleModelError."""
    return _load_predictor()


def clear_model_cache() -> None:
    _load_predictor.clear()


def read_json(path: Path) -> dict | None:
    if not Path(path).exists():
        return None
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def benchmark_program_count() -> int:
    return len(list(settings.BENCHMARK_DIR.glob("*.ow")))


def features_table(features: dict):
    import pandas as pd
    return pd.DataFrame({"#": range(1, len(features) + 1), "feature": list(features),
                         "value": list(features.values())}).set_index("#")
