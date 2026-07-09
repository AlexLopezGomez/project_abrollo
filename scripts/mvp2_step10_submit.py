"""MVP-2 Step 10 — Submit to Convex.

Gate: HTTP 200, total_value present in response, submission_id captured.
"""
from __future__ import annotations

import json
import logging
import shutil
import sys
import time
from pathlib import Path

import requests

from abrollo.config import data_path
from abrollo.submit.validator import load_portfolio

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("mvp2.step10")

CONVEX_URL = "https://different-cormorant-663.convex.site/api/submit"
TEAM_ID = "abrollo"
AGENT_NAME = "monte-carlo-cathedral-mvp2"
AGENT_VERSION = "0.0.2"
SNAPSHOT_ARTIFACTS = {
    "hypotheses": ("hypotheses", "mvp2.json", "hypotheses.json"),
    "dag": ("dag", "mvp2.json", "dag.json"),
    "portfolio": ("portfolios", "mvp2.json", "portfolio.json"),
    "graph": ("graph", "mvp2.gpickle", "graph.gpickle"),
    "graph_summary": ("graph", "mvp2_summary.json", "graph_summary.json"),
}


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

    run_id = out.stem
    snapshot_dir = snapshot_run(run_id, out, body, parsed)
    log.info("Snapshot saved to %s", snapshot_dir)

    print(f"[step10 OK] HTTP {resp.status_code}, saved to {out}")
    return 0


def snapshot_run(run_id: str, submission_path: Path, request_body: dict, response_body: object) -> Path:
    """Freeze the run artifacts used by this accepted leaderboard submission."""
    run_dir = data_path("runs", run_id)
    run_dir.mkdir(parents=True, exist_ok=True)

    shutil.copy2(submission_path, run_dir / "submission.json")

    copied: dict[str, str] = {"submission": "submission.json"}
    missing: list[str] = []
    for key, (folder, source_name, dest_name) in SNAPSHOT_ARTIFACTS.items():
        source = data_path(folder, source_name)
        dest = run_dir / dest_name
        if source.exists():
            shutil.copy2(source, dest)
            copied[key] = dest_name
        else:
            missing.append(str(source))

    manifest = build_manifest(
        run_id=run_id,
        submission_path=submission_path,
        request_body=request_body,
        response_body=response_body,
        copied=copied,
        missing=missing,
    )
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return run_dir


def build_manifest(
    *,
    run_id: str,
    submission_path: Path,
    request_body: dict,
    response_body: object,
    copied: dict[str, str],
    missing: list[str],
) -> dict:
    response = response_body if isinstance(response_body, dict) else {}
    total_invested = response.get("total_invested")
    total_value = response.get("total_value")
    return_pct = None
    if total_invested and total_value is not None:
        return_pct = (float(total_value) / float(total_invested) - 1) * 100

    graph_summary = _read_json_if_exists(data_path("graph", "mvp2_summary.json"))
    hypotheses = _read_json_if_exists(data_path("hypotheses", "mvp2.json"))

    return {
        "run_id": run_id,
        "pipeline": "mvp2",
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "submission_file": str(submission_path),
        "submission_id": response.get("submission_id"),
        "status": 200 if response.get("success") is True else response.get("status"),
        "agent": request_body.get("model_agent_name"),
        "version": request_body.get("model_agent_version"),
        "total_invested": total_invested,
        "total_value": total_value,
        "return_pct": return_pct,
        "n_transactions": len(request_body.get("transactions") or []),
        "hypotheses_count": len(hypotheses) if isinstance(hypotheses, list) else None,
        "graph_nodes": graph_summary.get("nodes") if isinstance(graph_summary, dict) else None,
        "graph_edges": graph_summary.get("edges") if isinstance(graph_summary, dict) else None,
        "artifacts": copied,
        "missing_artifacts": missing,
    }


def _read_json_if_exists(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


if __name__ == "__main__":
    sys.exit(main())
