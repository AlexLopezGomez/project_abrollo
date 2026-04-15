"""Step 11 — Dry-run + real POST to the Convex submission endpoint.

Three modes:
  --dry-run (default)  : print the request body, no network call.
  --safe               : equal-weight 50-ticker $20K portfolio, real POST.
  --real               : POST the Step 9 output.

Gate (real): HTTP 200 with a parseable body including portfolio value.
"""
from __future__ import annotations

import argparse
import json
import logging

from abrollo.cala.ndx import load_resolutions
from abrollo.config import data_path
from abrollo.submit.client import build_body, submit
from abrollo.submit.validator import load_portfolio, validate_submission

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("step11")


def _safe_equal_weight() -> dict[str, int]:
    # 50 × $20,000 = $1,000,000 equal-weight from resolved NDX alphabetical.
    hits = sorted(h["ticker"] for h in load_resolutions()["hits"])[:50]
    return {t: 20_000 for t in hits}


def _real() -> dict[str, int]:
    return load_portfolio(data_path("portfolios", "mvp.json"))


def main() -> None:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--dry-run", action="store_true", default=True)
    g.add_argument("--safe", action="store_true")
    g.add_argument("--real", action="store_true")
    args = ap.parse_args()

    if args.real:
        weights = _real()
        label = "REAL (Step 9 CVaR output)"
    elif args.safe:
        weights = _safe_equal_weight()
        label = "SAFE (50 × $20K equal-weight)"
    else:
        weights = _real()
        label = "DRY-RUN (Step 9 CVaR output)"

    log.info("Portfolio: %s — %d tickers, sum=$%s", label, len(weights), sum(weights.values()))
    ok, reasons = validate_submission(weights)
    if not ok:
        log.error("Pre-submit validator REJECTED: %s", reasons)
        raise SystemExit(1)
    log.info("Pre-submit validator ✓")

    if not (args.real or args.safe):
        log.info("Dry-run only — request body would be:")
        print(json.dumps(build_body(weights), indent=2)[:1500] + "\n...")
        return

    log.info("POSTing for real to Convex...")
    result = submit(weights)
    log.info("HTTP %d", result.status)
    log.info("Response: %s", json.dumps(result.body, indent=2)[:1200] if isinstance(result.body, dict) else str(result.body)[:1200])
    if result.status != 200:
        raise SystemExit(1)
    log.info("Step 11 GATE PASSED")


if __name__ == "__main__":
    main()
