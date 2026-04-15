"""Step 10 — Validate portfolio against submission rules.

Gates:
  (a) validator green-lights the Step 9 output
  (b) validator rejects a deliberately-broken portfolio (49 tickers) with a reason
"""
from __future__ import annotations

import logging

from abrollo.config import data_path
from abrollo.submit.validator import load_portfolio, validate_submission

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("step10")


def main() -> None:
    portfolio_path = data_path("portfolios", "mvp.json")
    weights = load_portfolio(portfolio_path)
    log.info("Loaded %d-ticker portfolio from %s", len(weights), portfolio_path)

    ok, reasons = validate_submission(weights)
    if not ok:
        log.error("Step 9 output FAILED validation: %s", reasons)
        raise SystemExit(1)
    log.info("Gate (a) ✓ Step 9 portfolio passes all %d rules", 7)

    # Craft a bad portfolio: 49 tickers taken from the good one.
    bad = dict(list(weights.items())[:49])
    # Re-balance to hit $1M so only the ticker-count rule fails.
    short = 1_000_000 - sum(bad.values())
    first = next(iter(bad))
    bad[first] += short
    ok_bad, reasons_bad = validate_submission(bad)
    assert not ok_bad, "Gate B failed: validator accepted a 49-ticker portfolio"
    log.info("Gate (b) ✓ 49-ticker portfolio rejected: %s", reasons_bad)

    log.info("Step 10 GATE PASSED")


if __name__ == "__main__":
    main()
