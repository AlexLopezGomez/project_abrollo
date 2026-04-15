"""Monte Carlo loop: 1000 iterations over the MVP DAG.

For each iteration i:
  1. Sample binary root states:
       TSMC_event ~ Bernoulli(0.12)
       export_control ~ Bernoulli(0.65)
  2. Sample discrete mechanism state:
       supply_delta ~ Categorical(CPT[TSMC_event, export_control])
  3. Sample discrete leaf states:
       NVDA_return_state ~ Categorical(CPT[supply_delta])
       AMD_return_state  ~ Categorical(CPT[supply_delta])
  4. Draw continuous returns:
       For DAG leaves: return ~ Normal(μ(state), σ=0.15)
       For non-DAG tickers: return ~ Normal(0.05, 0.20)

Output: (N_SIMS, N_TICKERS) numpy matrix, saved as parquet for Step 9.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd

from abrollo.cala.ndx import load_resolutions
from abrollo.config import data_path

log = logging.getLogger(__name__)

N_SIMS = 1000
DAG_LEAF_SIGMA = 0.15
NON_DAG_MU = 0.05
NON_DAG_SIGMA = 0.20

# CPT constants duplicated here to keep MC independent of pgmpy at runtime.
P_TSMC = 0.12
P_EC = 0.65

# supply_delta | TSMC, EC  — rows: [none, mild, severe]
# Columns in order (TSMC=F,EC=F) (F,T) (T,F) (T,T)
SUPPLY_CPT = np.array(
    [
        [0.85, 0.20, 0.05, 0.02],
        [0.12, 0.65, 0.35, 0.18],
        [0.03, 0.15, 0.60, 0.80],
    ]
)

# NVDA | supply — rows [up, flat, down]
NVDA_CPT = np.array(
    [
        [0.55, 0.25, 0.05],
        [0.35, 0.40, 0.20],
        [0.10, 0.35, 0.75],
    ]
)
AMD_CPT = np.array(
    [
        [0.50, 0.30, 0.10],
        [0.35, 0.40, 0.30],
        [0.15, 0.30, 0.60],
    ]
)

# State mean-return mapping (continuous μ given discrete state).
STATE_MU = {"up": 0.20, "flat": 0.00, "down": -0.25}
STATES_LEAF = ["up", "flat", "down"]


@dataclass
class MCResult:
    tickers: list[str]
    matrix: np.ndarray  # shape (N_SIMS, n_tickers)


def _sample_categorical(rng: np.random.Generator, probs: np.ndarray, n: int) -> np.ndarray:
    """Vectorized sampler: given a (k, n) prob matrix, sample n indices."""
    cum = np.cumsum(probs, axis=0)
    u = rng.random(n)
    return (u < cum).argmax(axis=0)


def run(n_sims: int = N_SIMS, seed: int = 42) -> MCResult:
    rng = np.random.default_rng(seed)

    tickers = sorted(h["ticker"] for h in load_resolutions()["hits"])
    n_tickers = len(tickers)
    log.info("MC: %d sims × %d tickers", n_sims, n_tickers)

    # Roots
    tsmc = rng.random(n_sims) < P_TSMC
    ec = rng.random(n_sims) < P_EC

    # Column index into SUPPLY_CPT for each iteration.
    # F,F=0  F,T=1  T,F=2  T,T=3
    supply_col = tsmc.astype(int) * 2 + ec.astype(int)
    supply_probs = SUPPLY_CPT[:, supply_col]  # (3, N_SIMS)
    supply_state = _sample_categorical(rng, supply_probs, n_sims)  # 0/1/2

    nvda_probs = NVDA_CPT[:, supply_state]
    amd_probs = AMD_CPT[:, supply_state]
    nvda_state = _sample_categorical(rng, nvda_probs, n_sims)
    amd_state = _sample_categorical(rng, amd_probs, n_sims)

    # State-dependent means
    state_mu_arr = np.array([STATE_MU[s] for s in STATES_LEAF])
    nvda_mu = state_mu_arr[nvda_state]
    amd_mu = state_mu_arr[amd_state]

    # Draw continuous returns
    matrix = rng.normal(NON_DAG_MU, NON_DAG_SIGMA, size=(n_sims, n_tickers))
    nvda_idx = tickers.index("NVDA")
    amd_idx = tickers.index("AMD")
    matrix[:, nvda_idx] = rng.normal(nvda_mu, DAG_LEAF_SIGMA)
    matrix[:, amd_idx] = rng.normal(amd_mu, DAG_LEAF_SIGMA)

    return MCResult(tickers=tickers, matrix=matrix)


def save(result: MCResult) -> None:
    path = data_path("scenarios", "mvp.parquet")
    df = pd.DataFrame(result.matrix, columns=result.tickers)
    df.to_parquet(path, index=False)
    meta = {
        "n_sims": int(result.matrix.shape[0]),
        "n_tickers": int(result.matrix.shape[1]),
        "mean_per_ticker": {
            t: float(result.matrix[:, i].mean()) for i, t in enumerate(result.tickers)
        },
        "std_per_ticker": {
            t: float(result.matrix[:, i].std()) for i, t in enumerate(result.tickers)
        },
    }
    data_path("scenarios", "mvp_meta.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )
