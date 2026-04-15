"""Hypothesis schema + validator.

Matches the shape in IDEA.md with MVP-scoped constraints:
  - id          : free-form string, e.g. "H_0247"
  - trigger     : natural-language description of a world event
  - trigger_probability  : 0.05 ≤ p ≤ 0.95  (sanity-bounded per IDEA Confusion #3)
  - effect_target : NASDAQ ticker symbol (must exist in our NDX universe)
  - effect_magnitude : return delta, bounded to [-1.0, 1.0]
  - effect_type : free-text slug (e.g. "gross_margin_delta", "revenue_delta")
  - sources     : list of Cala-native UUIDs (entities or context IDs)
  - source_dates: ISO-8601 YYYY-MM-DD strings, ALL ≤ cutoff_date
"""
from __future__ import annotations

import re
from datetime import date
from typing import Any

from pydantic import BaseModel, Field, field_validator

ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


class Hypothesis(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    trigger: str = Field(min_length=10, max_length=400)
    trigger_probability: float = Field(ge=0.05, le=0.95)
    effect_target: str = Field(min_length=1, max_length=8)
    effect_magnitude: float = Field(ge=-1.0, le=1.0)
    effect_type: str = Field(min_length=1, max_length=64)
    sources: list[str] = Field(min_length=1, max_length=10)
    source_dates: list[str] = Field(min_length=1, max_length=10)

    @field_validator("effect_target")
    @classmethod
    def ticker_upper(cls, v: str) -> str:
        return v.upper().strip()

    @field_validator("source_dates")
    @classmethod
    def all_iso(cls, v: list[str]) -> list[str]:
        for d in v:
            if not ISO_DATE_RE.match(d):
                raise ValueError(f"source_dates entry not YYYY-MM-DD: {d!r}")
            date.fromisoformat(d)  # parse or raise
        return v

    @field_validator("sources")
    @classmethod
    def all_uuid(cls, v: list[str]) -> list[str]:
        for s in v:
            if not UUID_RE.match(s):
                raise ValueError(f"source not a UUID: {s!r}")
        return v


def validate_hypothesis(
    raw: dict[str, Any],
    *,
    valid_uuids: set[str],
    ticker_universe: set[str],
    cutoff: date,
) -> tuple[Hypothesis | None, list[str]]:
    """Validate one hypothesis dict. Returns (hypothesis|None, reasons)."""
    reasons: list[str] = []
    try:
        h = Hypothesis.model_validate(raw)
    except Exception as e:
        return None, [f"schema: {e}"]

    if h.effect_target not in ticker_universe:
        reasons.append(f"effect_target {h.effect_target} not in NDX universe")

    unknown = [s for s in h.sources if s not in valid_uuids]
    if unknown:
        reasons.append(f"unknown source UUIDs: {unknown}")

    for d in h.source_dates:
        if date.fromisoformat(d) > cutoff:
            reasons.append(f"source_date {d} > cutoff {cutoff}")

    if reasons:
        return None, reasons
    return h, []
