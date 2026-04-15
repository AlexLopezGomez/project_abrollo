"""MVP-2 Step 4 — Relationship graph + BFS index from Cala entity data.

Builds a directed graph in networkx from the relationships in
data/cala_entities/{ticker}.json. Provides bfs_fanout() for hypothesis
propagation (Step 6).
"""
from __future__ import annotations

import json
import logging
import pickle
from collections import deque
from pathlib import Path
from typing import Any

import networkx as nx

from abrollo.config import data_path

log = logging.getLogger(__name__)

ENTITIES_DIR = data_path("cala_entities")


def build_graph(entities_dir: Path = ENTITIES_DIR) -> tuple[nx.DiGraph, dict[str, str]]:
    """Build a directed graph from Cala entity relationships.

    Returns: (graph, uuid_to_name) mapping UUIDs to human-readable names.
    """
    G = nx.DiGraph()
    uuid_to_name: dict[str, str] = {}

    ticker_files = sorted(entities_dir.glob("*.json"))
    ticker_files = [f for f in ticker_files if not f.name.startswith("_")]

    for fpath in ticker_files:
        ticker = fpath.stem
        try:
            entity = json.loads(fpath.read_text(encoding="utf-8"))
        except Exception as e:
            log.warning("Failed to load %s: %s", fpath, e)
            continue

        entity_id = entity.get("id", "")
        entity_name = entity.get("name", ticker)
        uuid_to_name[entity_id] = entity_name

        # Add the ticker node
        G.add_node(entity_id, name=entity_name, ticker=ticker, is_ndx=True)

        rels = entity.get("relationships", {})

        # Outgoing relationships
        for rel_type, targets in rels.get("outgoing", {}).items():
            if not isinstance(targets, list):
                continue
            for target in targets:
                if not isinstance(target, dict):
                    continue
                target_id = target.get("id", "")
                if not target_id:
                    continue
                target_name = target.get("name", "")
                if target_name:
                    uuid_to_name[target_id] = target_name

                if not G.has_node(target_id):
                    G.add_node(target_id, name=target_name,
                               entity_type=target.get("entity_type", ""))
                G.add_edge(entity_id, target_id, type=rel_type)

        # Incoming relationships (add reverse edge: source → this entity)
        for rel_type, sources in rels.get("incoming", {}).items():
            if not isinstance(sources, list):
                continue
            for source in sources:
                if not isinstance(source, dict):
                    continue
                source_id = source.get("id", "")
                if not source_id:
                    continue
                source_name = source.get("name", "")
                if source_name:
                    uuid_to_name[source_id] = source_name

                if not G.has_node(source_id):
                    G.add_node(source_id, name=source_name,
                               entity_type=source.get("entity_type", ""))
                G.add_edge(source_id, entity_id, type=rel_type)

    log.info("Graph: %d nodes, %d edges", G.number_of_nodes(), G.number_of_edges())
    return G, uuid_to_name


def bfs_fanout(
    G: nx.DiGraph,
    origin_uuid: str,
    max_hops: int = 2,
    decay: float = 0.6,
    max_nodes: int = 200,
) -> dict[str, float]:
    """BFS from origin_uuid, returning {uuid: beta} where beta = decay^distance.

    Uses undirected traversal (ignores edge direction) to maximize reach.
    Caps at max_nodes (break ties by shortest path, then by degree).
    """
    if origin_uuid not in G:
        return {}

    visited: dict[str, int] = {origin_uuid: 0}
    queue: deque[tuple[str, int]] = deque([(origin_uuid, 0)])

    # BFS on undirected view
    undirected = G.to_undirected(as_view=True)

    while queue:
        node, dist = queue.popleft()
        if dist >= max_hops:
            continue
        for neighbor in undirected.neighbors(node):
            if neighbor not in visited:
                visited[neighbor] = dist + 1
                queue.append((neighbor, dist + 1))

    # Compute betas
    betas: dict[str, float] = {}
    for uid, dist in visited.items():
        if uid == origin_uuid:
            continue
        betas[uid] = decay ** dist

    # Cap at max_nodes: sort by (distance ASC, degree DESC) and take top
    if len(betas) > max_nodes:
        scored = sorted(
            betas.items(),
            key=lambda x: (visited[x[0]], -undirected.degree(x[0])),
        )
        betas = dict(scored[:max_nodes])

    return betas


def get_ndx_uuids(G: nx.DiGraph) -> set[str]:
    """Return the set of UUIDs that are NDX tickers (have is_ndx=True)."""
    return {n for n, d in G.nodes(data=True) if d.get("is_ndx")}


def save_graph(G: nx.DiGraph, uuid_to_name: dict[str, str]) -> Path:
    """Save graph + summary to data/graph/."""
    out_dir = data_path("graph")
    out_dir.mkdir(parents=True, exist_ok=True)

    # Save as pickle
    gpickle_path = out_dir / "mvp2.gpickle"
    with open(gpickle_path, "wb") as f:
        pickle.dump(G, f)

    # Human-readable summary
    ndx_nodes = get_ndx_uuids(G)
    degrees = [d for _, d in G.degree()]
    components = nx.number_weakly_connected_components(G)

    summary = {
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges(),
        "ndx_nodes": len(ndx_nodes),
        "non_ndx_nodes": G.number_of_nodes() - len(ndx_nodes),
        "avg_out_degree": round(sum(d for _, d in G.out_degree()) / max(G.number_of_nodes(), 1), 2),
        "avg_in_degree": round(sum(d for _, d in G.in_degree()) / max(G.number_of_nodes(), 1), 2),
        "weakly_connected_components": components,
        "top_hubs_by_degree": sorted(
            [(uuid_to_name.get(n, n), d) for n, d in G.degree()],
            key=lambda x: -x[1],
        )[:20],
    }

    summary_path = out_dir / "mvp2_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")

    log.info("Saved graph to %s (%d nodes, %d edges)", gpickle_path,
             G.number_of_nodes(), G.number_of_edges())
    return gpickle_path
