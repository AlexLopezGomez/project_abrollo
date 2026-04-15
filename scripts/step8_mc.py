"""Step 8 — Run 1000 MC simulations.

Gate: matrix shape (1000, 99), finite means, non-zero std per ticker, no NaN.
Prints a stdout-ASCII histogram of NVDA returns as a sanity check.
"""
from __future__ import annotations

import logging

import numpy as np

from abrollo.mc.sim import N_SIMS, run, save

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("step8")


def ascii_histogram(values: np.ndarray, bins: int = 20, width: int = 40) -> str:
    counts, edges = np.histogram(values, bins=bins)
    peak = counts.max() or 1
    lines = []
    for c, lo, hi in zip(counts, edges[:-1], edges[1:]):
        bar = "#" * int(width * c / peak)
        lines.append(f"  [{lo:+.2f},{hi:+.2f}) {c:4d} {bar}")
    return "\n".join(lines)


def main() -> None:
    result = run(n_sims=N_SIMS)
    save(result)

    assert result.matrix.shape == (N_SIMS, len(result.tickers)), \
        f"Unexpected shape {result.matrix.shape}"
    log.info("Matrix shape: %s", result.matrix.shape)

    assert np.isfinite(result.matrix).all(), "NaN/Inf found in matrix"
    log.info("All values finite ✓")

    stds = result.matrix.std(axis=0)
    assert (stds > 0).all(), "Ticker(s) with zero std: %s" % np.where(stds == 0)[0]
    log.info("All %d tickers have positive std ✓", len(stds))

    means = result.matrix.mean(axis=0)
    log.info("Mean return range: [%.3f, %.3f]", means.min(), means.max())

    nvda_idx = result.tickers.index("NVDA")
    nvda_returns = result.matrix[:, nvda_idx]
    log.info("NVDA — mean=%.3f  std=%.3f  min=%.3f  max=%.3f",
             nvda_returns.mean(), nvda_returns.std(), nvda_returns.min(), nvda_returns.max())
    log.info("NVDA histogram:\n%s", ascii_histogram(nvda_returns))

    log.info("Step 8 GATE PASSED")


if __name__ == "__main__":
    main()
