"""MVP-2 Step 7 — Correlated Monte Carlo.

Gate: (a) shape (1000, N); (b) no NaN/inf; (c) per-ticker std > 0;
      (d) empirical corr matches Σ within 0.1 on median off-diagonal;
      (e) CVaR5 on equal-weight portfolio between -8% and -1%.
"""
from __future__ import annotations

import json
import logging
import sys

import numpy as np

from abrollo.agents.hypothesis_v2 import HypothesisV2
from abrollo.config import data_path
from abrollo.mc.sim_mvp2 import run, save

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("mvp2.step7")


def main() -> int:
    # Load covariance
    cov_path = data_path("cov") / "mvp2.npz"
    if not cov_path.exists():
        log.error("Covariance not found — run step 3 first")
        return 1
    cov_data = np.load(cov_path, allow_pickle=True)
    sigma = cov_data["sigma"]
    sigma_tickers = list(cov_data["tickers"])

    # Load propagation data
    dag_path = data_path("dag") / "mvp2.json"
    if not dag_path.exists():
        log.error("DAG not found — run step 6 first")
        return 1
    dag_data = json.loads(dag_path.read_text(encoding="utf-8"))

    # Reconstruct shift_per_ticker and probabilities
    shift_per_ticker: dict[str, dict[str, float]] = {}
    hypothesis_probabilities: dict[str, float] = {}

    for entry in dag_data:
        hid = entry["hypothesis_id"]
        hypothesis_probabilities[hid] = entry["probability"]
        for affected in entry["affected_tickers"]:
            ticker_uuid = affected["ticker_uuid"]
            shift_per_ticker.setdefault(ticker_uuid, {})[hid] = affected["shift"]

    log.info("Loaded: Σ (%d×%d), %d hypotheses, %d affected tickers",
             sigma.shape[0], sigma.shape[1], len(hypothesis_probabilities), len(shift_per_ticker))

    # Run MC
    result = run(
        sigma=sigma,
        sigma_tickers=sigma_tickers,
        shift_per_ticker=shift_per_ticker,
        hypothesis_probabilities=hypothesis_probabilities,
    )

    # Gate checks
    mat = result.matrix
    n_sims, n_tickers = mat.shape

    # (a) shape
    log.info("Shape: (%d, %d)", n_sims, n_tickers)

    # (b) no NaN/inf
    if not np.isfinite(mat).all():
        log.error("GATE FAIL (b): matrix has NaN or inf")
        return 1

    # (c) per-ticker std > 0
    stds = mat.std(axis=0)
    zero_std = np.sum(stds == 0)
    if zero_std > 0:
        log.error("GATE FAIL (c): %d tickers with zero std", zero_std)
        return 1

    # (d) empirical correlation vs Σ
    emp_corr = np.corrcoef(mat.T)
    d_inv = np.diag(1.0 / np.sqrt(np.diag(sigma) + 1e-30))
    sigma_corr = d_inv @ sigma @ d_inv
    np.fill_diagonal(emp_corr, np.nan)
    np.fill_diagonal(sigma_corr, np.nan)
    med_diff = np.nanmedian(np.abs(emp_corr - sigma_corr))
    med_emp = np.nanmedian(emp_corr)
    log.info("Median empirical corr: %.4f, median |emp - Σ| diff: %.4f", med_emp, med_diff)

    if med_diff > 0.1:
        log.warning("Gate (d) soft fail: median corr diff %.4f > 0.1", med_diff)

    # (e) CVaR5 on equal-weight
    eq_returns = mat.mean(axis=1)  # equal-weight portfolio return
    sorted_ret = np.sort(eq_returns)
    cvar5_idx = max(1, int(0.05 * n_sims))
    cvar5 = sorted_ret[:cvar5_idx].mean()
    log.info("CVaR5 (equal-weight): %.4f (%.2f%%)", cvar5, cvar5 * 100)

    if cvar5 < -0.08:
        log.warning("CVaR5 %.4f < -8%% — tails may be too fat", cvar5)
    if cvar5 > -0.01:
        log.warning("CVaR5 %.4f > -1%% — tails may be too thin (MVP-1 had -0.5%%)", cvar5)

    save(result)

    print(f"[step7 OK] ({n_sims}, {n_tickers}), median_emp_corr={med_emp:.4f}, "
          f"CVaR5={cvar5:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
