"""Step 2 — Resolve NASDAQ-100 tickers to Cala Company UUIDs.

Gate: ≥90/100 tickers resolved. Misses recorded but not fixed during MVP.
"""
from __future__ import annotations

import logging

from abrollo.cala.client import CalaClient
from abrollo.cala.ndx import (
    SAFE_THROTTLE,
    fetch_ndx_from_wikipedia,
    resolve_tickers,
    save_resolutions,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("step2")


def main() -> None:
    pairs = fetch_ndx_from_wikipedia()
    log.info("Resolving %d tickers at %.2fs/call (~%.0f/min)", len(pairs), SAFE_THROTTLE, 60 / SAFE_THROTTLE)
    client = CalaClient(throttle_seconds=SAFE_THROTTLE)
    resolutions = resolve_tickers(pairs, client=client)
    save_resolutions(resolutions)

    hits = [r for r in resolutions if r.uuid]
    misses = [r for r in resolutions if not r.uuid]
    log.info("=== Step 2 summary ===")
    log.info("  %d hits / %d attempts", len(hits), len(resolutions))
    for m in misses:
        log.info("  MISS  %-6s  %s", m.ticker, m.name)
    # Gate: ≥90 hits out of whatever we scraped (at least 100 expected)
    if len(hits) < 90:
        log.error("GATE FAILED: only %d hits, need ≥90", len(hits))
        raise SystemExit(1)
    log.info("GATE PASSED: %d / %d resolved", len(hits), len(resolutions))


if __name__ == "__main__":
    main()
