"""MVP-2 Step 8 — CVaR optimizer with CLARABEL.

Gate: (a) solver status is 'optimal'; (b) >=50 non-zero tickers;
      (c) each >= $5,000; (d) sum = $1,000,000; (e) >= 5 DAG-affected
      tickers have non-zero weight.
"""
from __future__ import annotations

import json
import logging
import sys

import pandas as pd

from abrollo.config import data_path
from abrollo.opt.cvar import optimize, save

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("mvp2.step8")


def main() -> int:
    # Load scenarios
    parquet_path = data_path("scenarios") / "mvp2.parquet"
    if not parquet_path.exists():
        log.error("Scenarios not found — run step 7 first")
        return 1
    returns_df = pd.read_parquet(parquet_path)
    log.info("Loaded scenarios: %s", returns_df.shape)

    # Scenario columns are entity UUIDs. Map to tickers for the optimizer.
    entities_dir = data_path("cala_entities")
    uuid_to_ticker: dict[str, str] = {}
    for fpath in entities_dir.glob("*.json"):
        if fpath.name.startswith("_"):
            continue
        try:
            e = json.loads(fpath.read_text(encoding="utf-8"))
            uuid_to_ticker[e.get("id", "")] = fpath.stem
        except Exception:
            continue

    col_map = {col: uuid_to_ticker.get(col, col) for col in returns_df.columns}
    returns_df = returns_df.rename(columns=col_map)

    # Deduplicate columns (GOOGL/GOOG share a UUID → same ticker after mapping)
    returns_df = returns_df.loc[:, ~returns_df.columns.duplicated()]
    log.info("Scenarios after dedup: %s", returns_df.shape)

    # Load DAG-affected tickers
    dag_path = data_path("dag") / "mvp2.json"
    dag_affected: set[str] = set()
    if dag_path.exists():
        dag_data = json.loads(dag_path.read_text(encoding="utf-8"))
        for entry in dag_data:
            for at in entry["affected_tickers"]:
                t = at.get("ticker", "")
                if t:
                    dag_affected.add(t)

    # Optimize
    outcome = optimize(returns_df)
    log.info("Solver: %s, status: %s", outcome.solver, outcome.status)
    log.info("E[r]: %.4f, CVaR5: %.4f", outcome.expected_return_pct, outcome.cvar5_pct)
    log.info("Non-zero tickers: %d", outcome.n_nonzero)

    if "optimal" not in outcome.status:
        log.warning("Gate (a): solver status is %r (not optimal)", outcome.status)

    if outcome.n_nonzero < 50:
        log.error("GATE FAIL (b): only %d non-zero tickers", outcome.n_nonzero)
        return 1

    total = sum(outcome.weights.values())
    log.info("Total: $%d", total)

    dag_in_portfolio = [t for t in outcome.weights if t in dag_affected and outcome.weights[t] > 0]
    log.info("DAG-affected tickers in portfolio: %d / %d total DAG-affected",
             len(dag_in_portfolio), len(dag_affected))

    if len(dag_in_portfolio) < 5:
        log.warning("Gate (e): only %d DAG-affected tickers in portfolio", len(dag_in_portfolio))

    save(outcome, "mvp2")

    print(f"[step8 OK] {outcome.n_nonzero} tickers, solver={outcome.solver}/{outcome.status}, "
          f"E[r]={outcome.expected_return_pct:.4f}, CVaR5={outcome.cvar5_pct:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
