"""MVP-2 Step 3 — Empirical covariance matrix from Cala numerical_observations.

Strategy:
  1. Try to extract return-like series from Cala numobs per ticker.
  2. If enough tickers have data (>=10 with >=24 aligned observations),
     use Ledoit-Wolf shrinkage.
  3. Otherwise, build a single-factor model: Σ_ij = σ_i · σ_j · ρ  (ρ=0.30).
     For tickers without data, use σ_default = 0.20 (monthly).

The matrix is always built for ALL tickers in the entity directory so it
matches the scenario column space.
"""
from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.covariance import LedoitWolf

from abrollo.config import CUTOFF_DATE, data_path

log = logging.getLogger(__name__)

ENTITIES_DIR = data_path("cala_entities")
PRICE_KEYWORDS = ["stock_price", "share_price", "market_cap", "total_return",
                  "closing price", "stock price", "share price", "market cap",
                  "market capitalization", "total return", "revenue"]
FALLBACK_RHO = 0.30
FALLBACK_SIGMA = 0.20  # monthly vol for tickers with no data
MIN_ALIGNED_OBS = 24
MIN_TICKERS_FOR_LW = 10


def _find_best_series(numobs: list[dict], cutoff: date) -> list[dict] | None:
    """Pick the numerical observation series most likely to be a price/return proxy."""
    if not numobs:
        return None

    by_metric: dict[str, list[dict]] = {}
    metric_names: dict[str, str] = {}

    for obs in numobs:
        if not isinstance(obs, dict):
            continue
        # Handle nested structure: numobs from retrieve_entity have 'data' arrays
        if "data" in obs and isinstance(obs["data"], list):
            metric_id = obs.get("id", "unknown")
            metric_name = obs.get("name", "")
            metric_names[metric_id] = metric_name
            for dp in obs["data"]:
                if not isinstance(dp, dict):
                    continue
                t = dp.get("time", "")
                v = dp.get("value")
                if t and v is not None:
                    try:
                        d = date.fromisoformat(str(t)[:10])
                    except ValueError:
                        continue
                    if d <= cutoff:
                        by_metric.setdefault(metric_id, []).append(
                            {"date": str(t)[:10], "value": v}
                        )
            continue

        # Flat structure (legacy format)
        obs_date = obs.get("date") or obs.get("time", "")
        if not obs_date:
            continue
        try:
            d = date.fromisoformat(str(obs_date)[:10])
        except ValueError:
            continue
        if d > cutoff:
            continue
        metric_id = obs.get("metric_id", obs.get("id", "unknown"))
        name = obs.get("metric_name", obs.get("name", ""))
        metric_names[metric_id] = name
        by_metric.setdefault(metric_id, []).append(obs)

    if not by_metric:
        return None

    # Prefer price-like metrics
    for mid, name in metric_names.items():
        lower = name.lower()
        if any(kw in lower for kw in PRICE_KEYWORDS):
            series = by_metric[mid]
            if len(series) >= 12:
                log.debug("Found price-like metric: %s (%d obs)", name, len(series))
                return series

    # Fallback: longest series
    best_id = max(by_metric, key=lambda k: len(by_metric[k]))
    best = by_metric[best_id]
    log.debug("Using longest series: %s (%d obs)", metric_names.get(best_id, "?"), len(best))
    return best


def _series_to_monthly_log_returns(observations: list[dict]) -> pd.Series:
    """Convert dated observations to monthly log-return series."""
    records = []
    for obs in observations:
        try:
            d = date.fromisoformat(str(obs.get("date", obs.get("time", "")))[:10])
            v = float(obs["value"])
            if v > 0:
                records.append((d, v))
        except (ValueError, KeyError, TypeError):
            continue

    if len(records) < 2:
        return pd.Series(dtype=float)

    df = pd.DataFrame(records, columns=["date", "value"])
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").drop_duplicates(subset="date", keep="last")
    df = df.set_index("date")

    monthly = df["value"].resample("ME").last().dropna()
    if len(monthly) < 2:
        return pd.Series(dtype=float)

    log_ret = np.log(monthly / monthly.shift(1)).dropna()
    return log_ret


def build_covariance(
    entities_dir: Path = ENTITIES_DIR,
    cutoff_date: str = CUTOFF_DATE,
) -> tuple[np.ndarray, list[str], dict[str, Any]]:
    """Build the covariance matrix for all tickers in the entity directory.

    Returns: (sigma, ticker_uuids, metadata_dict)
    Ticker order uses entity UUIDs (matching scenario matrix columns).
    """
    cutoff = date.fromisoformat(cutoff_date)

    ticker_files = sorted(entities_dir.glob("*.json"))
    ticker_files = [f for f in ticker_files if not f.name.startswith("_")]

    # Collect all ticker UUIDs and whatever return series we can extract
    all_ticker_uuids: list[str] = []
    seen_uuids: set[str] = set()
    ticker_series: dict[str, pd.Series] = {}  # keyed by UUID
    uuid_to_ticker: dict[str, str] = {}

    for fpath in ticker_files:
        ticker = fpath.stem
        try:
            entity = json.loads(fpath.read_text(encoding="utf-8"))
        except Exception as e:
            log.warning("Failed to load %s: %s", fpath, e)
            continue

        entity_uuid = entity.get("id", "")
        if not entity_uuid or entity_uuid in seen_uuids:
            continue
        seen_uuids.add(entity_uuid)

        all_ticker_uuids.append(entity_uuid)
        uuid_to_ticker[entity_uuid] = ticker

        numobs = entity.get("numerical_observations", [])
        if isinstance(numobs, dict):
            flat: list[dict] = []
            for v in numobs.values():
                if isinstance(v, list):
                    flat.extend(v)
            numobs = flat

        series_data = _find_best_series(numobs, cutoff)
        if not series_data:
            continue

        monthly_ret = _series_to_monthly_log_returns(series_data)
        if len(monthly_ret) >= 2:
            ticker_series[entity_uuid] = monthly_ret

    n_total = len(all_ticker_uuids)
    n_with_data = len(ticker_series)
    log.info("Tickers: %d total, %d with return series", n_total, n_with_data)

    meta: dict[str, Any] = {
        "n_tickers": n_total,
        "n_tickers_with_data": n_with_data,
        "cutoff": cutoff_date,
        "tickers": all_ticker_uuids,
        "uuid_to_ticker": uuid_to_ticker,
    }

    # Decide strategy
    use_lw = False
    if n_with_data >= MIN_TICKERS_FOR_LW:
        returns_df = pd.DataFrame(ticker_series)
        returns_df = returns_df.dropna(axis=0, how="all")
        if len(returns_df) >= MIN_ALIGNED_OBS:
            use_lw = True
            meta["n_obs"] = len(returns_df)

    if use_lw:
        log.info("Using Ledoit-Wolf on %d tickers × %d observations", n_with_data, len(returns_df))
        filled = returns_df.fillna(returns_df.mean())
        X = filled.values
        lw = LedoitWolf()
        lw.fit(X)

        # Build full matrix: LW for tickers with data, single-factor for rest
        lw_uuids = list(returns_df.columns)
        lw_cov = lw.covariance_
        lw_stds = np.sqrt(np.diag(lw_cov))

        sigma = np.full((n_total, n_total), 0.0)
        idx_map = {uid: i for i, uid in enumerate(all_ticker_uuids)}
        lw_idx_map = {uid: i for i, uid in enumerate(lw_uuids)}

        # Fill LW block
        for uid_i in lw_uuids:
            for uid_j in lw_uuids:
                i, j = idx_map[uid_i], idx_map[uid_j]
                li, lj = lw_idx_map[uid_i], lw_idx_map[uid_j]
                sigma[i, j] = lw_cov[li, lj]

        # Fill non-LW tickers with single-factor
        for uid in all_ticker_uuids:
            if uid in lw_idx_map:
                continue
            i = idx_map[uid]
            sigma[i, i] = FALLBACK_SIGMA ** 2
            for uid_j in all_ticker_uuids:
                if uid == uid_j:
                    continue
                j = idx_map[uid_j]
                sigma_j = lw_stds[lw_idx_map[uid_j]] if uid_j in lw_idx_map else FALLBACK_SIGMA
                sigma[i, j] = FALLBACK_SIGMA * sigma_j * FALLBACK_RHO
                sigma[j, i] = sigma[i, j]

        meta["method"] = "ledoit_wolf_hybrid"
        meta["shrinkage_coef"] = float(lw.shrinkage_)
    else:
        # Pure single-factor fallback for all tickers
        log.warning("FALLBACK: only %d tickers with data. Using single-factor model for all %d.",
                     n_with_data, n_total)
        stds = np.full(n_total, FALLBACK_SIGMA)
        # Use actual stds where available
        for uid, series in ticker_series.items():
            if uid in {u: i for i, u in enumerate(all_ticker_uuids)}:
                idx = all_ticker_uuids.index(uid)
                stds[idx] = series.std() if len(series) > 1 else FALLBACK_SIGMA

        sigma = np.outer(stds, stds) * FALLBACK_RHO
        np.fill_diagonal(sigma, stds ** 2)

        meta["method"] = "single_factor"
        meta["rho"] = FALLBACK_RHO
        meta["n_obs"] = 0
        meta["shrinkage_coef"] = None

    # Ensure PSD
    eigvals = np.linalg.eigvalsh(sigma)
    min_eig = eigvals.min()
    if min_eig < -1e-10:
        log.warning("Σ has negative eigenvalue %.2e — projecting to nearest PSD", min_eig)
        eigvals_clipped = np.maximum(eigvals, 0)
        Q = np.linalg.eigh(sigma)[1]
        sigma = Q @ np.diag(eigvals_clipped) @ Q.T
        sigma = (sigma + sigma.T) / 2
        meta["psd_projected"] = True

    meta["min_eigenvalue"] = float(np.linalg.eigvalsh(sigma).min())

    # Correlation diagnostics
    diag = np.diag(sigma)
    d_inv = np.diag(1.0 / np.sqrt(diag + 1e-30))
    corr = d_inv @ sigma @ d_inv
    np.fill_diagonal(corr, np.nan)
    meta["max_offdiag_corr"] = float(np.nanmax(corr))
    meta["median_offdiag_corr"] = float(np.nanmedian(corr))

    return sigma, all_ticker_uuids, meta


def save_covariance(sigma: np.ndarray, tickers: list[str], meta: dict[str, Any]) -> Path:
    """Save Σ to data/cov/mvp2.npz + metadata JSON."""
    out_dir = data_path("cov")
    out_dir.mkdir(parents=True, exist_ok=True)

    npz_path = out_dir / "mvp2.npz"
    np.savez(npz_path, sigma=sigma, tickers=np.array(tickers))

    meta_path = out_dir / "mvp2_meta.json"
    meta_path.write_text(json.dumps(meta, indent=2, default=str), encoding="utf-8")

    log.info("Saved Σ (%d×%d) to %s", sigma.shape[0], sigma.shape[1], npz_path)
    return npz_path
