"""Step 7 — Build + persist the 5-node DAG.

Gate: pgmpy BayesianNetwork builds without errors, check_model() is True,
we can query P(NVDA_return | TSMC=T, EC=T) and get a finite probability.
"""
from __future__ import annotations

import logging

from abrollo.dag.mvp_dag import build_model, query_nvda_conditional, save

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("step7")


def main() -> None:
    model = build_model()
    log.info("DAG nodes: %s", model.nodes())
    log.info("DAG edges: %s", model.edges())
    pkl, human = save(model)
    log.info("Saved pickle: %s", pkl)
    log.info("Saved human-readable: %s", human)

    p_down = query_nvda_conditional(model)
    log.info("P(NVDA_return=down | TSMC=T, export_control=T) = %.3f", p_down)
    assert 0.0 < p_down < 1.0, f"Query returned invalid probability: {p_down}"
    log.info("Step 7 GATE PASSED")


if __name__ == "__main__":
    main()
