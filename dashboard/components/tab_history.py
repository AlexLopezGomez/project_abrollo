from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from .ui import AMBER, GREEN, apply_plotly_theme, section_header


def render_history_tab(history: list[dict], selected_filename: str) -> None:
    if not history:
        st.info("No runs in data/submissions/.")
        return

    df = pd.DataFrame(history)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    for column in (
        "total_invested",
        "total_value",
        "return_pct",
        "n_transactions",
        "hypotheses_count",
        "graph_nodes",
        "graph_edges",
    ):
        df[column] = pd.to_numeric(df[column], errors="coerce")

    latest = df.sort_values("timestamp", ascending=False).iloc[0]
    best_return = df["return_pct"].max()
    best_value = df["total_value"].max()

    section_header("Run history", "Comparison of submissions and snapshots")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Runs", str(len(df)))
    c2.metric("Best return", _format_pct(best_return))
    c3.metric("Latest return", _format_pct(latest["return_pct"]))
    c4.metric("Best final value", _format_money(best_value))

    st.divider()

    df_chart = df.sort_values("timestamp").copy()
    df_chart["run_label"] = (
        df_chart["timestamp"].dt.strftime("%Y-%m-%d %H:%M")
        + " · "
        + df_chart["pipeline"].fillna("")
    )

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(
            x=df_chart["run_label"],
            y=df_chart["total_value"],
            name="Final value",
            mode="lines+markers",
            line=dict(color=GREEN, width=3),
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=df_chart["run_label"],
            y=df_chart["return_pct"],
            name="Return %",
            mode="lines+markers",
            line=dict(color=AMBER, width=3),
        ),
        secondary_y=True,
    )
    fig.update_layout(title="Evolution per run")
    fig.update_yaxes(title_text="Final value ($)", secondary_y=False)
    fig.update_yaxes(title_text="Return (%)", secondary_y=True)
    apply_plotly_theme(fig, height=410)
    st.plotly_chart(fig, use_container_width=True)

    section_header("Detected runs", "Runs found in data/submissions/")
    df_table = df.sort_values("timestamp", ascending=False).copy()
    df_table["Active"] = df_table["filename"] == selected_filename
    df_table["Snapshot"] = df_table["snapshot_status"].map({
        "snapshotted": "Yes",
        "legacy": "Legacy",
    }).fillna("Legacy")
    df_table = df_table[
        [
            "Active",
            "timestamp",
            "pipeline",
            "status",
            "Snapshot",
            "hypotheses_count",
            "graph_nodes",
            "graph_edges",
            "submission_id",
            "agent",
            "version",
            "total_invested",
            "total_value",
            "return_pct",
            "n_transactions",
            "filename",
        ]
    ].rename(
        columns={
            "timestamp": "Date",
            "pipeline": "Pipeline",
            "status": "Status",
            "hypotheses_count": "Hypotheses",
            "graph_nodes": "KG nodes",
            "graph_edges": "KG edges",
            "submission_id": "Submission ID",
            "agent": "Agent",
            "version": "Version",
            "total_invested": "Capital invested",
            "total_value": "Final value",
            "return_pct": "Return %",
            "n_transactions": "Transactions",
            "filename": "File",
        }
    )
    st.dataframe(
        df_table,
        use_container_width=True,
        hide_index=True,
        height=360,
        column_config={
            "Date": st.column_config.DatetimeColumn(format="YYYY-MM-DD HH:mm:ss"),
            "Capital invested": st.column_config.NumberColumn(format="$%.0f"),
            "Final value": st.column_config.NumberColumn(format="$%.2f"),
            "Return %": st.column_config.NumberColumn(format="%.2f%%"),
            "Transactions": st.column_config.NumberColumn(format="%d"),
            "Hypotheses": st.column_config.NumberColumn(format="%d"),
            "KG nodes": st.column_config.NumberColumn(format="%d"),
            "KG edges": st.column_config.NumberColumn(format="%d"),
        },
    )


def _format_money(value: object) -> str:
    if pd.isna(value):
        return "—"
    return f"${float(value):,.2f}"


def _format_pct(value: object) -> str:
    if pd.isna(value):
        return "—"
    return f"{float(value):+.2f}%"
