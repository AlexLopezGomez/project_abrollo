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


def _is_relationship_ok(rel: dict, cutoff: date) -> bool:
    """A relationship passes if it has at least one source dated <= cutoff.

    - properties.sources must contain at least one entry with date <= cutoff.
    - valid_since (if present) must be <= cutoff.
    - valid_until is NOT used as rejection criterion (expired relations still existed).
    - If properties or sources are missing → reject (conservative).
    """
    props = rel.get("properties")
    if not isinstance(props, dict):
        return False

    # Check valid_since if present
    valid_since = _parse(props.get("valid_since"))
    if valid_since is not None and valid_since > cutoff:
        return False

    sources = props.get("sources")
    if not isinstance(sources, list) or not sources:
        return False

    return any(_is_source_ok(s, cutoff) for s in sources if isinstance(s, dict))


def filter_relationships(
    rels: dict[str, Any], cutoff_date: str = CUTOFF_DATE
) -> tuple[dict[str, Any], int, int]:
    """Filter outgoing/incoming relationships by cutoff date.

    Returns (filtered_rels, total_count, kept_count).
    """
    cutoff = date.fromisoformat(cutoff_date)
    out: dict[str, Any] = {}
    total = 0
    kept = 0

    for direction in ("outgoing", "incoming"):
        dir_data = rels.get(direction, {})
        if not isinstance(dir_data, dict):
            continue
        filtered_dir: dict[str, list] = {}
        for rel_type, targets in dir_data.items():
            if not isinstance(targets, list):
                continue
            filtered_targets = []
            for target in targets:
                total += 1
                if not isinstance(target, dict):
                    continue
                if _is_relationship_ok(target, cutoff):
                    filtered_targets.append(target)
                    kept += 1
            if filtered_targets:
                filtered_dir[rel_type] = filtered_targets
        if filtered_dir:
            out[direction] = filtered_dir

    return out, total, kept


def filter_entity_by_cutoff(
    entity: dict[str, Any], cutoff_date: str = CUTOFF_DATE
) -> dict[str, Any]:
    """Return a deep-copied entity with post-cutoff sources stripped.

    - properties[p].sources drops any entry whose date > cutoff_date or is unparseable.
    - A property whose *all* sources fall after cutoff (i.e. empty after filter) is removed.
    - numerical_observations entries that carry a `date` field get the same treatment; those
      that don't carry dates are kept as-is (catalog metadata).
    - relationships are filtered via filter_relationships() using source dates and valid_since.
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

    rels = out.get("relationships")
    if isinstance(rels, dict):
        filtered_rels, _total, _kept = filter_relationships(rels, cutoff_date)
        out["relationships"] = filtered_rels

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
