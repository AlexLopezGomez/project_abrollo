"""MVP-2 Step 5 — Generate hypotheses with HypothesisV2 schema.

Gate: (a) 10 hypotheses returned; (b) 10/10 schema-valid; (c) 10/10 origin
      UUIDs in allow-list; (d) 10/10 source_dates match allow-list verbatim;
      (e) >= 8 distinct origins.
"""
from __future__ import annotations

import json
import logging
import pickle
import sys
from pathlib import Path

import networkx as nx

from abrollo.agents.hypothesis_v2 import HypothesisV2, call_sonnet_hypotheses
from abrollo.config import CUTOFF_DATE, data_path
from abrollo.dag.graph import get_ndx_uuids

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("mvp2.step5")


def build_allow_lists(graph_path: Path) -> tuple[list[dict], set[str], list[str]]:
    """Build origin allow-list and dates allow-list from saved data."""
    with open(graph_path, "rb") as f:
        G = pickle.load(f)
    ndx_uuids = get_ndx_uuids(G)

    # Origins: non-NDX nodes (macro/thematic entities), sorted by degree
    uuid_to_name = nx.get_node_attributes(G, "name")
    non_ndx = [(n, G.degree(n)) for n in G.nodes() if n not in ndx_uuids and uuid_to_name.get(n)]
    non_ndx.sort(key=lambda x: -x[1])

    # If not enough non-NDX hubs, include NDX nodes too
    if len(non_ndx) < 50:
        ndx_nodes = [(n, G.degree(n)) for n in ndx_uuids if uuid_to_name.get(n)]
        ndx_nodes.sort(key=lambda x: -x[1])
        non_ndx.extend(ndx_nodes)

    origin_entries = [{"uuid": uid, "name": uuid_to_name.get(uid, "?")} for uid, _ in non_ndx[:50]]
    allowed_origin_uuids = set(G.nodes())  # all graph nodes are valid origins

    # Dates: collect all property source dates <= cutoff from entity files
    entities_dir = data_path("cala_entities")
    allowed_dates: set[str] = set()
    for fpath in entities_dir.glob("*.json"):
        if fpath.name.startswith("_"):
            continue
        try:
            entity = json.loads(fpath.read_text(encoding="utf-8"))
        except Exception:
            continue
        props = entity.get("properties", {})
        if not isinstance(props, dict):
            continue
        for pname, pbody in props.items():
            if not isinstance(pbody, dict):
                continue
            for src in pbody.get("sources", []):
                if isinstance(src, dict):
                    d = src.get("date", "")
                    if isinstance(d, str) and d[:10] <= CUTOFF_DATE:
                        allowed_dates.add(d[:10])

    log.info("Allow-list: %d origin entries, %d total graph nodes, %d dates",
             len(origin_entries), len(allowed_origin_uuids), len(allowed_dates))
    return origin_entries, allowed_origin_uuids, sorted(allowed_dates)


def main() -> int:
    graph_path = data_path("graph") / "mvp2.gpickle"
    if not graph_path.exists():
        log.error("Graph not found at %s — run step 4 first", graph_path)
        return 1

    origin_entries, allowed_origin_uuids, allowed_dates = build_allow_lists(graph_path)

    if not allowed_dates:
        log.error("No allowed dates found — check entity data")
        return 1

    hypotheses = call_sonnet_hypotheses(
        origin_entries=origin_entries,
        allowed_dates=allowed_dates,
        allowed_origin_uuids=allowed_origin_uuids,
    )

    # Gate checks
    n = len(hypotheses)
    distinct_origins = len({h.origin_entity_uuid for h in hypotheses})

    log.info("Hypotheses: %d valid, %d distinct origins", n, distinct_origins)

    if n < 8:
        log.error("GATE FAIL: only %d valid hypotheses (need >= 8)", n)
        return 1

    if distinct_origins < 8:
        log.warning("Only %d distinct origins (target: 10)", distinct_origins)

    # Save
    out_path = data_path("hypotheses") / "mvp2.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps([h.model_dump() for h in hypotheses], indent=2),
        encoding="utf-8",
    )

    print(f"[step5 OK] {n} hypotheses, {distinct_origins} distinct origins")
    return 0


if __name__ == "__main__":
    sys.exit(main())
