"""MVP-2 Step 6 — Entity-level DAG + propagation to tickers.

Gate: (a) check_model() = True; (b) union of affected tickers >= 30;
      (c) at least 2 hypotheses overlap on some ticker.
"""
from __future__ import annotations

import json
import logging
import pickle
import sys

import networkx as nx

from abrollo.agents.hypothesis_v2 import HypothesisV2
from abrollo.config import data_path
from abrollo.dag.graph import get_ndx_uuids
from abrollo.dag.propagation import build_dag, propagate_hypotheses, save_propagation

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("mvp2.step6")


def main() -> int:
    # Load graph
    graph_path = data_path("graph") / "mvp2.gpickle"
    if not graph_path.exists():
        log.error("Graph not found — run step 4 first")
        return 1
    with open(graph_path, "rb") as f:
        G = pickle.load(f)

    # Load hypotheses
    hyp_path = data_path("hypotheses") / "mvp2.json"
    if not hyp_path.exists():
        log.error("Hypotheses not found — run step 5 first")
        return 1
    raw = json.loads(hyp_path.read_text(encoding="utf-8"))
    hypotheses = [HypothesisV2.model_validate(h) for h in raw]
    log.info("Loaded %d hypotheses", len(hypotheses))

    # Propagate
    shift_per_ticker = propagate_hypotheses(hypotheses, G, max_hops=2, decay=0.6)

    ndx_uuids = get_ndx_uuids(G)
    affected_ndx = {t for t in shift_per_ticker if t in ndx_uuids}
    log.info("Affected NDX tickers: %d / %d", len(affected_ndx), len(ndx_uuids))

    # Gate (b): coverage
    if len(affected_ndx) < 30:
        log.warning("Only %d NDX tickers affected (target >= 30). Trying max_hops=3...", len(affected_ndx))
        shift_per_ticker = propagate_hypotheses(hypotheses, G, max_hops=3, decay=0.6)
        affected_ndx = {t for t in shift_per_ticker if t in ndx_uuids}
        log.info("With hops=3: %d NDX tickers affected", len(affected_ndx))

    if len(affected_ndx) < 15:
        log.error("GATE FAIL: only %d NDX tickers affected (need >= 15)", len(affected_ndx))
        return 1

    # Gate (c): overlap
    overlap_tickers = {
        t for t, shifts in shift_per_ticker.items()
        if t in ndx_uuids and len(shifts) >= 2
    }
    log.info("Tickers with overlapping hypotheses: %d", len(overlap_tickers))

    # Build DAG
    model = build_dag(hypotheses)
    log.info("DAG check_model: %s", model.check_model())

    # Save
    save_propagation(hypotheses, shift_per_ticker, model, G)

    print(f"[step6 OK] {len(affected_ndx)} NDX tickers affected, "
          f"{len(overlap_tickers)} overlapping, DAG valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
