"""Semiconductor-domain hypothesis agent.

Gathers Cala context for the 5 anchor tickers + peer set, then asks Sonnet 4.6
(tool-use, forced choice) for exactly 10 causal hypotheses in the IDEA.md schema.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from anthropic import Anthropic

from abrollo.agents.hypothesis import Hypothesis, validate_hypothesis
from abrollo.cala.client import CalaClient
from abrollo.cala.cutoff import filter_entity_by_cutoff
from abrollo.cala.ndx import load_resolutions
from abrollo.config import (
    ANTHROPIC_MODEL,
    CUTOFF_DATE,
    SEMI_ANCHOR_TICKERS,
    data_path,
    require_anthropic_key,
)

log = logging.getLogger(__name__)

# NDX tickers that plausibly belong to the semiconductor / semi-adjacent peer set.
SEMI_PEER_TICKERS: list[str] = [
    # Anchors
    "NVDA", "AMD", "INTC", "QCOM", "AVGO",
    # Additional chip makers
    "MU", "MCHP", "MPWR", "MRVL", "ADI", "TXN", "NXPI", "ARM",
    # Chip equipment
    "AMAT", "ASML", "KLAC", "LRCX",
    # EDA software
    "CDNS", "SNPS",
    # Storage
    "WDC", "STX",
]

KNOWLEDGE_QUERY = (
    "what are the key supply-chain, geopolitical, and demand risks for NASDAQ "
    "semiconductor names in 2025?"
)

SYSTEM_PROMPT = """You are a quantitative-finance research analyst emitting STRUCTURED CAUSAL HYPOTHESES about semiconductor-sector NASDAQ stocks.

You produce ONLY structured hypotheses via the `emit_hypotheses` tool. Do not write prose.

Constraints (HARD):
1. Every hypothesis must cite at least one Cala UUID from the allow-list provided in the user message.
   A UUID not on the allow-list is a HALLUCINATION and invalidates the hypothesis.
2. Every source_date MUST be <= {cutoff}. You are operating under a strict no-lookahead rule:
   pretend it is {cutoff} and no later information exists. Prefer dates drawn from the
   "known_dates" list provided per UUID; if you must invent a plausible date for a context UUID,
   pick one in [2024-01-01, {cutoff}].
3. trigger_probability must be in [0.05, 0.95] (sanity bounds).
4. effect_target must be one of the NDX tickers in the provided universe list.
5. effect_magnitude is a return delta in approx [-0.5, +0.5] (hard bounds [-1, +1]).
6. Return EXACTLY 10 hypotheses. No more, no less.
7. Hypotheses should span DIFFERENT triggers (don't emit 10 variants of "TSMC outage").
8. Each hypothesis id should be unique, format like "H_SEMI_01" through "H_SEMI_10".
"""


@dataclass
class AgentInputs:
    tickers: dict[str, str]  # ticker -> uuid (full NDX)
    semi_peers: dict[str, dict[str, Any]]  # ticker -> {uuid, match_name}
    anchor_profiles: dict[str, dict[str, Any]]  # ticker -> cutoff-filtered profile
    knowledge_search: dict[str, Any]  # filtered narrative + context + entities
    # valid_uuids and known_dates derived below
    valid_uuids: set[str] = field(default_factory=set)
    known_dates: dict[str, list[str]] = field(default_factory=dict)


def collect_inputs(client: CalaClient) -> AgentInputs:
    res = load_resolutions()
    all_hits = {h["ticker"]: h for h in res["hits"]}
    tickers = {t: h["uuid"] for t, h in all_hits.items()}

    semi_peers: dict[str, dict[str, Any]] = {}
    for t in SEMI_PEER_TICKERS:
        h = all_hits.get(t)
        if h:
            semi_peers[t] = {"uuid": h["uuid"], "match_name": h["match_name"]}
        else:
            log.warning("Semi peer %s missing from resolutions — skipping", t)

    log.info("Loading 5 anchor profiles from cache and cutoff-filtering")
    anchor_profiles: dict[str, dict[str, Any]] = {}
    for t in SEMI_ANCHOR_TICKERS:
        raw = json.loads(data_path("semi_profiles", f"{t}.json").read_text(encoding="utf-8"))
        anchor_profiles[t] = filter_entity_by_cutoff(raw)

    log.info("Calling knowledge_search for semi risks narrative")
    ks_raw = client.knowledge_search(KNOWLEDGE_QUERY)
    # context lacks `date`, so we do NOT filter it; see Step 6 notes in retro.

    # Build allow-list of UUIDs the agent may cite.
    valid_uuids: set[str] = set()
    valid_uuids.update(h["uuid"] for h in all_hits.values())
    for t, prof in anchor_profiles.items():
        if "id" in prof:
            valid_uuids.add(prof["id"])
    for item in (ks_raw.get("context") or []):
        if isinstance(item, dict) and item.get("id"):
            valid_uuids.add(item["id"])
    for item in (ks_raw.get("entities") or []):
        if isinstance(item, dict) and item.get("id"):
            valid_uuids.add(item["id"])
    for expl in (ks_raw.get("explainability") or []):
        for ref in (expl.get("references") or []):
            valid_uuids.add(ref)

    # Build known_dates: for anchor company UUIDs, collect pre-cutoff source dates.
    known_dates: dict[str, list[str]] = {}
    for t, prof in anchor_profiles.items():
        entity_uuid = prof.get("id")
        if not entity_uuid:
            continue
        dates: set[str] = set()
        for pbody in (prof.get("properties") or {}).values():
            for s in (pbody.get("sources") or []):
                d = s.get("date")
                if d:
                    dates.add(d[:10])
        if dates:
            known_dates[entity_uuid] = sorted(dates)

    log.info(
        "Inputs: %d NDX tickers, %d semi peers, %d anchor profiles, %d valid UUIDs",
        len(tickers), len(semi_peers), len(anchor_profiles), len(valid_uuids),
    )
    return AgentInputs(
        tickers=tickers,
        semi_peers=semi_peers,
        anchor_profiles=anchor_profiles,
        knowledge_search=ks_raw,
        valid_uuids=valid_uuids,
        known_dates=known_dates,
    )


def _format_user_message(inp: AgentInputs) -> str:
    lines: list[str] = []
    lines.append(f"# Cutoff date (no data after this): {CUTOFF_DATE}")
    lines.append("")
    lines.append("## NDX ticker universe (effect_target must be one of these)")
    lines.append(", ".join(sorted(inp.tickers.keys())))
    lines.append("")
    lines.append("## Semiconductor peer set (ticker -> Cala entity UUID)")
    for t in sorted(inp.semi_peers.keys()):
        lines.append(f"- {t:6s} {inp.semi_peers[t]['uuid']}  ({inp.semi_peers[t]['match_name']})")
    lines.append("")
    lines.append("## Anchor company profiles (cutoff-filtered)")
    for t, prof in inp.anchor_profiles.items():
        uid = prof.get("id", "?")
        name = prof.get("name", "?")
        props = list((prof.get("properties") or {}).keys())
        kd = inp.known_dates.get(uid, [])
        lines.append(f"### {t} — {name} — uuid={uid}")
        lines.append(f"  surviving properties: {props}")
        lines.append(f"  known pre-cutoff source dates for this UUID: {kd}")
    lines.append("")
    ks = inp.knowledge_search
    lines.append("## Narrative context from Cala `knowledge_search`")
    lines.append("")
    content = (ks.get("content") or "").strip()
    if len(content) > 6000:
        content = content[:6000] + "\n...[truncated]"
    lines.append(content)
    lines.append("")
    lines.append("## knowledge_search entities (id -> name/type) — citable UUIDs")
    for e in (ks.get("entities") or [])[:40]:
        lines.append(f"- {e.get('id')}  {e.get('name')} ({e.get('entity_type')})")
    lines.append("")
    lines.append("## knowledge_search explainability claims (content + reference UUIDs)")
    for i, expl in enumerate((ks.get("explainability") or [])[:20], 1):
        refs = expl.get("references") or []
        txt = (expl.get("content") or "").strip()
        lines.append(f"{i}. refs={refs}")
        lines.append(f"   claim: {txt[:240]}")
    lines.append("")
    lines.append("Emit EXACTLY 10 hypotheses via the emit_hypotheses tool.")
    return "\n".join(lines)


_TOOL_SCHEMA = {
    "name": "emit_hypotheses",
    "description": "Emit exactly 10 structured causal hypotheses about NASDAQ semiconductor names.",
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
                    "required": [
                        "id",
                        "trigger",
                        "trigger_probability",
                        "effect_target",
                        "effect_magnitude",
                        "effect_type",
                        "sources",
                        "source_dates",
                    ],
                    "properties": {
                        "id": {"type": "string"},
                        "trigger": {"type": "string"},
                        "trigger_probability": {"type": "number", "minimum": 0.05, "maximum": 0.95},
                        "effect_target": {"type": "string"},
                        "effect_magnitude": {"type": "number", "minimum": -1.0, "maximum": 1.0},
                        "effect_type": {"type": "string"},
                        "sources": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 1,
                        },
                        "source_dates": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 1,
                        },
                    },
                },
            }
        },
    },
}


def call_llm(inp: AgentInputs) -> list[dict[str, Any]]:
    client = Anthropic(api_key=require_anthropic_key())
    system = SYSTEM_PROMPT.format(cutoff=CUTOFF_DATE)
    user_msg = _format_user_message(inp)
    log.info("Calling %s with %d-char user message", ANTHROPIC_MODEL, len(user_msg))
    resp = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=8000,
        system=system,
        tools=[_TOOL_SCHEMA],
        tool_choice={"type": "tool", "name": "emit_hypotheses"},
        messages=[{"role": "user", "content": user_msg}],
    )
    log.info(
        "Anthropic usage: input=%d output=%d",
        resp.usage.input_tokens,
        resp.usage.output_tokens,
    )
    for block in resp.content:
        if getattr(block, "type", None) == "tool_use" and block.name == "emit_hypotheses":
            return list(block.input.get("hypotheses") or [])
    raise RuntimeError("LLM did not return emit_hypotheses tool call")


def run() -> dict[str, Any]:
    cala = CalaClient()
    inputs = collect_inputs(cala)
    raw_list = call_llm(inputs)
    log.info("LLM emitted %d raw hypotheses", len(raw_list))

    cutoff = date.fromisoformat(CUTOFF_DATE)
    ticker_set = set(inputs.tickers.keys())
    valid: list[Hypothesis] = []
    rejects: list[dict[str, Any]] = []
    for raw in raw_list:
        h, reasons = validate_hypothesis(
            raw,
            valid_uuids=inputs.valid_uuids,
            ticker_universe=ticker_set,
            cutoff=cutoff,
        )
        if h:
            valid.append(h)
        else:
            rejects.append({"raw": raw, "reasons": reasons})

    log.info("Validated %d / %d hypotheses", len(valid), len(raw_list))
    for r in rejects:
        log.warning("REJECTED %s: %s", r["raw"].get("id"), r["reasons"])

    payload = {
        "cutoff_date": CUTOFF_DATE,
        "raw_count": len(raw_list),
        "valid_count": len(valid),
        "reject_count": len(rejects),
        "hypotheses": [h.model_dump() for h in valid],
        "rejects": rejects,
    }
    out = data_path("hypotheses", "semi.json")
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    log.info("Saved %s", out)
    return payload
