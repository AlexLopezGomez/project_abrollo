"""Convex submission endpoint client.

POST https://different-cormorant-663.convex.site/api/submit
Body shape (derived from IDEA.md; exact field names may need confirmation after
a dry-run call):
    {
        "team_id": "abrollo",
        "model_agent_name": "monte-carlo-cathedral-mvp",
        "model_agent_version": "0.0.1",
        "transactions": [
            {"ticker": "NVDA", "amount_usd": 20000},
            ...
        ]
    }
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Any

import requests

from abrollo.config import data_path

log = logging.getLogger(__name__)

CONVEX_URL = "https://different-cormorant-663.convex.site/api/submit"
TEAM_ID = "abrollo"
AGENT_NAME = "terra"
AGENT_VERSION = "0.0.1"


@dataclass
class SubmitResult:
    status: int
    body: Any
    request: dict[str, Any]


def build_body(weights: dict[str, int]) -> dict[str, Any]:
    txs = [
        {"nasdaq_code": t, "amount": int(w)}
        for t, w in sorted(weights.items(), key=lambda kv: -kv[1])
    ]
    return {
        "team_id": TEAM_ID,
        "model_agent_name": AGENT_NAME,
        "model_agent_version": AGENT_VERSION,
        "transactions": txs,
    }


def submit(weights: dict[str, int], *, timeout: float = 60.0) -> SubmitResult:
    body = build_body(weights)
    log.info("POST %s  (%d transactions, sum=$%s)",
             CONVEX_URL, len(body["transactions"]), sum(weights.values()))
    resp = requests.post(
        CONVEX_URL,
        json=body,
        headers={"Content-Type": "application/json",
                 "User-Agent": "abrollo-mvp/0.0.1"},
        timeout=timeout,
    )
    try:
        parsed = resp.json()
    except ValueError:
        parsed = resp.text
    result = SubmitResult(status=resp.status_code, body=parsed, request=body)

    stamp = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
    out = data_path("submissions", f"mvp_run_{stamp}.json")
    out.write_text(
        json.dumps(
            {"status": result.status, "request": result.request, "response": result.body},
            indent=2,
        ),
        encoding="utf-8",
    )
    log.info("Saved %s", out)
    return result
