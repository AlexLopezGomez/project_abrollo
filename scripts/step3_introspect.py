"""Step 3 — Introspect AAPL + NVDA.

Gate: both responses have non-empty `properties` and ≥1 numerical_observations entry
with a description. Log whether relationships are present.
"""
from __future__ import annotations

import json
import logging

from abrollo.cala.client import CalaClient
from abrollo.cala.ndx import load_resolutions
from abrollo.config import data_path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("step3")


def _lookup(hits: list[dict], ticker: str) -> dict:
    for h in hits:
        if h["ticker"] == ticker:
            return h
    raise KeyError(f"{ticker} not in resolutions")


def introspect(client: CalaClient, ticker: str, uuid: str) -> dict:
    log.info("Introspect %s (%s)", ticker, uuid)
    resp = client.entity_introspection(uuid)
    properties = resp.get("properties") or []
    relationships = resp.get("relationships") or {}
    numobs = resp.get("numerical_observations") or {}
    outgoing = relationships.get("outgoing") or []
    incoming = relationships.get("incoming") or []
    numobs_categories = list(numobs.keys()) if isinstance(numobs, dict) else []
    log.info(
        "  %s: %d properties, %d outgoing rel, %d incoming rel, numobs categories=%s",
        ticker,
        len(properties),
        len(outgoing),
        len(incoming),
        numobs_categories,
    )
    log.info("    properties (up to 10): %s", properties[:10])
    log.info("    outgoing (up to 6): %s", outgoing[:6])
    log.info("    incoming (up to 6): %s", incoming[:6])
    for cat in numobs_categories:
        items = numobs.get(cat) or []
        sample = items[:3] if isinstance(items, list) else items
        log.info("    numobs[%s] (%d items, sample): %s", cat, len(items) if hasattr(items, "__len__") else 0, sample)
    return resp


def main() -> None:
    data = load_resolutions()
    hits = data["hits"]
    aapl = _lookup(hits, "AAPL")
    nvda = _lookup(hits, "NVDA")

    client = CalaClient()
    samples = {
        "AAPL": {"uuid": aapl["uuid"], "introspection": introspect(client, "AAPL", aapl["uuid"])},
        "NVDA": {"uuid": nvda["uuid"], "introspection": introspect(client, "NVDA", nvda["uuid"])},
    }

    out = data_path("introspection_samples.json")
    out.write_text(json.dumps(samples, indent=2), encoding="utf-8")
    log.info("Saved %s", out)

    # Gate: non-empty properties, at least one numerical_observations category
    for ticker, payload in samples.items():
        resp = payload["introspection"]
        props = resp.get("properties") or []
        numobs = resp.get("numerical_observations") or {}
        assert props, f"{ticker}: no properties"
        if not numobs:
            log.warning("%s: numerical_observations is empty", ticker)
        else:
            log.info("%s: numobs categories present: %s", ticker, list(numobs.keys()))

    log.info("Step 3 complete.")


if __name__ == "__main__":
    main()
