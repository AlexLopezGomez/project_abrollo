from __future__ import annotations

from html import escape
from typing import Any

import plotly.graph_objects as go
import streamlit as st


BG = "#050706"
SURFACE = "#0d100f"
SURFACE_2 = "#141815"
LINE = "rgba(244, 241, 232, 0.12)"
TEXT = "#f4f1e8"
MUTED = "#9da79d"
GREEN = "#67e8a5"
CYAN = "#69d4df"
AMBER = "#f4b860"
RED = "#ff6b5f"


def install_theme() -> None:
    st.markdown(
        f"""
<style>
  :root {{
    --ab-bg: {BG};
    --ab-surface: {SURFACE};
    --ab-surface-2: {SURFACE_2};
    --ab-line: {LINE};
    --ab-text: {TEXT};
    --ab-muted: {MUTED};
    --ab-green: {GREEN};
    --ab-cyan: {CYAN};
    --ab-amber: {AMBER};
    --ab-red: {RED};
  }}

  .stApp {{
    background:
      linear-gradient(rgba(244, 241, 232, 0.035) 1px, transparent 1px),
      linear-gradient(90deg, rgba(244, 241, 232, 0.025) 1px, transparent 1px),
      var(--ab-bg);
    background-size: 52px 52px;
    color: var(--ab-text);
  }}

  [data-testid="stHeader"] {{
    background: rgba(5, 7, 6, 0.82);
    backdrop-filter: blur(14px);
  }}

  [data-testid="stSidebar"] {{
    background: #080b09;
    border-right: 1px solid var(--ab-line);
  }}

  [data-testid="stSidebar"] * {{
    color: var(--ab-text);
  }}

  div[data-baseweb="select"] > div,
  [data-testid="stSidebar"] [data-baseweb="select"] > div {{
    border: 1px solid var(--ab-line);
    border-radius: 8px;
    background: var(--ab-surface-2) !important;
    color: var(--ab-text) !important;
  }}

  div[data-baseweb="select"] span,
  [data-testid="stSidebar"] [data-baseweb="select"] span {{
    color: var(--ab-text) !important;
  }}

  div[data-baseweb="select"] svg,
  [data-testid="stSidebar"] [data-baseweb="select"] svg {{
    color: var(--ab-green) !important;
    fill: var(--ab-green) !important;
  }}

  [data-testid="stSidebar"] div[data-testid="stMetric"] [data-testid="stMetricValue"] {{
    font-size: 28px;
  }}

  .block-container {{
    max-width: 1480px;
    padding-top: 1.5rem;
    padding-bottom: 4rem;
  }}

  h1, h2, h3 {{
    letter-spacing: 0;
  }}

  div[data-testid="stMetric"] {{
    min-height: 112px;
    padding: 15px 16px;
    border: 1px solid var(--ab-line);
    border-radius: 8px;
    background: rgba(20, 24, 21, 0.9);
    box-shadow: 0 18px 50px rgba(0, 0, 0, 0.18);
  }}

  div[data-testid="stMetric"] label {{
    color: var(--ab-muted) !important;
  }}

  div[data-testid="stMetric"] [data-testid="stMetricValue"] {{
    color: var(--ab-text);
    font-weight: 850;
  }}

  div[data-testid="stMetric"] [data-testid="stMetricDelta"] {{
    color: var(--ab-green);
  }}

  div[data-testid="stTabs"] button {{
    min-height: 46px;
    border-radius: 8px 8px 0 0;
    color: var(--ab-muted);
    font-weight: 700;
  }}

  div[data-testid="stTabs"] button[aria-selected="true"] {{
    color: var(--ab-green);
    background: rgba(103, 232, 165, 0.08);
  }}

  div[data-testid="stTabs"] [data-baseweb="tab-highlight"] {{
    background-color: var(--ab-green);
  }}

  div[data-testid="stDataFrame"],
  div[data-testid="stExpander"] {{
    border-radius: 8px;
    overflow: hidden;
  }}

  div[data-testid="stExpander"] details {{
    border: 1px solid var(--ab-line);
    border-radius: 8px;
    background: rgba(20, 24, 21, 0.82);
  }}

  .ab-hero {{
    display: grid;
    grid-template-columns: minmax(0, 1.05fr) minmax(440px, 0.95fr);
    gap: 18px;
    align-items: stretch;
    margin-bottom: 20px;
  }}

  .ab-hero-main,
  .ab-hero-panel,
  .ab-card {{
    border: 1px solid var(--ab-line);
    border-radius: 8px;
    background: rgba(13, 16, 15, 0.92);
    box-shadow: 0 24px 80px rgba(0, 0, 0, 0.25);
  }}

  .ab-hero-main {{
    padding: 26px 28px;
  }}

  .ab-eyebrow {{
    display: inline-flex;
    align-items: center;
    gap: 9px;
    color: var(--ab-green);
    font-size: 12px;
    font-weight: 850;
    letter-spacing: 0.11em;
    text-transform: uppercase;
  }}

  .ab-dot {{
    width: 9px;
    height: 9px;
    border-radius: 50%;
    background: var(--ab-green);
    box-shadow: 0 0 0 5px rgba(103, 232, 165, 0.12);
  }}

  .ab-hero-title {{
    margin: 18px 0 10px;
    color: var(--ab-text);
    font-size: clamp(38px, 5vw, 74px);
    line-height: 0.95;
    font-weight: 900;
  }}

  .ab-hero-copy {{
    max-width: 860px;
    color: #d9ddd4;
    font-size: 18px;
    line-height: 1.45;
  }}

  .ab-hero-panel {{
    display: grid;
    gap: 14px;
    padding: 22px;
  }}

  .ab-panel-row {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 14px;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--ab-line);
  }}

  .ab-panel-value span,
  .ab-chip span,
  .ab-kpi span {{
    color: var(--ab-muted);
  }}

  .ab-panel-value strong {{
    display: block;
    margin-top: 4px;
    color: var(--ab-text);
    font-size: clamp(34px, 4vw, 56px);
    line-height: 1;
  }}

  .ab-panel-value em {{
    display: block;
    margin-top: 7px;
    color: var(--ab-green);
    font-style: normal;
    font-weight: 800;
  }}

  .ab-chip-row {{
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }}

  .ab-chip {{
    display: inline-flex;
    align-items: center;
    gap: 7px;
    min-height: 34px;
    padding: 0 10px;
    border: 1px solid var(--ab-line);
    border-radius: 999px;
    background: rgba(244, 241, 232, 0.04);
    color: var(--ab-text);
    font-size: 13px;
  }}

  .ab-chip--good {{
    border-color: rgba(103, 232, 165, 0.34);
    color: var(--ab-green);
  }}

  .ab-chip--warn {{
    border-color: rgba(244, 184, 96, 0.34);
    color: var(--ab-amber);
  }}

  .ab-section {{
    margin: 8px 0 16px;
  }}

  .ab-section span {{
    color: var(--ab-green);
    font-size: 12px;
    font-weight: 850;
    letter-spacing: 0.11em;
    text-transform: uppercase;
  }}

  .ab-section h2 {{
    margin: 6px 0 0;
    color: var(--ab-text);
    font-size: clamp(25px, 3vw, 42px);
    line-height: 1.05;
  }}

  .ab-kpi-grid {{
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 10px;
    margin: 10px 0 18px;
  }}

  .ab-kpi {{
    min-height: 116px;
    padding: 14px;
    border: 1px solid var(--ab-line);
    border-radius: 8px;
    background: rgba(20, 24, 21, 0.9);
  }}

  .ab-kpi strong {{
    display: block;
    margin-top: 16px;
    color: var(--ab-text);
    font-size: 30px;
    line-height: 1;
  }}

  .ab-kpi small {{
    display: block;
    margin-top: 6px;
    color: var(--ab-muted);
  }}

  .ab-sidebar-title {{
    color: var(--ab-green);
    font-size: 12px;
    font-weight: 850;
    letter-spacing: 0.11em;
    text-transform: uppercase;
  }}

  @media (max-width: 900px) {{
    .ab-hero,
    .ab-kpi-grid {{
      grid-template-columns: 1fr;
    }}
  }}
</style>
        """,
        unsafe_allow_html=True,
    )


def chip(label: str, tone: str = "") -> str:
    class_name = "ab-chip"
    if tone:
        class_name += f" ab-chip--{escape(tone)}"
    return f'<span class="{class_name}">{escape(label)}</span>'


def section_header(eyebrow: str, title: str) -> None:
    st.markdown(
        f"""
<div class="ab-section">
  <span>{escape(eyebrow)}</span>
  <h2>{escape(title)}</h2>
</div>
        """,
        unsafe_allow_html=True,
    )


def kpi_grid(items: list[tuple[str, str, str]]) -> None:
    cards = "\n".join(
        f"""
<div class="ab-kpi">
  <span>{escape(label)}</span>
  <strong>{escape(value)}</strong>
  <small>{escape(caption)}</small>
</div>
        """
        for label, value, caption in items
    )
    st.markdown(f'<div class="ab-kpi-grid">{cards}</div>', unsafe_allow_html=True)


def render_hero(
    *,
    title: str,
    subtitle: str,
    run_label: str,
    total_value: str,
    return_pct: str,
    chips: list[str],
) -> None:
    chip_html = "".join(chips)
    st.markdown(
        f"""
<div class="ab-hero">
  <div class="ab-hero-main">
    <div class="ab-eyebrow"><span class="ab-dot"></span>Abrollo decision dashboard</div>
    <div class="ab-hero-title">{escape(title)}</div>
    <div class="ab-hero-copy">{escape(subtitle)}</div>
  </div>
  <div class="ab-hero-panel">
    <div class="ab-panel-row">
      <div class="ab-eyebrow">{escape(run_label)}</div>
    </div>
    <div class="ab-panel-value">
      <span>Valor final de cartera</span>
      <strong>{escape(total_value)}</strong>
      <em>{escape(return_pct)} retorno</em>
    </div>
    <div class="ab-chip-row">{chip_html}</div>
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )


def apply_plotly_theme(fig: go.Figure, *, height: int | None = None) -> go.Figure:
    fig.update_layout(
        plot_bgcolor=BG,
        paper_bgcolor=BG,
        font=dict(color=TEXT, family="Inter, Segoe UI, sans-serif"),
        margin=dict(t=52, b=24, l=24, r=24),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor="rgba(0,0,0,0)",
        ),
    )
    fig.update_xaxes(gridcolor="rgba(244,241,232,0.08)", zerolinecolor="rgba(244,241,232,0.2)")
    fig.update_yaxes(gridcolor="rgba(244,241,232,0.08)", zerolinecolor="rgba(244,241,232,0.2)")
    if height is not None:
        fig.update_layout(height=height)
    return fig


def metric_tone(value: object) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return ""
    if number > 0:
        return "good"
    if number < 0:
        return "warn"
    return ""
