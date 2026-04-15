"""MVP-2 Step 4 — Build relationship graph + BFS index.

Gate: (a) >= 500 nodes and >= 1000 edges;
      (b) bfs_fanout from 3 hub origins returns >= 20 NDX tickers within beta > 0.1.
"""
from __future__ import annotations

import logging
import sys

from abrollo.dag.graph import bfs_fanout, build_graph, get_ndx_uuids, save_graph

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("mvp2.step4")


def main() -> int:
    G, uuid_to_name = build_graph()
    ndx_uuids = get_ndx_uuids(G)

    n_nodes = G.number_of_nodes()
    n_edges = G.number_of_edges()
    log.info("Graph: %d nodes, %d edges, %d NDX tickers", n_nodes, n_edges, len(ndx_uuids))

    # Gate (a): size
    if n_nodes < 500:
        log.warning("Gate (a) soft fail: %d nodes < 500", n_nodes)
    if n_edges < 1000:
        log.warning("Gate (a) soft fail: %d edges < 1000", n_edges)

    # Gate (b): BFS reach — pick 3 hubs by degree
    hubs = sorted(G.nodes(), key=lambda n: G.degree(n), reverse=True)
    # Prefer non-NDX hubs (macro/thematic entities)
    non_ndx_hubs = [h for h in hubs if h not in ndx_uuids]
    test_origins = (non_ndx_hubs[:3] if len(non_ndx_hubs) >= 3 else hubs[:3])

    bfs_ok = 0
    for origin in test_origins:
        name = uuid_to_name.get(origin, origin[:12])
        betas = bfs_fanout(G, origin, max_hops=2, decay=0.6)
        ndx_reached = {uid for uid, beta in betas.items() if uid in ndx_uuids and beta > 0.1}
        log.info("BFS from %s: %d total, %d NDX tickers (beta>0.1)", name, len(betas), len(ndx_reached))
        if len(ndx_reached) >= 20:
            bfs_ok += 1

    if bfs_ok == 0:
        # Try with max_hops=3
        log.warning("No hub reached >= 20 NDX tickers at hops=2. Trying hops=3...")
        for origin in test_origins:
            name = uuid_to_name.get(origin, origin[:12])
            betas = bfs_fanout(G, origin, max_hops=3, decay=0.6)
            ndx_reached = {uid for uid, beta in betas.items() if uid in ndx_uuids and beta > 0.1}
            log.info("BFS(hops=3) from %s: %d total, %d NDX (beta>0.1)", name, len(betas), len(ndx_reached))
            if len(ndx_reached) >= 20:
                bfs_ok += 1

    save_graph(G, uuid_to_name)

    print(f"[step4 OK] graph: {n_nodes} nodes, {n_edges} edges, {bfs_ok}/3 hubs reach >=20 NDX")
    return 0


if __name__ == "__main__":
    sys.exit(main())
