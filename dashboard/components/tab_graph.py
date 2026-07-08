from __future__ import annotations

import os
import tempfile

import streamlit as st
import streamlit.components.v1 as components

from .ui import BG, CYAN, GREEN, MUTED, RED, TEXT, kpi_grid, section_header
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

    section_header("Knowledge Graph", "Grafo Cala con origins, NDX y cartera seleccionada")
    kpi_grid([
        ("KG nodes", str(summary.get("nodes", "—")), f"Fuente: {artifact_key}"),
        ("KG edges", str(summary.get("edges", "—")), "Relaciones Cala"),
        ("NDX nodes", str(summary.get("ndx_nodes", "—")), "Universo Nasdaq"),
        ("Origins", str(len(origin_uuids)), "Hipótesis Claude"),
    ])

    col_graph, col_legend = st.columns([3, 1])

    with col_legend:
        st.markdown("### Leyenda KG")
        st.caption(f"Fuente: `{artifact_key}`")
        st.markdown(
            """
            <div class="ab-card" style="padding: 14px; display: grid; gap: 9px;">
              <span style="color:#ff6b5f;">● Origin hipótesis</span>
              <span style="color:#69d4df;">● NDX en portfolio</span>
              <span style="color:#9da79d;">● NDX no en portfolio</span>
              <span style="color:#29322d;">● Entidad no-NDX</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
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
        st.caption(
            f"Mostrando {len(subgraph_nodes)} nodos · BFS depth={depth} desde "
            f"{len(origin_uuids)} origins + NDX en portfolio"
        )

        html_content = _build_pyvis_html(G, subgraph_nodes, origin_uuids, portfolio_tickers)
        components.html(html_content, height=720, scrolling=False)


def _build_pyvis_html(G, subgraph_nodes, origin_uuids, portfolio_tickers) -> str:
    from pyvis.network import Network

    net = Network(
        height="690px",
        width="100%",
        directed=True,
        bgcolor=BG,
        font_color=TEXT,
    )
    net.set_options("""{
      "physics": {
        "enabled": true,
        "stabilization": {
          "enabled": true,
          "iterations": 350,
          "updateInterval": 25,
          "fit": true
        },
        "barnesHut": {
          "gravitationalConstant": -1800,
          "centralGravity": 0.18,
          "springLength": 160,
          "springConstant": 0.03,
          "damping": 0.45,
          "avoidOverlap": 0.35
        },
        "minVelocity": 0.75
      },
      "edges": {
        "arrows": {"to": {"enabled": true, "scaleFactor": 0.4}},
        "color": {"color": "rgba(157, 167, 157, 0.42)"},
        "width": 1.2
      },
      "nodes": {"font": {"size": 11, "color": "#f4f1e8"}},
      "interaction": {
        "dragNodes": true,
        "dragView": true,
        "hover": true,
        "tooltipDelay": 100,
        "zoomView": true
      }
    }""")

    subgraph_set = set(subgraph_nodes)

    for node in subgraph_nodes:
        data = G.nodes.get(node, {})
        name = data.get("name", node[:12])
        ticker = data.get("ticker", "")
        is_ndx = data.get("is_ndx", False)

        if node in origin_uuids:
            color, size = RED, 30
        elif is_ndx and ticker in portfolio_tickers:
            color, size = CYAN, 20
        elif is_ndx:
            color, size = MUTED, 14
        else:
            color, size = "#29322d", 10

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
    return _freeze_physics_after_stabilization(html_content)


def _freeze_physics_after_stabilization(html_content: str) -> str:
    script = """
<script>
(function freezePhysicsAfterStabilization() {
  function freeze() {
    if (!window.network || window.__abrolloPhysicsFrozen) {
      return;
    }
    window.__abrolloPhysicsFrozen = true;
    window.network.stopSimulation();
    window.network.setOptions({ physics: false });
  }

  function bind() {
    if (!window.network) {
      window.setTimeout(bind, 50);
      return;
    }
    window.network.once("stabilizationIterationsDone", freeze);
    window.setTimeout(freeze, 4500);
  }

  bind();
})();
</script>
</body>
"""
    if "</body>" not in html_content:
        return html_content + script.removesuffix("</body>\n")
    return html_content.replace("</body>", script, 1)
