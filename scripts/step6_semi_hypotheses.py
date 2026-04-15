"""Step 6 — Semiconductor agent: Cala context → 10 validated hypotheses.

Gates:
  (a) exactly 10 hypotheses emitted
  (b) 10/10 parse as valid JSON matching schema
  (c) each hypothesis has ≥1 source UUID in our allow-list
  (d) all source_dates ≤ 2025-04-15
  (e) each effect_target resolves to a ticker in the NDX universe
"""
from __future__ import annotations

import logging

from abrollo.agents.semi_agent import run

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def main() -> None:
    payload = run()
    # Gate evaluation
    ok = payload["valid_count"] == 10 and payload["raw_count"] == 10
    print("=" * 60)
    print(f"Raw:     {payload['raw_count']}")
    print(f"Valid:   {payload['valid_count']}")
    print(f"Rejects: {payload['reject_count']}")
    if not ok:
        print("GATE FAILED — see /data/hypotheses/semi.json for rejects.")
        raise SystemExit(1)
    print("GATE PASSED — 10/10 hypotheses validated.")


if __name__ == "__main__":
    main()
