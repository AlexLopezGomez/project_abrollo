"""MVP-2 Step 5 — HypothesisV2 schema + Sonnet 4.6 forced tool-use.

Key change vs MVP-1: hypothesis names an origin_entity_uuid (not a target
ticker). Fan-out to tickers is computed by BFS on the relationship graph
(Step 6). source_dates must appear VERBATIM in the allow-list.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import date
from typing import Any

import anthropic
from pydantic import BaseModel, Field, field_validator

from abrollo.config import ANTHROPIC_MODEL, CUTOFF_DATE, require_anthropic_key

log = logging.getLogger(__name__)

ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


class HypothesisV2(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    trigger: str = Field(min_length=10, max_length=200)
    origin_entity_uuid: str
    probability: float = Field(ge=0.0, le=1.0)
    magnitude: float = Field(ge=-0.5, le=0.5)
    horizon_days: int = Field(ge=1, le=365)
    sources: list[str] = Field(min_length=1, max_length=10)
    source_dates: list[str] = Field(min_length=1, max_length=10)

    @field_validator("source_dates")
    @classmethod
    def all_iso(cls, v: list[str]) -> list[str]:
        for d in v:
            if not ISO_DATE_RE.match(d):
                raise ValueError(f"source_dates entry not YYYY-MM-DD: {d!r}")
            date.fromisoformat(d)
        return v

    @field_validator("sources")
    @classmethod
    def all_uuid(cls, v: list[str]) -> list[str]:
        for s in v:
            if not UUID_RE.match(s):
                raise ValueError(f"source not a UUID: {s!r}")
        return v


def validate_hypothesis_v2(
    raw: dict[str, Any],
    *,
    allowed_origin_uuids: set[str],
    allowed_dates: set[str],
    cutoff: date,
) -> tuple[HypothesisV2 | None, list[str]]:
    """Validate one v2 hypothesis. Returns (hypothesis|None, reasons)."""
    reasons: list[str] = []
    try:
        h = HypothesisV2.model_validate(raw)
    except Exception as e:
        return None, [f"schema: {e}"]

    if h.origin_entity_uuid not in allowed_origin_uuids:
        reasons.append(f"origin_entity_uuid {h.origin_entity_uuid} not in allow-list")

    for d in h.source_dates:
        if d not in allowed_dates:
            reasons.append(f"source_date {d} not in allow-list (verbatim match required)")
        if date.fromisoformat(d) > cutoff:
            reasons.append(f"source_date {d} > cutoff {cutoff}")

    if reasons:
        return None, reasons
    return h, []


TOOL_SCHEMA = {
    "name": "emit_hypotheses",
    "description": "Emit exactly 10 investment hypotheses based on Cala entity data. Each hypothesis names an origin entity UUID and a magnitude of expected return shock.",
    "input_schema": {
        "type": "object",
        "required": ["hypotheses"],
        "properties": {
            "hypotheses": {
                "type": "array",
                "minItems": 10,
                "maxItems": 10,
                "items": {
                    "type": "object",
                    "required": ["id", "trigger", "origin_entity_uuid", "probability",
                                 "magnitude", "horizon_days", "sources", "source_dates"],
                    "properties": {
                        "id": {"type": "string", "description": "Unique ID like H_V2_01"},
                        "trigger": {"type": "string", "maxLength": 200,
                                    "description": "Natural-language event description. No dates after 2025-04-15."},
                        "origin_entity_uuid": {"type": "string",
                                                "description": "UUID of the origin entity. MUST be from the allowed_origins list."},
                        "probability": {"type": "number", "minimum": 0, "maximum": 1,
                                        "description": "Probability this event occurs in the horizon."},
                        "magnitude": {"type": "number", "minimum": -0.5, "maximum": 0.5,
                                      "description": "Expected return shock at the origin entity."},
                        "horizon_days": {"type": "integer", "minimum": 1, "maximum": 365},
                        "sources": {"type": "array", "items": {"type": "string"},
                                    "description": "Cala entity UUIDs used as evidence."},
                        "source_dates": {"type": "array", "items": {"type": "string"},
                                         "description": "ISO dates from Cala. MUST be copied VERBATIM from allowed_dates."},
                    },
                },
            },
        },
    },
}


def build_system_prompt(
    origin_entries: list[dict[str, str]],
    allowed_dates: list[str],
    exclude_origins: set[str] | None = None,
) -> str:
    """Build system prompt with allow-lists.

    Args:
        exclude_origins: UUIDs to filter out of the ALLOWED ORIGINS block
            (used in round 2+ so the LLM picks different entities).
    """
    filtered = origin_entries
    if exclude_origins:
        filtered = [e for e in origin_entries if e["uuid"] not in exclude_origins]
    origins_block = "\n".join(
        f"  - {e['uuid']}  ({e['name']})" for e in filtered[:50]
    )
    dates_block = json.dumps(sorted(allowed_dates)[:200])

    return f"""You are an investment analyst generating hypotheses about NASDAQ-100 companies.

HARD RULES:
1. Each hypothesis must name an origin_entity_uuid from the allowed_origins list below.
2. All 10 hypotheses must have DISTINCT origin_entity_uuid values.
3. Every source_dates value must be COPIED VERBATIM from the allowed_dates list below. Do NOT invent dates.
4. No trigger text may reference events after 2025-04-15.
5. Magnitudes in [-0.5, 0.5]: positive = bullish, negative = bearish.
6. Probabilities in [0, 1]: your genuine belief.

ALLOWED ORIGINS (top entities by graph connectivity — use these UUIDs exactly):
{origins_block}

ALLOWED DATES (copy-paste only — any date not in this list will be rejected):
{dates_block}

Generate 10 diverse hypotheses covering different sectors and risk factors.
Focus on macro events, regulatory changes, supply chain disruptions, and competitive dynamics.
Each hypothesis should identify a causal chain from the origin entity to affected companies."""


def _call_single_round(
    client: anthropic.Anthropic,
    origin_entries: list[dict[str, str]],
    allowed_dates: list[str],
    allowed_origin_uuids: set[str],
    cutoff: date,
    allowed_dates_set: set[str],
    exclude_origins: set[str] | None = None,
    max_retries: int = 2,
) -> list[HypothesisV2]:
    """Run a single round of 10 hypotheses with its own retries."""
    system = build_system_prompt(origin_entries, allowed_dates, exclude_origins=exclude_origins)

    for attempt in range(max_retries + 1):
        log.info("Sonnet call attempt %d/%d", attempt + 1, max_retries + 1)

        resp = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=4096,
            system=system,
            messages=[{
                "role": "user",
                "content": "Generate 10 investment hypotheses using the emit_hypotheses tool. "
                           "Remember: origin_entity_uuid must be from allowed_origins, "
                           "source_dates must be VERBATIM from allowed_dates.",
            }],
            tools=[TOOL_SCHEMA],
            tool_choice={"type": "tool", "name": "emit_hypotheses"},
        )

        log.info("Sonnet response: %d input tokens, %d output tokens",
                 resp.usage.input_tokens, resp.usage.output_tokens)

        tool_block = None
        for block in resp.content:
            if block.type == "tool_use" and block.name == "emit_hypotheses":
                tool_block = block
                break

        if not tool_block:
            log.error("No tool_use block in response")
            continue

        raw_hypotheses = tool_block.input.get("hypotheses", [])
        validated: list[HypothesisV2] = []
        all_reasons: list[str] = []

        for raw in raw_hypotheses:
            h, reasons = validate_hypothesis_v2(
                raw,
                allowed_origin_uuids=allowed_origin_uuids,
                allowed_dates=allowed_dates_set,
                cutoff=cutoff,
            )
            if h:
                validated.append(h)
            else:
                all_reasons.extend(reasons)

        log.info("Round validated %d / %d hypotheses", len(validated), len(raw_hypotheses))
        if all_reasons:
            log.warning("Validation issues: %s", all_reasons[:10])

        if len(validated) >= 8:
            return validated

        log.warning("Only %d valid hypotheses — retrying round", len(validated))

    raise RuntimeError(f"Failed to get >= 8 valid hypotheses in round after {max_retries + 1} attempts")


def call_sonnet_hypotheses(
    origin_entries: list[dict[str, str]],
    allowed_dates: list[str],
    allowed_origin_uuids: set[str],
    cutoff_date: str = CUTOFF_DATE,
    max_retries: int = 2,
    n_rounds: int = 2,
) -> list[HypothesisV2]:
    """Call Sonnet 4.6 with forced tool-use to emit hypotheses across multiple rounds.

    Each round generates 10 hypotheses. Round 2+ excludes origin UUIDs already
    used by validated hypotheses from previous rounds, forcing diversity.
    """
    client = anthropic.Anthropic(api_key=require_anthropic_key())
    cutoff = date.fromisoformat(cutoff_date)
    allowed_dates_set = set(allowed_dates)

    all_validated: list[HypothesisV2] = []

    for rnd in range(n_rounds):
        exclude_origins: set[str] | None = None
        if rnd > 0:
            exclude_origins = {h.origin_entity_uuid for h in all_validated}
            log.info("Round %d: excluding %d origins from previous rounds", rnd + 1, len(exclude_origins))

        round_hyps = _call_single_round(
            client=client,
            origin_entries=origin_entries,
            allowed_dates=allowed_dates,
            allowed_origin_uuids=allowed_origin_uuids,
            cutoff=cutoff,
            allowed_dates_set=allowed_dates_set,
            exclude_origins=exclude_origins,
            max_retries=max_retries,
        )
        all_validated.extend(round_hyps)
        log.info("After round %d: %d total validated hypotheses", rnd + 1, len(all_validated))

    min_required = 8 * n_rounds
    if len(all_validated) < min_required:
        raise RuntimeError(
            f"Only {len(all_validated)} valid hypotheses across {n_rounds} rounds "
            f"(need >= {min_required})"
        )

    return all_validated
