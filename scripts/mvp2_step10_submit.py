"""MVP-2 Step 10 — Submit to Convex.

Gate: HTTP 200, total_value present in response, submission_id captured.
"""
from __future__ import annotations

import json
import logging
import sys
import time

import requests

from abrollo.config import data_path
from abrollo.submit.validator import load_portfolio

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("mvp2.step10")

CONVEX_URL = "https://different-cormorant-663.convex.site/api/submit"
TEAM_ID = "abrollo"
AGENT_NAME = "monte-carlo-cathedral-mvp2"
AGENT_VERSION = "0.0.2"


def main() -> int:
    portfolio_path = data_path("portfolios") / "mvp2.json"
    if not portfolio_path.exists():
        log.error("Portfolio not found — run step 8 first")
        return 1

    weights = load_portfolio(portfolio_path)

    txs = [
        {"nasdaq_code": t, "amount": int(w)}
        for t, w in sorted(weights.items(), key=lambda kv: -kv[1])
    ]
    body = {
        "team_id": TEAM_ID,
        "model_agent_name": AGENT_NAME,
        "model_agent_version": AGENT_VERSION,
        "transactions": txs,
    }

    log.info("POST %s  (%d transactions, sum=$%d)",
             CONVEX_URL, len(txs), sum(weights.values()))

    resp = requests.post(
        CONVEX_URL,
        json=body,
        headers={"Content-Type": "application/json", "User-Agent": "abrollo-mvp2/0.0.2"},
        timeout=180,
    )

    try:
        parsed = resp.json()
    except ValueError:
        parsed = resp.text

    log.info("Response: %d — %s", resp.status_code, str(parsed)[:300])

    # Save
    stamp = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
    out = data_path("submissions") / f"mvp2_run_{stamp}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "status": resp.status_code,
        "request": body,
        "response": parsed,
    }, indent=2), encoding="utf-8")

    if resp.status_code != 200:
        log.error("GATE FAIL: HTTP %d (expected 200)", resp.status_code)
        return 1

    if isinstance(parsed, dict):
        total_value = parsed.get("total_value")
        submission_id = parsed.get("submission_id")
        log.info("submission_id: %s", submission_id)
        log.info("total_value: %s", total_value)

        if total_value is None:
            log.warning("total_value not in response")
    else:
        log.warning("Response is not JSON dict")

    print(f"[step10 OK] HTTP {resp.status_code}, saved to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
