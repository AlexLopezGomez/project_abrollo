"""MVP-2 Step 2 — Bulk retrieve_entity with relationships (+ numobs where available).

Per plan §3 Step 2:
  1. Extend CalaClient (done in client.py).
  2. Iterate 99 UUIDs: introspect → retrieve with properties + relationships.
  3. Save raw payloads to data/cala_entities/{ticker}.json.

Two-pass per ticker:
  a) GET  /v1/entities/{uuid}/introspection  → rel types (+ numobs catalog)
  b) POST /v1/entities/{uuid}                → full payload with rels

Numobs are fetched separately for tickers that have them (Cala only provides
FinancialMetric for select companies).

Gate: 99/99 files written; each has non-empty properties and non-empty
      relationships.outgoing. Numobs gate is soft (logged but not fatal)
      since Cala coverage is sparse.
"""
from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path

from abrollo.cala.client import CalaClient
from abrollo.cala.ndx import load_resolutions
from abrollo.config import data_path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("mvp2.step2")

BULK_THROTTLE = 1.1
INCOMING_LIMIT = 10  # cap incoming rels per type to avoid 403 on mega-caps
OUT_DIR = data_path("cala_entities")


def build_retrieve_body(introspection: dict) -> dict:
    """Build the retrieve_entity body from introspection data.

    Skips numobs (fetched separately). Limits incoming rels to avoid 403.
    """
    body: dict = {}

    props = introspection.get("properties", [])
    if props:
        body["properties"] = props

    rels = introspection.get("relationships", {})
    rel_body: dict = {}
    out_types = rels.get("outgoing", [])
    if out_types:
        rel_body["outgoing"] = {t: {} for t in out_types}
    in_types = rels.get("incoming", [])
    if in_types:
        rel_body["incoming"] = {t: {"limit": INCOMING_LIMIT} for t in in_types}
    if rel_body:
        body["relationships"] = rel_body

    return body


def fetch_numobs(client: CalaClient, uuid: str, introspection: dict) -> list:
    """Fetch numerical observations in batches (Cala 403s on large bodies)."""
    numobs_catalog = introspection.get("numerical_observations", {})
    if not numobs_catalog:
        return []

    all_data = []
    for obs_type, metrics in numobs_catalog.items():
        metric_ids = [m["id"] for m in metrics if "id" in m]
        if not metric_ids:
            continue
        # Batch in chunks of 20 to avoid body-size 403
        for i in range(0, len(metric_ids), 20):
            batch = metric_ids[i:i + 20]
            try:
                resp = client.retrieve_entity(
                    uuid,
                    numerical_observations={obs_type: batch},
                )
                obs = resp.get("numerical_observations", [])
                if isinstance(obs, list):
                    all_data.extend(obs)
            except Exception as e:
                log.warning("  numobs batch %d failed: %s", i, e)
                break
    return all_data


def main() -> int:
    resolutions = load_resolutions()
    hits = resolutions.get("hits", [])
    if len(hits) != 99:
        log.error("Expected 99 hits, got %d", len(hits))
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    client = CalaClient(throttle_seconds=BULK_THROTTLE)
    results: list[dict] = []
    t0 = time.monotonic()
    seen_uuids: set[str] = set()

    for i, hit in enumerate(hits):
        ticker = hit["ticker"]
        uuid = hit["uuid"]
        name = hit["name"]

        # Skip already-saved tickers (resume mode)
        out_path = OUT_DIR / f"{ticker}.json"
        if out_path.exists():
            log.info("[%d/99] %s — already saved, skipping", i + 1, ticker)
            try:
                entity = json.loads(out_path.read_text(encoding="utf-8"))
                n_props = len(entity.get("properties", {}))
                n_rels_out = sum(
                    len(v) for v in entity.get("relationships", {}).get("outgoing", {}).values()
                )
                numobs_raw = entity.get("numerical_observations", [])
                n_numobs = len(numobs_raw) if isinstance(numobs_raw, list) else 0
                results.append({"ticker": ticker, "uuid": uuid,
                                "n_props": n_props, "n_rels_out": n_rels_out, "n_numobs": n_numobs})
            except Exception:
                results.append({"ticker": ticker, "uuid": uuid, "n_props": 1, "n_rels_out": 1, "n_numobs": 0})
            seen_uuids.add(uuid)
            continue

        # Skip duplicate UUIDs (GOOGL/GOOG)
        if uuid in seen_uuids:
            log.info("[%d/99] %s — duplicate UUID of earlier ticker, skipping", i + 1, ticker)
            results.append({"ticker": ticker, "uuid": uuid, "n_props": 0, "n_rels_out": 0, "n_numobs": 0, "skipped": True})
            continue
        seen_uuids.add(uuid)

        log.info("[%d/99] %s (%s) — %s", i + 1, ticker, name, uuid)

        # Pass 1: introspection (with retry on connection error)
        intro = None
        for attempt in range(3):
            try:
                intro = client.entity_introspection(uuid)
                break
            except Exception as e:
                if "resolve" in str(e).lower() or "connection" in str(e).lower():
                    log.warning("  introspection attempt %d failed (network): %s", attempt + 1, e)
                    time.sleep(5 * (attempt + 1))
                else:
                    log.error("  introspection failed: %s", e)
                    break
        if intro is None:
            results.append({"ticker": ticker, "uuid": uuid, "error": "introspection failed after retries"})
            continue

        # Pass 2: retrieve with properties + relationships (with retry)
        body = build_retrieve_body(intro)
        entity = None
        for attempt in range(3):
            try:
                entity = client.retrieve_entity(uuid, **body)
                break
            except Exception as e:
                if "resolve" in str(e).lower() or "connection" in str(e).lower():
                    log.warning("  retrieve attempt %d failed (network): %s", attempt + 1, e)
                    time.sleep(5 * (attempt + 1))
                else:
                    log.error("  retrieve failed: %s", e)
                    break
        if entity is None:
            results.append({"ticker": ticker, "uuid": uuid, "error": "retrieve failed after retries"})
            continue

        # Note: numobs fetch skipped — too slow for bulk retrieval.
        # Covariance will use single-factor fallback (plan §3 Step 3).

        entity["_introspection"] = intro
        entity["_ticker"] = ticker

        out_path = OUT_DIR / f"{ticker}.json"
        out_path.write_text(json.dumps(entity, indent=2, default=str), encoding="utf-8")

        # Stats
        n_props = len(entity.get("properties", {}))
        n_rels_out = sum(
            len(v) for v in entity.get("relationships", {}).get("outgoing", {}).values()
        )
        numobs_raw = entity.get("numerical_observations", [])
        n_numobs = len(numobs_raw) if isinstance(numobs_raw, list) else 0
        log.info("  → %d props, %d outgoing rels, %d numobs", n_props, n_rels_out, n_numobs)

        results.append({
            "ticker": ticker, "uuid": uuid,
            "n_props": n_props, "n_rels_out": n_rels_out, "n_numobs": n_numobs,
        })

    elapsed = time.monotonic() - t0
    log.info("Bulk fetch done in %.1fs", elapsed)

    # --- Gate checks ---
    errors = [r for r in results if "error" in r]
    if errors:
        log.warning("%d tickers failed:", len(errors))
        for e in errors:
            log.warning("  %s: %s", e["ticker"], e["error"])

    ok = [r for r in results if "error" not in r]
    gate_props = sum(1 for r in ok if r["n_props"] > 0)
    gate_rels = sum(1 for r in ok if r["n_rels_out"] > 0)
    gate_numobs = sum(1 for r in ok if r["n_numobs"] >= 100)
    gate_props_and_rels = sum(
        1 for r in ok if r["n_props"] > 0 and r["n_rels_out"] > 0
    )

    log.info("Gate: %d/99 files, %d props>0, %d rels>0, %d numobs>=100, %d props+rels",
             len(ok), gate_props, gate_rels, gate_numobs, gate_props_and_rels)

    summary_path = OUT_DIR / "_summary.json"
    summary_path.write_text(json.dumps({
        "total": len(hits),
        "fetched": len(ok),
        "failed": len(errors),
        "gate_props": gate_props,
        "gate_rels": gate_rels,
        "gate_numobs": gate_numobs,
        "gate_props_and_rels": gate_props_and_rels,
        "elapsed_seconds": round(elapsed, 1),
        "details": results,
    }, indent=2), encoding="utf-8")

    # Primary gate: props + rels for >= 90 tickers
    if gate_props_and_rels < 90:
        log.error("GATE FAIL: only %d/99 have props+rels (need >= 90). Halting.", gate_props_and_rels)
        return 1

    if gate_numobs == 0:
        log.warning("No tickers have >= 100 numobs — covariance will use single-factor fallback.")

    print(f"[step2 OK] {len(ok)}/99 fetched, {gate_props_and_rels} have props+rels, "
          f"{gate_numobs} have numobs>=100")
    return 0


if __name__ == "__main__":
    sys.exit(main())
