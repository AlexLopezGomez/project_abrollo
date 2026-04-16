"""MVP-2 Step 7 — Correlated Monte Carlo with MVN(μ_scenario, Σ).

Each scenario:
  1. Sample Bernoulli for each hypothesis (fire / not fire).
  2. Compute μ_scenario = μ_base + sum of active hypothesis shifts.
  3. Draw r ~ MVN(μ_scenario, Σ).

Output: (N_sim, n_tickers) matrix of return scenarios.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from abrollo.config import data_path

log = logging.getLogger(__name__)

N_SIMS = 5000
MU_BASE_DEFAULT = 0.0  # zero drift — let hypotheses drive signal


@dataclass
class MCResultV2:
    tickers: list[str]
    matrix: np.ndarray  # (N_SIMS, n_tickers)
    hypothesis_ids: list[str]
    n_sims: int
    sigma_source: str


def run(
    sigma: np.ndarray,
    sigma_tickers: list[str],
    shift_per_ticker: dict[str, dict[str, float]],
    hypothesis_probabilities: dict[str, float],
    n_sims: int = N_SIMS,
    mu_base: float = MU_BASE_DEFAULT,
    seed: int = 42,
) -> MCResultV2:
    """Run correlated Monte Carlo.

    Args:
        sigma: (n, n) covariance matrix.
        sigma_tickers: ticker list matching sigma rows/cols.
        shift_per_ticker: {ticker_uuid: {hyp_id: shift_value}}.
        hypothesis_probabilities: {hyp_id: probability}.
        n_sims: number of scenarios.
        mu_base: baseline drift per ticker.
        seed: RNG seed.
    """
    rng = np.random.default_rng(seed)
    n = len(sigma_tickers)
    hypothesis_ids = sorted(hypothesis_probabilities.keys())

    # Map ticker → index
    ticker_idx = {t: i for i, t in enumerate(sigma_tickers)}

    # Pre-compute per-hypothesis shift vectors
    hyp_shift_vectors: dict[str, np.ndarray] = {}
    for hid in hypothesis_ids:
        vec = np.zeros(n)
        for ticker_uuid, shifts in shift_per_ticker.items():
            if hid in shifts and ticker_uuid in ticker_idx:
                vec[ticker_idx[ticker_uuid]] = shifts[hid]
        hyp_shift_vectors[hid] = vec

    # Pre-compute Bernoulli probabilities
    probs = np.array([hypothesis_probabilities[hid] for hid in hypothesis_ids])

    scenarios = np.empty((n_sims, n), dtype=np.float64)

    for s in range(n_sims):
        # Sample hypothesis activations
        h_states = rng.random(len(hypothesis_ids)) < probs

        # Build scenario mean
        mu = np.full(n, mu_base)
        for j, (hid, active) in enumerate(zip(hypothesis_ids, h_states)):
            if active:
                mu += hyp_shift_vectors[hid]

        # Draw from MVN
        scenarios[s] = rng.multivariate_normal(mean=mu, cov=sigma, check_valid="raise")

    log.info("MC: %d scenarios × %d tickers", n_sims, n)
    return MCResultV2(
        tickers=sigma_tickers,
        matrix=scenarios,
        hypothesis_ids=hypothesis_ids,
        n_sims=n_sims,
        sigma_source="mvp2",
    )


def save(result: MCResultV2) -> Path:
    """Save scenarios to parquet + metadata JSON."""
    out_dir = data_path("scenarios")
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame(result.matrix, columns=result.tickers)
    parquet_path = out_dir / "mvp2.parquet"
    df.to_parquet(parquet_path)

    meta: dict[str, Any] = {
        "n_sims": result.n_sims,
        "n_tickers": len(result.tickers),
        "tickers": result.tickers,
        "hypothesis_ids": result.hypothesis_ids,
        "sigma_source": result.sigma_source,
    }
    meta_path = out_dir / "mvp2_meta.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    log.info("Saved scenarios (%d × %d) to %s", result.n_sims, len(result.tickers), parquet_path)
    return parquet_path
