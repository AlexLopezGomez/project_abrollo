"""Step 5 — Unit-test the cutoff filter on the NVDA profile saved in Step 4.

Asserts:
  (a) output has no source date > cutoff
  (b) output has ≥1 property remaining
  (c) function is idempotent
"""
from __future__ import annotations

import json
import logging
from datetime import date

from abrollo.cala.cutoff import filter_entity_by_cutoff
from abrollo.config import CUTOFF_DATE, data_path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("step5")


def all_dates(entity: dict) -> list[str]:
    dates: list[str] = []
    for pbody in (entity.get("properties") or {}).values():
        for s in (pbody.get("sources") or []):
            d = s.get("date")
            if d:
                dates.append(d)
    return dates


def main() -> None:
    src = data_path("semi_profiles", "NVDA.json")
    nvda = json.loads(src.read_text(encoding="utf-8"))
    cutoff = date.fromisoformat(CUTOFF_DATE)

    before_props = len(nvda.get("properties") or {})
    before_dates = all_dates(nvda)
    before_post = sum(1 for d in before_dates if date.fromisoformat(d[:10]) > cutoff)
    log.info("Before filter: %d properties, %d sources (%d post-cutoff)",
             before_props, len(before_dates), before_post)

    filtered = filter_entity_by_cutoff(nvda)
    after_props = len(filtered.get("properties") or {})
    after_dates = all_dates(filtered)
    after_post = sum(1 for d in after_dates if date.fromisoformat(d[:10]) > cutoff)
    log.info("After filter:  %d properties, %d sources (%d post-cutoff)",
             after_props, len(after_dates), after_post)

    # Gate (a)
    assert after_post == 0, f"Gate A failed: {after_post} post-cutoff sources remain"
    log.info("Gate A ✓ no post-cutoff sources remain")

    # Gate (b) — at least 1 property survives (NVDA had pre-cutoff sources; AVGO would fail)
    assert after_props >= 1, "Gate B failed: no properties left after filter"
    log.info("Gate B ✓ %d properties remain", after_props)

    # Gate (c) — idempotent
    twice = filter_entity_by_cutoff(filtered)
    assert json.dumps(twice, sort_keys=True) == json.dumps(filtered, sort_keys=True), \
        "Gate C failed: filter is not idempotent"
    log.info("Gate C ✓ idempotent")

    # Print surviving property names for the retrospective
    log.info("Surviving properties: %s", sorted((filtered.get("properties") or {}).keys()))
    log.info("Step 5 complete.")


if __name__ == "__main__":
    main()
