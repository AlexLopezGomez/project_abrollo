"""Submission-rule validator (§3 Step 10 of the plan).

Checks every rule the Convex endpoint enforces, plus extra audits:
- MVP-1: lookahead on hypothesis effect_target
- MVP-2: placeholder-date rejector + origin-not-ticker check
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from abrollo.cala.ndx import load_resolutions
from abrollo.config import CUTOFF_DATE, data_path

TOTAL_USD = 1_000_000
MIN_WEIGHT_USD = 5_000
MIN_TICKERS = 50


def _hypothesis_lookahead_ok(tickers: set[str]) -> tuple[bool, list[str]]:
    p = data_path("hypotheses", "semi.json")
    if not p.exists():
        return True, []
    payload = json.loads(p.read_text(encoding="utf-8"))
    hyp = payload.get("hypotheses") or []
    cutoff = date.fromisoformat(CUTOFF_DATE)
    failures: list[str] = []
    for h in hyp:
        target = h.get("effect_target")
        if target not in tickers:
            continue
        for d in h.get("source_dates") or []:
            try:
                if date.fromisoformat(d) > cutoff:
                    failures.append(f"hypothesis {h.get('id')} cites date {d} > cutoff")
            except ValueError:
                failures.append(f"hypothesis {h.get('id')} has unparseable date {d}")
    return not failures, failures


def _mvp2_placeholder_date_check(allowed_dates: set[str] | None = None) -> tuple[bool, list[str]]:
    """MVP-2 Step 9: reject hypotheses whose source_dates are not in allow-list."""
    p = data_path("hypotheses", "mvp2.json")
    if not p.exists():
        return True, []
    hyps = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(hyps, list):
        hyps = hyps.get("hypotheses", [])

    if allowed_dates is None:
        allowed_dates = _collect_allowed_dates()

    failures: list[str] = []
    for h in hyps:
        hid = h.get("id", "?")
        for d in h.get("source_dates", []):
            if d not in allowed_dates:
                failures.append(f"hypothesis {hid}: source_date {d} not in allow-list")
    return not failures, failures


def _mvp2_origin_not_ticker_check() -> tuple[bool, list[str]]:
    """MVP-2 Step 9: origin_entity_uuid must NOT be a ticker UUID."""
    p = data_path("hypotheses", "mvp2.json")
    if not p.exists():
        return True, []
    hyps = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(hyps, list):
        hyps = hyps.get("hypotheses", [])

    resolved = load_resolutions()
    ticker_uuids = {h["uuid"] for h in resolved.get("hits", [])}

    failures: list[str] = []
    for h in hyps:
        origin = h.get("origin_entity_uuid", "")
        if origin in ticker_uuids:
            failures.append(
                f"hypothesis {h.get('id', '?')}: origin {origin} is a ticker UUID "
                f"(must be a macro/thematic entity)")
    return not failures, failures


def _collect_allowed_dates() -> set[str]:
    """Collect all property source dates <= cutoff from entity files."""
    entities_dir = data_path("cala_entities")
    allowed: set[str] = set()
    if not entities_dir.exists():
        return allowed
    for fpath in entities_dir.glob("*.json"):
        if fpath.name.startswith("_"):
            continue
        try:
            entity = json.loads(fpath.read_text(encoding="utf-8"))
        except Exception:
            continue
        props = entity.get("properties", {})
        if not isinstance(props, dict):
            continue
        for pbody in props.values():
            if not isinstance(pbody, dict):
                continue
            for src in pbody.get("sources", []):
                if isinstance(src, dict):
                    d = src.get("date", "")
                    if isinstance(d, str) and d[:10] <= CUTOFF_DATE:
                        allowed.add(d[:10])
    return allowed


def validate_submission(
    weights: dict[str, int],
    mvp2: bool = False,
) -> tuple[bool, list[str]]:
    reasons: list[str] = []

    resolved = load_resolutions()
    ndx = {h["ticker"] for h in resolved["hits"]}

    if len(weights) < MIN_TICKERS:
        reasons.append(f"only {len(weights)} distinct tickers (need ≥{MIN_TICKERS})")

    for t in weights:
        if t != t.upper() or not t.isascii():
            reasons.append(f"ticker {t!r} not ASCII-upper")

    for t, w in weights.items():
        if not isinstance(w, int):
            reasons.append(f"{t} weight not int: {w!r}")
            continue
        if w < MIN_WEIGHT_USD:
            reasons.append(f"{t} weight ${w} < minimum ${MIN_WEIGHT_USD}")

    total = sum(weights.values())
    if total != TOTAL_USD:
        reasons.append(f"sum ${total:,} != ${TOTAL_USD:,}")

    outside = [t for t in weights if t not in ndx]
    if outside:
        reasons.append(f"tickers not in resolved NDX universe: {outside}")

    ok, hyp_reasons = _hypothesis_lookahead_ok(set(weights.keys()))
    if not ok:
        reasons.extend(hyp_reasons)

    # MVP-2 extra checks
    if mvp2:
        ok2, r2 = _mvp2_placeholder_date_check()
        if not ok2:
            reasons.extend(r2)

        ok3, r3 = _mvp2_origin_not_ticker_check()
        if not ok3:
            reasons.extend(r3)

    return not reasons, reasons


def load_portfolio(path: str | Path) -> dict[str, int]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return {t: int(w) for t, w in (raw.get("weights") or {}).items()}
