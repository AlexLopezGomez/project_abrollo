from __future__ import annotations

import os
import tempfile

import streamlit as st
import streamlit.components.v1 as components

from .data_loader import (
    build_hypothesis_subgraph,
    get_graph_mtime,
    get_graph_summary_mtime,
    load_graph,
    load_graph_summary,
)


def render_graph_tab(dag: list[dict], portfolio: dict, artifact_key: str = "mvp2") -> None:
    graph_mtime = get_graph_mtime(artifact_key)
    G = load_graph(artifact_key, graph_mtime)
    summary = load_graph_summary(artifact_key, get_graph_summary_mtime(artifact_key))

    origin_uuids = frozenset(e.get("origin_uuid") for e in dag if e.get("origin_uuid"))
    portfolio_tickers = frozenset((portfolio.get("weights") or {}).keys())

    col_graph, col_legend = st.columns([3, 1])

    with col_legend:
        st.markdown("### Leyenda")
        st.caption(f"Fuente: `{artifact_key}`")
        st.markdown("🔴 **Origin hipótesis**")
        st.markdown("🟦 **NDX en portfolio**")
        st.markdown("⚫ NDX no en portfolio")
        st.markdown("⬛ Entidad no-NDX")
        st.divider()
        st.markdown(f"**Nodos totales KG:** {summary.get('nodes', '—')}")
        st.markdown(f"**Aristas totales:** {summary.get('edges', '—')}")
        st.markdown(f"**NDX tickers:** {summary.get('ndx_nodes', '—')}")
        st.divider()
        st.markdown("**Top hubs por grado:**")
        for name, degree in (summary.get("top_hubs_by_degree") or [])[:8]:
            st.markdown(f"- {name[:30]} ({degree})")

        depth = st.slider("BFS depth desde origins", min_value=1, max_value=2, value=1)

    with col_graph:
        if G is None:
            st.warning(
                f"No hay Knowledge Graph disponible para `{artifact_key}`. "
                "Si es un run legacy, no existe snapshot histórico de KG."
            )
            if summary:
                st.json(summary)
            return

        subgraph_nodes = build_hypothesis_subgraph(
            artifact_key,
            graph_mtime,
            origin_uuids,
            portfolio_tickers,
            depth,
        )
        st.caption(f"Mostrando {len(subgraph_nodes)} nodos (BFS depth={depth} desde {len(origin_uuids)} origins + NDX en portfolio)")

        html_content = _build_pyvis_html(G, subgraph_nodes, origin_uuids, portfolio_tickers)
        components.html(html_content, height=680, scrolling=False)


def _build_pyvis_html(G, subgraph_nodes, origin_uuids, portfolio_tickers) -> str:
    from pyvis.network import Network

    net = Network(
        height="650px",
        width="100%",
        directed=True,
        bgcolor="#1a1a2e",
        font_color="white",
    )
    net.set_options("""{
      "physics": {
        "stabilization": {"iterations": 80, "fit": true},
        "barnesHut": {"gravitationalConstant": -3000, "springLength": 120}
      },
      "edges": {
        "arrows": {"to": {"enabled": true, "scaleFactor": 0.4}},
        "color": {"color": "#444466"},
        "width": 1.2
      },
      "nodes": {"font": {"size": 11, "color": "white"}},
      "interaction": {"hover": true, "tooltipDelay": 100}
    }""")

    subgraph_set = set(subgraph_nodes)

    for node in subgraph_nodes:
        data = G.nodes.get(node, {})
        name = data.get("name", node[:12])
        ticker = data.get("ticker", "")
        is_ndx = data.get("is_ndx", False)

        if node in origin_uuids:
            color, size = "#ff6b6b", 30
        elif is_ndx and ticker in portfolio_tickers:
            color, size = "#4ecdc4", 20
        elif is_ndx:
            color, size = "#95a5a6", 14
        else:
            color, size = "#2c3e50", 10

        label = ticker if ticker else name[:18]
        title = f"{name}<br>{'NDX: ' + ticker if ticker else 'Entidad'}"
        if node in origin_uuids:
            title += "<br><b>⭐ Origin hipótesis</b>"

        net.add_node(node, label=label, title=title, color=color, size=size)

    for src, dst, edata in G.edges(data=True):
        if src in subgraph_set and dst in subgraph_set:
            rel_type = edata.get("type", "")
            net.add_edge(src, dst, title=rel_type)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode="w", encoding="utf-8") as f:
        fname = f.name
    net.save_graph(fname)
    html_content = open(fname, encoding="utf-8").read()
    os.unlink(fname)
    return html_content
