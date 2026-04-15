"""Step 9 — CVaR optimize.

Gates:
  - solver status optimal/optimal_inaccurate
  - ≥50 non-zero tickers
  - each non-zero weight ≥ $5,000
  - sum of weights == $1,000,000 (exact integer USD)
"""
from __future__ import annotations

import logging

import pandas as pd

from abrollo.config import data_path
from abrollo.opt.cvar import BUDGET, MIN_TICKERS, MIN_WEIGHT, optimize, save

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("step9")


def main() -> None:
    R = pd.read_parquet(data_path("scenarios", "mvp.parquet"))
    outcome = optimize(R)
    save(outcome)

    log.info("Status: %s (solver=%s)", outcome.status, outcome.solver)
    log.info("E[return]: %.4f  CVaR_5: %.4f", outcome.expected_return_pct, outcome.cvar5_pct)
    log.info("Non-zero tickers: %d", outcome.n_nonzero)
    top = sorted(outcome.weights.items(), key=lambda kv: -kv[1])[:10]
    log.info("Top 10: %s", top)

    assert outcome.status in ("optimal", "optimal_inaccurate"), \
        f"Bad solver status: {outcome.status}"
    assert outcome.n_nonzero >= MIN_TICKERS, \
        f"Only {outcome.n_nonzero} tickers, need ≥{MIN_TICKERS}"
    assert all(w >= MIN_WEIGHT for w in outcome.weights.values()), \
        "Some non-zero weights under $5000"
    total = sum(outcome.weights.values())
    assert total == int(BUDGET), f"Sum = {total}, expected {int(BUDGET)}"

    log.info("Step 9 GATE PASSED — sum=${:,} across {} tickers".format(total, outcome.n_nonzero))


if __name__ == "__main__":
    main()
