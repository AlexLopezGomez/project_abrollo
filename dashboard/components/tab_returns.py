from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def render_returns_tab(submission: dict, portfolio: dict) -> None:
    resp = submission.get("response") or {}
    if not resp:
        st.warning("La submission seleccionada no trae bloque response.")
        return

    weights = _submission_weights(submission) or portfolio.get("weights", {})
    total_invested = _as_float(resp.get("total_invested"))
    if total_invested is None:
        total_invested = sum(weights.values())
    total_value = _as_float(resp.get("total_value"))
    if total_value is None:
        total_value = total_invested

    purchase_prices: dict = resp.get("purchase_prices_apr15") or {}
    eval_prices: dict = resp.get("eval_prices_today") or {}
    n_tickers = len([amount for amount in weights.values() if amount])

    pct_return = (total_value / total_invested - 1) * 100 if total_invested else 0.0
    pnl_total = total_value - total_invested

    # --- Métricas hero ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Return", f"{pct_return:+.2f}%", delta=f"${pnl_total:,.0f}")
    c2.metric("Valor de cartera", f"${total_value:,.2f}")
    c3.metric("Capital invertido", f"${total_invested:,.0f}")
    c4.metric("Tickers en portfolio", str(n_tickers))

    st.divider()

    # --- Tabla de posiciones ---
    rows = []
    for ticker, amount in weights.items():
        p_buy = purchase_prices.get(ticker)
        p_now = eval_prices.get(ticker)
        if p_buy and p_now and p_buy > 0:
            ret_pct = (p_now / p_buy - 1) * 100
            pos_value = amount * p_now / p_buy
            pnl = pos_value - amount
        else:
            ret_pct = None
            pos_value = amount
            pnl = 0.0
        rows.append({
            "Ticker": ticker,
            "Invertido ($)": amount,
            "Precio Apr15": p_buy,
            "Precio Hoy": p_now,
            "Retorno %": ret_pct,
            "P&L ($)": round(pnl, 2),
            "Peso %": round(amount / total_invested * 100, 2) if total_invested else None,
        })

    if not rows:
        st.info("La submission seleccionada no trae transacciones para mostrar posiciones.")
        return

    df = pd.DataFrame(rows).sort_values("P&L ($)", ascending=False)

    # --- Bar chart por ticker ---
    df_chart = df.dropna(subset=["Retorno %"]).sort_values("Retorno %", ascending=False)
    if df_chart.empty:
        st.info("No hay precios suficientes para calcular retorno por ticker.")
    else:
        colors = ["#4ecdc4" if r >= 0 else "#ff6b6b" for r in df_chart["Retorno %"]]
        fig = go.Figure(go.Bar(
            x=df_chart["Ticker"],
            y=df_chart["Retorno %"],
            marker_color=colors,
            customdata=df_chart[["Invertido ($)", "Precio Apr15", "Precio Hoy", "P&L ($)"]].values,
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Retorno: %{y:.2f}%<br>"
                "Invertido: $%{customdata[0]:,.0f}<br>"
                "Apr15: $%{customdata[1]:.2f}<br>"
                "Hoy: $%{customdata[2]:.2f}<br>"
                "P&L: $%{customdata[3]:,.2f}"
                "<extra></extra>"
            ),
        ))
        fig.update_layout(
            title="Retorno por ticker (precio hoy vs precio Apr15)",
            xaxis_title="Ticker",
            yaxis_title="Retorno %",
            height=400,
            plot_bgcolor="#0e1117",
            paper_bgcolor="#0e1117",
            font_color="white",
            xaxis=dict(tickangle=-45),
        )
        fig.add_hline(y=0, line_color="white", line_width=0.5, opacity=0.4)
        st.plotly_chart(fig, use_container_width=True)

    # --- Tabla detallada ---
    st.subheader("Posiciones detalladas")
    df_display = df.copy()
    df_display["Invertido ($)"] = df_display["Invertido ($)"].map("${:,.0f}".format)
    df_display["Precio Apr15"] = df_display["Precio Apr15"].map(lambda v: f"${v:.2f}" if v else "—")
    df_display["Precio Hoy"] = df_display["Precio Hoy"].map(lambda v: f"${v:.2f}" if v else "—")
    df_display["Retorno %"] = df_display["Retorno %"].map(lambda v: f"{v:+.2f}%" if pd.notna(v) else "—")
    df_display["P&L ($)"] = df_display["P&L ($)"].map("${:,.2f}".format)
    df_display["Peso %"] = df_display["Peso %"].map(lambda v: f"{v:.2f}%" if pd.notna(v) else "—")
    st.dataframe(df_display, use_container_width=True, height=400)

    # --- Detalles del optimizador ---
    with st.expander("Detalles del optimizador CVaR"):
        oc1, oc2, oc3 = st.columns(3)
        oc1.metric("Solver", portfolio.get("solver", "—"))
        oc2.metric("CVaR 5%", f"{portfolio.get('cvar_5_pct', 0):.4f}")
        oc3.metric("E[r] (Monte Carlo)", f"{portfolio.get('expected_return_pct', 0):+.4f}")


def _submission_weights(submission: dict) -> dict[str, float]:
    transactions = (submission.get("request") or {}).get("transactions") or []
    weights: dict[str, float] = {}
    for tx in transactions:
        ticker = tx.get("nasdaq_code") or tx.get("ticker")
        amount = _as_float(tx.get("amount"))
        if ticker and amount is not None:
            weights[ticker] = weights.get(ticker, 0.0) + amount
    return weights


def _as_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
