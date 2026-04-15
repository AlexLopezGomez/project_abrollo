"""CVaR-penalized portfolio optimization.

Objective:  maximize  E[R·w/1e6]  -  λ · CVaR_5[loss]
    where  loss = -R·w/1e6
    CVaR_5 linearized as   α + (1/(0.05·N)) Σ max(0, loss_i - α)

Constraints (submission rules, hard):
    w ≥ 0
    sum(w) = $1,000,000
    count(w > 0) ≥ 50
    each non-zero w ≥ $5,000

Because the MIP formulation of the last two is slow for N=99, we use a two-phase
relaxation: (1) unconstrained CVaR solve, (2) select top-K (50–60) tickers by
weight, re-solve restricted to that support with the min-$5K floor applied.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Iterable

import cvxpy as cp
import numpy as np
import pandas as pd

from abrollo.config import data_path

log = logging.getLogger(__name__)

LAMBDA = 2.0
ALPHA_LEVEL = 0.05       # CVaR 5%
MIN_WEIGHT = 5_000.0     # USD
BUDGET = 1_000_000.0     # USD
MIN_TICKERS = 50
MAX_TICKERS = 60


@dataclass
class CVaROutcome:
    weights: dict[str, float]
    expected_return_pct: float
    cvar5_pct: float
    status: str
    solver: str
    n_nonzero: int


def _solve_cvar(
    returns: np.ndarray,
    *,
    support_mask: np.ndarray | None = None,
    enforce_min_weight: bool = False,
) -> tuple[cp.Variable, cp.Problem]:
    n_sims, n_tickers = returns.shape
    w = cp.Variable(n_tickers, nonneg=True)
    alpha = cp.Variable()
    z = cp.Variable(n_sims, nonneg=True)

    scenario_returns = returns @ w / BUDGET
    losses = -scenario_returns

    cvar = alpha + cp.sum(z) / (ALPHA_LEVEL * n_sims)
    obj = cp.Maximize(cp.mean(scenario_returns) - LAMBDA * cvar)

    constraints = [
        cp.sum(w) == BUDGET,
        z >= losses - alpha,
    ]
    if support_mask is not None:
        off_support = np.where(~support_mask)[0]
        if off_support.size > 0:
            constraints.append(w[off_support] == 0)
        on_support = np.where(support_mask)[0]
        if enforce_min_weight and on_support.size > 0:
            constraints.append(w[on_support] >= MIN_WEIGHT)
    prob = cp.Problem(obj, constraints)
    return w, prob


def _best_solve(prob: cp.Problem) -> str:
    for solver in ("CLARABEL", "ECOS", "SCS"):
        try:
            prob.solve(solver=solver, verbose=False)
        except Exception as e:  # pragma: no cover
            log.warning("%s failed: %s", solver, e)
            continue
        if prob.status in ("optimal", "optimal_inaccurate"):
            return solver
    return "failed"


def optimize(returns_df: pd.DataFrame) -> CVaROutcome:
    tickers = list(returns_df.columns)
    R = returns_df.to_numpy(dtype=float)
    log.info("CVaR optimize on (%d sims, %d tickers), λ=%.2f", R.shape[0], R.shape[1], LAMBDA)

    # Phase 1: unconstrained CVaR (just ≥0, sum=1M).
    w1, prob1 = _solve_cvar(R)
    solver1 = _best_solve(prob1)
    if solver1 == "failed":
        raise RuntimeError(f"Phase 1 CVaR solve failed: {prob1.status}")
    log.info("Phase 1 (%s): status=%s, obj=%.6f", solver1, prob1.status, prob1.value)
    w_free = np.array(w1.value).flatten()

    # Phase 2: pick support, enforce min $5K.
    order = np.argsort(-w_free)
    for k in range(MAX_TICKERS, MIN_TICKERS - 1, -1):
        support = np.zeros(len(tickers), dtype=bool)
        support[order[:k]] = True
        if MIN_WEIGHT * k > BUDGET:
            continue
        w2, prob2 = _solve_cvar(R, support_mask=support, enforce_min_weight=True)
        solver2 = _best_solve(prob2)
        if solver2 != "failed" and prob2.status in ("optimal", "optimal_inaccurate"):
            log.info("Phase 2 (k=%d, %s): status=%s, obj=%.6f",
                     k, solver2, prob2.status, prob2.value)
            w_final = np.array(w2.value).flatten()
            return _assemble(tickers, R, w_final, prob2.status, solver2)
        log.warning("Phase 2 k=%d infeasible/failed", k)

    raise RuntimeError("Phase 2 failed at every support size from %d down to %d"
                       % (MAX_TICKERS, MIN_TICKERS))


def _assemble(
    tickers: list[str],
    returns: np.ndarray,
    weights: np.ndarray,
    status: str,
    solver: str,
) -> CVaROutcome:
    # Clean tiny numerical dust and force integer-dollar weights summing to budget.
    weights = np.where(weights < 1.0, 0.0, weights)
    nonzero_idx = np.where(weights > 0)[0]
    rounded = np.round(weights).astype(int)
    drift = int(BUDGET) - int(rounded.sum())
    if drift != 0 and nonzero_idx.size > 0:
        # Push drift onto the largest weight.
        top = nonzero_idx[np.argmax(weights[nonzero_idx])]
        rounded[top] += drift

    final = {t: int(rounded[i]) for i, t in enumerate(tickers) if rounded[i] > 0}

    wvec = np.zeros(len(tickers))
    for i, t in enumerate(tickers):
        wvec[i] = final.get(t, 0)
    sr = returns @ wvec / BUDGET
    exp_ret = float(sr.mean())
    losses = -sr
    worst_k = max(1, int(ALPHA_LEVEL * len(losses)))
    cvar5 = float(np.sort(losses)[-worst_k:].mean())

    return CVaROutcome(
        weights=final,
        expected_return_pct=exp_ret,
        cvar5_pct=cvar5,
        status=status,
        solver=solver,
        n_nonzero=len(final),
    )


def save(outcome: CVaROutcome, path_stem: str = "mvp") -> None:
    out = {
        "lambda": LAMBDA,
        "alpha_level": ALPHA_LEVEL,
        "expected_return_pct": outcome.expected_return_pct,
        "cvar_5_pct": outcome.cvar5_pct,
        "n_nonzero_tickers": outcome.n_nonzero,
        "solver": outcome.solver,
        "status": outcome.status,
        "weights": outcome.weights,
    }
    data_path("portfolios", f"{path_stem}.json").write_text(
        json.dumps(out, indent=2, sort_keys=True), encoding="utf-8"
    )
