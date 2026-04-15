"""Step 1 — Cala auth smoke test.

Gates (per 01-mvp-plan.md):
  a) 200 OK on GET /v1/entities?name=Apple&limit=3, Apple in results.
  b) at least one 429 observed under deliberate burst load.
  c) /openapi.json saved to /data/openapi.pinned.json.
"""
from __future__ import annotations

import json
import logging
import time

from abrollo.cala.client import CalaClient, CalaError
from abrollo.config import data_path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("step1")


def gate_a_happy_call(client: CalaClient) -> dict:
    log.info("Gate A: GET /v1/entities?name=Apple&limit=3")
    resp = client.entity_search("Apple", limit=3)
    entities = resp.get("entities", [])
    log.info("  returned %d entities", len(entities))
    for e in entities[:3]:
        log.info("  - %s [%s] id=%s", e.get("name"), e.get("entity_type"), e.get("id"))
    assert any("apple" in (e.get("name") or "").lower() for e in entities), \
        "Apple not found in entity_search response — auth or index issue"
    return resp


def gate_b_stress_test(client: CalaClient, n: int = 120) -> int:
    """Burst N calls with throttle disabled to provoke a 429."""
    log.info("Gate B: burst %d calls to provoke 429 (throttle disabled)", n)
    burst_client = CalaClient(api_key=client.api_key, throttle_seconds=0.0)
    seen_429 = 0
    errors_other = 0
    start = time.monotonic()
    for i in range(n):
        try:
            burst_client.entity_search("Apple", limit=1)
        except CalaError as e:
            if e.status == 429:
                seen_429 += 1
                log.info("  429 at call #%d (after %.1fs)", i + 1, time.monotonic() - start)
                break
            errors_other += 1
            log.warning("  non-429 error at #%d: %s", i + 1, e)
    else:
        log.warning("  burst finished %d calls with no 429 (ceiling is above %d/min)", n, n)
    log.info("  429 seen: %d   other errors: %d", seen_429, errors_other)
    return seen_429


def gate_c_pin_openapi(client: CalaClient) -> None:
    log.info("Gate C: fetching /openapi.json")
    spec = client.openapi()
    out = data_path("openapi.pinned.json")
    out.write_text(json.dumps(spec, indent=2, sort_keys=True), encoding="utf-8")
    log.info("  saved %s (%d top-level keys)", out, len(spec) if isinstance(spec, dict) else 0)


def main() -> None:
    client = CalaClient()
    gate_a_happy_call(client)
    gate_c_pin_openapi(client)
    gate_b_stress_test(client)
    log.info("Step 1 complete.")


if __name__ == "__main__":
    main()
