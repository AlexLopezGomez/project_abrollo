from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st

from components.data_loader import (
    get_dag,
    get_hypotheses,
    get_portfolio,
    get_submission_history,
    load_submission,
)
from components.tab_graph import render_graph_tab
from components.tab_history import render_history_tab
from components.tab_hypotheses import render_hypotheses_tab
from components.tab_returns import render_returns_tab
from components.ui import chip, install_theme, render_hero


def _format_money(value: object) -> str:
    if value is None:
        return "—"
    return f"${float(value):,.2f}"


def _format_money_compact(value: object) -> str:
    if value is None:
        return "—"
    number = float(value)
    if abs(number) >= 1_000_000:
        return f"${number / 1_000_000:.2f}M"
    if abs(number) >= 1_000:
        return f"${number / 1_000:.1f}K"
    return f"${number:,.0f}"


def _format_pct(value: object) -> str:
    if value is None:
        return "—"
    return f"{float(value):+.2f}%"


def _format_run_option(row: dict) -> str:
    timestamp = row.get("timestamp")
    date_text = timestamp.strftime("%Y-%m-%d %H:%M") if hasattr(timestamp, "strftime") else "sin fecha"
    return_pct = _format_pct(row.get("return_pct"))
    return f"{date_text} · {row.get('pipeline', '—')} · {return_pct}"


st.set_page_config(
    page_title="Abrollo — Portfolio Dashboard",
    page_icon="AB",
    layout="wide",
    initial_sidebar_state="expanded",
)
install_theme()

history = get_submission_history()
if not history:
    st.error("No se encontraron submissions en data/submissions/.")
    st.stop()

history_by_filename = {row["filename"]: row for row in history}
run_labels_by_filename = {
    filename: _format_run_option(row)
    for filename, row in history_by_filename.items()
}
filename_by_run_label = {
    label: filename
    for filename, label in run_labels_by_filename.items()
}

st.sidebar.markdown('<div class="ab-sidebar-title">Run selector</div>', unsafe_allow_html=True)
selected_option = st.sidebar.radio(
    "Lanzamiento",
    [row["filename"] for row in history],
    index=0,
    format_func=lambda filename: run_labels_by_filename.get(filename, filename),
)
selected_filename = filename_by_run_label.get(selected_option, selected_option)
selected_run = history_by_filename[selected_filename]
submission_data, submission_file = load_submission(selected_filename)
artifact_key = selected_run.get("artifact_key", "mvp2")
artifact_label = selected_run.get("artifact_label", artifact_key)
hypotheses = get_hypotheses(artifact_key)
dag = get_dag(artifact_key, hypotheses)
portfolio = get_portfolio(artifact_key)

sid = (submission_data.get("response") or {}).get("submission_id", "—")
snapshot_status = selected_run.get("snapshot_status", "legacy")
pipeline = selected_run.get("pipeline", "—")
run_label = _format_run_option(selected_run)

st.sidebar.divider()
st.sidebar.markdown('<div class="ab-sidebar-title">Selected run</div>', unsafe_allow_html=True)
st.sidebar.caption(f"Archivo: `{submission_file}`")
st.sidebar.caption(f"Submission ID: `{sid}`")
st.sidebar.caption(f"Artefactos: `{artifact_label}`")
st.sidebar.caption(f"Snapshot: `{snapshot_status}`")
st.sidebar.metric("Valor final", _format_money_compact(selected_run.get("total_value")))
st.sidebar.metric("Retorno", _format_pct(selected_run.get("return_pct")))
st.sidebar.metric("Transacciones", str(selected_run.get("n_transactions", "—")))
st.sidebar.divider()
st.sidebar.markdown('<div class="ab-sidebar-title">Artifact health</div>', unsafe_allow_html=True)
st.sidebar.caption(f"Hipótesis: `{len(hypotheses)}`")
st.sidebar.caption(f"Solver: `{portfolio.get('solver', '—')}`")
st.sidebar.caption(f"Tickers: `{portfolio.get('n_nonzero_tickers', '—')}`")

render_hero(
    title="Monte Carlo Cathedral",
    subtitle=(
        "Selector histórico, submissions, hipótesis Claude, Knowledge Graph y cartera final "
        "sobre los artefactos reales del pipeline Abrollo."
    ),
    run_label=run_label,
    total_value=_format_money(selected_run.get("total_value")),
    return_pct=_format_pct(selected_run.get("return_pct")),
    chips=[
        chip(str(pipeline)),
        chip(str(snapshot_status), "good" if snapshot_status == "snapshotted" else "warn"),
        chip(f"submission {sid[:12]}…" if sid and sid != "—" else "sin submission id"),
        chip(f"{len(hypotheses)} hipótesis"),
        chip(f"{portfolio.get('n_nonzero_tickers', '—')} tickers"),
        chip(f"solver {portfolio.get('solver', '—')}"),
    ],
)

tab1, tab2, tab3, tab4 = st.tabs(["Returns", "Historial", "Knowledge Graph", "Hipótesis de Claude"])

with tab1:
    render_returns_tab(submission_data, portfolio)

with tab2:
    render_history_tab(history, submission_file)

with tab3:
    render_graph_tab(dag, portfolio, artifact_key)

with tab4:
    render_hypotheses_tab(hypotheses, dag, portfolio)
