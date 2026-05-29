from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots


def render_history_tab(history: list[dict], selected_filename: str) -> None:
    if not history:
        st.info("No hay lanzamientos en data/submissions/.")
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

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Lanzamientos", str(len(df)))
    c2.metric("Mejor retorno", _format_pct(best_return))
    c3.metric("Último retorno", _format_pct(latest["return_pct"]))
    c4.metric("Mejor valor final", _format_money(best_value))

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
            name="Valor final",
            mode="lines+markers",
            line=dict(color="#4ecdc4", width=3),
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=df_chart["run_label"],
            y=df_chart["return_pct"],
            name="Retorno %",
            mode="lines+markers",
            line=dict(color="#ffb86b", width=3),
        ),
        secondary_y=True,
    )
    fig.update_layout(
        title="Evolución por lanzamiento",
        height=380,
        plot_bgcolor="#0e1117",
        paper_bgcolor="#0e1117",
        font_color="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=65, b=20, l=20, r=20),
    )
    fig.update_yaxes(title_text="Valor final ($)", secondary_y=False)
    fig.update_yaxes(title_text="Retorno (%)", secondary_y=True)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Lanzamientos detectados")
    df_table = df.sort_values("timestamp", ascending=False).copy()
    df_table["Activo"] = df_table["filename"] == selected_filename
    df_table["Snapshot"] = df_table["snapshot_status"].map({
        "snapshotted": "Sí",
        "legacy": "Legacy",
    }).fillna("Legacy")
    df_table = df_table[
        [
            "Activo",
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
            "timestamp": "Fecha",
            "pipeline": "Pipeline",
            "status": "Status",
            "hypotheses_count": "Hipótesis",
            "graph_nodes": "KG nodes",
            "graph_edges": "KG edges",
            "submission_id": "Submission ID",
            "agent": "Agente",
            "version": "Versión",
            "total_invested": "Capital invertido",
            "total_value": "Valor final",
            "return_pct": "Retorno %",
            "n_transactions": "Transacciones",
            "filename": "Archivo",
        }
    )
    st.dataframe(
        df_table,
        use_container_width=True,
        hide_index=True,
        height=360,
        column_config={
            "Fecha": st.column_config.DatetimeColumn(format="YYYY-MM-DD HH:mm:ss"),
            "Capital invertido": st.column_config.NumberColumn(format="$%.0f"),
            "Valor final": st.column_config.NumberColumn(format="$%.2f"),
            "Retorno %": st.column_config.NumberColumn(format="%.2f%%"),
            "Transacciones": st.column_config.NumberColumn(format="%d"),
            "Hipótesis": st.column_config.NumberColumn(format="%d"),
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
