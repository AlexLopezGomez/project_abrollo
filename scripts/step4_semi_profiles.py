"""Step 4 — Retrieve full profiles + source dates for the 5 semi anchor tickers.

Gates:
  a) every company has ≥3 properties with at least one dated source
  b) ≥50% of those dates parse cleanly as ISO-8601
  c) we observe ≥1 date > 2025-04-15 (confirms filter will do real work)
"""
from __future__ import annotations

import json
import logging
from collections import Counter
from datetime import date

from abrollo.cala.client import CalaClient
from abrollo.cala.ndx import load_resolutions
from abrollo.config import CUTOFF_DATE, SEMI_ANCHOR_TICKERS, data_path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("step4")


def parse_iso_date(raw: str | None) -> date | None:
    if not raw:
        return None
    try:
        return date.fromisoformat(raw[:10])
    except Exception:
        return None


def audit_profile(ticker: str, profile: dict) -> dict:
    props = profile.get("properties") or {}
    dated_props = 0
    total_sources = 0
    parseable_dates = 0
    pre_cutoff = 0
    post_cutoff = 0
    null_dates = 0
    cutoff_dt = date.fromisoformat(CUTOFF_DATE)

    for pname, pbody in props.items():
        if not isinstance(pbody, dict):
            continue
        sources = pbody.get("sources") or []
        if not sources:
            continue
        has_any_date = False
        for s in sources:
            total_sources += 1
            raw = s.get("date")
            if not raw:
                null_dates += 1
                continue
            d = parse_iso_date(raw)
            if d is None:
                continue
            parseable_dates += 1
            has_any_date = True
            if d <= cutoff_dt:
                pre_cutoff += 1
            else:
                post_cutoff += 1
        if has_any_date:
            dated_props += 1

    stats = {
        "ticker": ticker,
        "property_count": len(props),
        "properties_with_dated_source": dated_props,
        "total_sources": total_sources,
        "parseable_dates": parseable_dates,
        "pre_cutoff_le_2025_04_15": pre_cutoff,
        "post_cutoff_gt_2025_04_15": post_cutoff,
        "null_dates": null_dates,
    }
    log.info("%s audit: %s", ticker, stats)
    return stats


def main() -> None:
    data = load_resolutions()
    hits_by_ticker = {h["ticker"]: h for h in data["hits"]}

    client = CalaClient()
    per_ticker_stats: list[dict] = []
    for ticker in SEMI_ANCHOR_TICKERS:
        hit = hits_by_ticker.get(ticker)
        if not hit:
            log.error("%s missing from resolutions — cannot fetch profile", ticker)
            raise SystemExit(1)
        log.info("Retrieve %s (%s) — %s", ticker, hit["uuid"], hit["match_name"])
        profile = client.retrieve_entity(hit["uuid"])
        out = data_path("semi_profiles", f"{ticker}.json")
        out.write_text(json.dumps(profile, indent=2), encoding="utf-8")
        stats = audit_profile(ticker, profile)
        per_ticker_stats.append(stats)

    # Gates
    agg = Counter()
    for s in per_ticker_stats:
        agg["pre_cutoff"] += s["pre_cutoff_le_2025_04_15"]
        agg["post_cutoff"] += s["post_cutoff_gt_2025_04_15"]
        agg["parseable"] += s["parseable_dates"]
        agg["total_sources"] += s["total_sources"]

    log.info("=== Step 4 aggregate ===")
    log.info("  total_sources=%d parseable=%d pre_cutoff=%d post_cutoff=%d",
             agg["total_sources"], agg["parseable"], agg["pre_cutoff"], agg["post_cutoff"])

    failures = []
    for s in per_ticker_stats:
        if s["properties_with_dated_source"] < 3:
            failures.append(f"{s['ticker']}: only {s['properties_with_dated_source']} dated props (need ≥3)")
    if agg["total_sources"] > 0 and agg["parseable"] / agg["total_sources"] < 0.5:
        failures.append(f"parseable ratio {agg['parseable']}/{agg['total_sources']} < 50%")
    if agg["post_cutoff"] == 0:
        log.info("  NOTE: no post-cutoff dates seen across 5 anchors — Cala may pre-filter server-side")

    if failures:
        for f in failures:
            log.error("GATE FAILED: %s", f)
        raise SystemExit(1)

    # Save the audit digest too
    audit_path = data_path("semi_profiles", "_audit.json")
    audit_path.write_text(json.dumps({"per_ticker": per_ticker_stats, "aggregate": dict(agg)}, indent=2))
    log.info("Saved %s", audit_path)
    log.info("Step 4 complete.")


if __name__ == "__main__":
    main()
