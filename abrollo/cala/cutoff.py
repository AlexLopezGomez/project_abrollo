"""Cutoff filter — the no-lookahead firewall.

Every Cala `source` has a `date`. Anything > CUTOFF must be dropped. A property
whose entire source set falls after cutoff is removed. Same logic applies to
`knowledge_search` context arrays (each item also carries a `date`).

This is the mechanical enforcement of "no market data or news after
2025-04-15" — see IDEA.md and 01-mvp-plan.md §0 gate 3.
"""
from __future__ import annotations

import copy
from datetime import date
from typing import Any

from abrollo.config import CUTOFF_DATE


def _parse(raw: Any) -> date | None:
    if not raw or not isinstance(raw, str):
        return None
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None


def _is_source_ok(src: dict, cutoff: date) -> bool:
    """A source passes if its date is present AND <= cutoff.

    Missing/unparseable dates are rejected — conservative default per R3 mitigation.
    """
    d = _parse(src.get("date"))
    return d is not None and d <= cutoff


def _filter_sources(sources: list, cutoff: date) -> list:
    return [s for s in sources if isinstance(s, dict) and _is_source_ok(s, cutoff)]


def filter_entity_by_cutoff(
    entity: dict[str, Any], cutoff_date: str = CUTOFF_DATE
) -> dict[str, Any]:
    """Return a deep-copied entity with post-cutoff sources stripped.

    - properties[p].sources drops any entry whose date > cutoff_date or is unparseable.
    - A property whose *all* sources fall after cutoff (i.e. empty after filter) is removed.
    - numerical_observations entries that carry a `date` field get the same treatment; those
      that don't carry dates are kept as-is (catalog metadata).
    - relationships are kept as-is (no per-edge date surfaced by the REST API today).
    """
    cutoff = date.fromisoformat(cutoff_date)
    out = copy.deepcopy(entity)

    props = out.get("properties")
    if isinstance(props, dict):
        keep: dict[str, Any] = {}
        for pname, pbody in props.items():
            if not isinstance(pbody, dict):
                # Unexpected shape — conservatively drop.
                continue
            sources = pbody.get("sources") or []
            filtered = _filter_sources(sources, cutoff)
            if not filtered:
                # All sources were post-cutoff or undated → kill the property.
                continue
            pbody["sources"] = filtered
            keep[pname] = pbody
        out["properties"] = keep

    numobs = out.get("numerical_observations")
    if isinstance(numobs, list):
        cleaned = []
        for obs in numobs:
            if not isinstance(obs, dict):
                continue
            raw_date = obs.get("date")
            if raw_date is None:
                # Catalog metadata (description/unit/taxonomy) — keep.
                cleaned.append(obs)
                continue
            d = _parse(raw_date)
            if d is not None and d <= cutoff:
                cleaned.append(obs)
        out["numerical_observations"] = cleaned

    return out


def filter_knowledge_search(
    payload: dict[str, Any], cutoff_date: str = CUTOFF_DATE
) -> dict[str, Any]:
    """Filter the `context` array of a knowledge_search response by cutoff date.

    Context entries that lack a date field are dropped (conservative).
    """
    cutoff = date.fromisoformat(cutoff_date)
    out = copy.deepcopy(payload)
    ctx = out.get("context")
    if isinstance(ctx, list):
        kept = []
        for item in ctx:
            if not isinstance(item, dict):
                continue
            d = _parse(item.get("date"))
            if d is not None and d <= cutoff:
                kept.append(item)
        out["context"] = kept
    return out
