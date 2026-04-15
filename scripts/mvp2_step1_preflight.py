"""MVP-2 Step 1 — sanity check MVP-1 reuse surface still loads.

Per plan §3 Step 1:
  (a) load data/nasdaq100_uuids.json, assert 99 entries
  (b) instantiate CalaClient, do one entity_search, assert 200
  (c) import opt.cvar, submit.validator, submit.client without errors

Exit 0 on success with [preflight OK].
"""
from __future__ import annotations

import logging
import sys

from abrollo.cala.client import CalaClient
from abrollo.cala.ndx import load_resolutions

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("mvp2.step1")


def main() -> int:
    # (a) NDX UUIDs load.
    res = load_resolutions()
    hits = res.get("hits") or []
    if len(hits) != 99:
        log.error("expected 99 hits in nasdaq100_uuids.json, got %d", len(hits))
        return 1
    log.info("[a] nasdaq100_uuids.json OK — %d hits", len(hits))

    # (b) Cala client + one entity_search.
    client = CalaClient()
    resp = client.entity_search(name="Apple", entity_types=["Company"], limit=3)
    entities = resp.get("entities") or []
    if not entities:
        log.error("entity_search('Apple') returned no entities: %r", resp)
        return 2
    log.info("[b] entity_search OK — %d entities, top=%r", len(entities), entities[0].get("name"))

    # (c) imports exercise.
    from abrollo.opt import cvar  # noqa: F401
    from abrollo.submit import client as _sub_client  # noqa: F401
    from abrollo.submit import validator as _sub_val  # noqa: F401
    log.info("[c] imports OK — abrollo.opt.cvar, abrollo.submit.{client,validator}")

    print("[preflight OK]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
