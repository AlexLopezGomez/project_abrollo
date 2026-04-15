"""MVP-2 Step 6 — Hypothesis → ticker shifts via BFS on relationship graph.

For each hypothesis, BFS from its origin_entity_uuid through the Cala
relationship graph, intersect with NDX tickers, and compute per-ticker
shifts: shift = beta * magnitude.

Also builds a shallow pgmpy BayesianNetwork with one independent Bernoulli
root per hypothesis (correlation between tickers comes from Σ, not DAG).
"""
from __future__ import annotations

import json
import logging
import pickle
from pathlib import Path
from typing import Any

import networkx as nx
from pgmpy.factors.discrete import TabularCPD
from pgmpy.models import DiscreteBayesianNetwork as BayesianNetwork

from abrollo.agents.hypothesis_v2 import HypothesisV2
from abrollo.config import data_path
from abrollo.dag.graph import bfs_fanout, get_ndx_uuids

log = logging.getLogger(__name__)


def propagate_hypotheses(
    hypotheses: list[HypothesisV2],
    G: nx.DiGraph,
    max_hops: int = 2,
    decay: float = 0.6,
) -> dict[str, dict[str, float]]:
    """Propagate hypotheses to NDX tickers via BFS.

    Returns: {ticker_uuid: {hypothesis_id: shift}} where shift = beta * magnitude.
    """
    ndx_uuids = get_ndx_uuids(G)
    # shift_per_ticker[ticker_uuid][hypothesis_id] = shift
    shift_per_ticker: dict[str, dict[str, float]] = {}

    for h in hypotheses:
        betas = bfs_fanout(G, h.origin_entity_uuid, max_hops=max_hops, decay=decay)
        ndx_reached = {uid: beta for uid, beta in betas.items() if uid in ndx_uuids}

        log.info("Hypothesis %s (origin=%s): BFS reached %d nodes, %d NDX tickers",
                 h.id, h.origin_entity_uuid[:12], len(betas), len(ndx_reached))

        for ticker_uuid, beta in ndx_reached.items():
            shift = beta * h.magnitude
            shift_per_ticker.setdefault(ticker_uuid, {})[h.id] = shift

    affected_tickers = len(shift_per_ticker)
    log.info("Total affected NDX tickers: %d / %d", affected_tickers, len(ndx_uuids))
    return shift_per_ticker


def build_dag(hypotheses: list[HypothesisV2]) -> BayesianNetwork:
    """Build a shallow BayesianNetwork: one independent Bernoulli root per hypothesis.

    No intermediate nodes. Correlation between tickers comes from Σ in the MC step.
    """
    model = BayesianNetwork()

    for h in hypotheses:
        node = h.id
        model.add_node(node)
        cpd = TabularCPD(
            variable=node,
            variable_card=2,
            values=[[1 - h.probability], [h.probability]],
            state_names={node: ["F", "T"]},
        )
        model.add_cpds(cpd)

    assert model.check_model(), "DAG model check failed"
    return model


def save_propagation(
    hypotheses: list[HypothesisV2],
    shift_per_ticker: dict[str, dict[str, float]],
    model: BayesianNetwork,
    G: nx.DiGraph,
) -> Path:
    """Save DAG + propagation data to data/dag/."""
    out_dir = data_path("dag")
    out_dir.mkdir(parents=True, exist_ok=True)

    # Pickle the BayesianNetwork
    pkl_path = out_dir / "mvp2.pkl"
    with open(pkl_path, "wb") as f:
        pickle.dump(model, f)

    # Human-readable JSON
    uuid_to_name = nx.get_node_attributes(G, "name")
    uuid_to_ticker = {n: d.get("ticker", "") for n, d in G.nodes(data=True) if d.get("ticker")}

    readable: list[dict[str, Any]] = []
    for h in hypotheses:
        affected = []
        for ticker_uuid, shifts in shift_per_ticker.items():
            if h.id in shifts:
                affected.append({
                    "ticker_uuid": ticker_uuid,
                    "ticker": uuid_to_ticker.get(ticker_uuid, "?"),
                    "name": uuid_to_name.get(ticker_uuid, "?"),
                    "shift": round(shifts[h.id], 6),
                })
        affected.sort(key=lambda x: abs(x["shift"]), reverse=True)
        readable.append({
            "hypothesis_id": h.id,
            "origin_uuid": h.origin_entity_uuid,
            "origin_name": uuid_to_name.get(h.origin_entity_uuid, "?"),
            "magnitude": h.magnitude,
            "probability": h.probability,
            "affected_tickers": affected,
            "n_affected": len(affected),
        })

    json_path = out_dir / "mvp2.json"
    json_path.write_text(json.dumps(readable, indent=2), encoding="utf-8")

    log.info("Saved DAG to %s and %s", pkl_path, json_path)
    return pkl_path
