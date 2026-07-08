from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from .ui import CYAN, GREEN, apply_plotly_theme, section_header


def render_hypotheses_tab(
    hypotheses: list[dict],
    dag: list[dict],
    portfolio: dict,
) -> None:
    portfolio_tickers = set((portfolio.get("weights") or {}).keys())
    dag_index = {e.get("hypothesis_id"): e for e in dag if e.get("hypothesis_id")}

    # --- Métricas resumen ---
    bullish = sum(1 for h in hypotheses if h.get("magnitude", 0) > 0)
    bearish = sum(1 for h in hypotheses if h.get("magnitude", 0) < 0)
    avg_prob = sum(h.get("probability", 0) for h in hypotheses) / max(len(hypotheses), 1)

    section_header("Claude evidence", "Hipótesis, fuentes y propagación a tickers")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total hipótesis", len(hypotheses))
    c2.metric("Bullish", bullish)
    c3.metric("Bearish", bearish)
    c4.metric("Prob. media", f"{avg_prob:.0%}")

    st.divider()

    # --- Filtros ---
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        min_prob = st.slider("Probabilidad mínima", 0.0, 1.0, 0.0, 0.05)
    with fc2:
        direction = st.selectbox("Dirección", ["Todas", "Bullish (+)", "Bearish (-)"])
    with fc3:
        sort_by = st.selectbox("Ordenar por", ["Probabilidad", "Magnitud (abs)", "ID"])

    filtered = [h for h in hypotheses if h.get("probability", 0) >= min_prob]
    if direction == "Bullish (+)":
        filtered = [h for h in filtered if h.get("magnitude", 0) > 0]
    elif direction == "Bearish (-)":
        filtered = [h for h in filtered if h.get("magnitude", 0) < 0]

    if sort_by == "Probabilidad":
        filtered.sort(key=lambda h: -h.get("probability", 0))
    elif sort_by == "Magnitud (abs)":
        filtered.sort(key=lambda h: -abs(h.get("magnitude", 0)))
    else:
        filtered.sort(key=lambda h: h.get("id", ""))

    st.caption(f"Mostrando {len(filtered)} de {len(hypotheses)} hipótesis")

    # --- Cards expandibles ---
    for h in filtered:
        h_id = h.get("id", "—")
        dag_entry = dag_index.get(h_id, {})
        affected = dag_entry.get("affected_tickers", [])
        mag = h.get("magnitude", 0)
        prob_pct = int(h.get("probability", 0) * 100)
        sign_icon = "📈" if mag > 0 else "📉"
        origin_name = dag_entry.get("origin_name", h.get("origin_entity_uuid", "")[:16])
        trigger_short = h.get("trigger", "")[:90]

        with st.expander(
            f"{sign_icon} **{h_id}** — {trigger_short}…  "
            f"| P={prob_pct}% | Mag={mag:+.0%} | {origin_name}"
        ):
            col_meta, col_tickers = st.columns([2, 3])

            with col_meta:
                st.markdown(f"**Trigger:** {h.get('trigger', '—')}")
                st.markdown(f"**Origin:** {origin_name}")
                st.caption(f"Origin UUID: `{h.get('origin_entity_uuid', '—')}`")
                st.markdown(f"**Probabilidad:** {h.get('probability', 0):.0%}")
                st.markdown(f"**Magnitud:** {mag:+.0%}")
                st.markdown(f"**Horizonte:** {h.get('horizon_days', '—')} días")
                st.markdown(f"**Tickers afectados:** {dag_entry.get('n_affected', len(affected))}")
                if h.get("source_dates"):
                    st.markdown(f"**Fechas fuente:** {', '.join(h['source_dates'][:3])}")
                if h.get("sources"):
                    st.markdown("**Source UUIDs:**")
                    st.code("\n".join(str(source) for source in h["sources"]), language="text")

            with col_tickers:
                if affected:
                    df_t = pd.DataFrame(affected[:20])[["ticker", "shift"] +
                           (["name"] if "name" in affected[0] else [])]
                    df_t["en_portfolio"] = df_t["ticker"].isin(portfolio_tickers)
                    df_t = df_t.sort_values("shift", ascending=False)

                    fig = px.bar(
                        df_t,
                        x="ticker",
                        y="shift",
                        color="en_portfolio",
                        color_discrete_map={True: GREEN, False: CYAN},
                        labels={"shift": "Shift esperado", "en_portfolio": "En portfolio"},
                        hover_data=["name"] if "name" in df_t.columns else None,
                        title=f"Tickers afectados — {h_id}",
                    )
                    fig.update_layout(
                        margin=dict(t=35, b=10, l=10, r=10),
                        showlegend=True,
                        xaxis=dict(tickangle=-45),
                    )
                    apply_plotly_theme(fig, height=280)
                    st.plotly_chart(fig, use_container_width=True, key=f"hyp_{h_id}")
                else:
                    st.info("Sin tickers afectados en el DAG para esta hipótesis.")
