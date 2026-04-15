"""Submission-rule validator (§3 Step 10 of the plan).

Checks every rule the Convex endpoint enforces, plus one extra: a lookahead audit
that every hypothesis whose effect_target appears in the portfolio has all
source_dates <= cutoff.
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


def validate_submission(weights: dict[str, int]) -> tuple[bool, list[str]]:
    reasons: list[str] = []

    resolved = load_resolutions()
    ndx = {h["ticker"] for h in resolved["hits"]}

    # 1. ≥50 distinct tickers
    if len(weights) < MIN_TICKERS:
        reasons.append(f"only {len(weights)} distinct tickers (need ≥{MIN_TICKERS})")

    # 2/3. ASCII upper-case, no duplicates (dict keys implicitly dedupe)
    for t in weights:
        if t != t.upper() or not t.isascii():
            reasons.append(f"ticker {t!r} not ASCII-upper")

    # 4. each weight ≥ $5000
    for t, w in weights.items():
        if not isinstance(w, int):
            reasons.append(f"{t} weight not int: {w!r}")
            continue
        if w < MIN_WEIGHT_USD:
            reasons.append(f"{t} weight ${w} < minimum ${MIN_WEIGHT_USD}")

    # 5. sum exactly $1M
    total = sum(weights.values())
    if total != TOTAL_USD:
        reasons.append(f"sum ${total:,} != ${TOTAL_USD:,}")

    # 6. every ticker in known NDX universe
    outside = [t for t in weights if t not in ndx]
    if outside:
        reasons.append(f"tickers not in resolved NDX universe: {outside}")

    # 7. lookahead audit on cited hypotheses
    ok, hyp_reasons = _hypothesis_lookahead_ok(set(weights.keys()))
    if not ok:
        reasons.extend(hyp_reasons)

    return not reasons, reasons


def load_portfolio(path: str | Path) -> dict[str, int]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return {t: int(w) for t, w in (raw.get("weights") or {}).items()}
