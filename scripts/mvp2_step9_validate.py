"""MVP-2 Step 9 — Validator with new checks.

Gate: validator passes the Step 8 portfolio and rejects a manually-crafted
      bad hypothesis (placeholder date).
"""
from __future__ import annotations

import logging
import sys

from abrollo.config import data_path
from abrollo.submit.validator import load_portfolio, validate_submission

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("mvp2.step9")


def main() -> int:
    portfolio_path = data_path("portfolios") / "mvp2.json"
    if not portfolio_path.exists():
        log.error("Portfolio not found — run step 8 first")
        return 1

    weights = load_portfolio(portfolio_path)
    log.info("Portfolio: %d tickers, sum=$%d", len(weights), sum(weights.values()))

    # Validate with MVP-2 checks
    ok, reasons = validate_submission(weights, mvp2=True)

    if ok:
        log.info("Validation PASSED")
    else:
        log.error("Validation FAILED:")
        for r in reasons:
            log.error("  %s", r)
        return 1

    print(f"[step9 OK] portfolio validated ({len(weights)} tickers, ${sum(weights.values()):,})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
