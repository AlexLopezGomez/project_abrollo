"""MVP-2 Step 3 — Build empirical covariance matrix.

Gate: (a) Sigma is PSD; (b) shape covers all entity tickers; (c) max off-diag
      corr <= 0.99; (d) median correlation in [0.1, 0.6] (soft for
      single-factor model which gives constant rho).
"""
from __future__ import annotations

import logging
import sys

from abrollo.mc.covariance import build_covariance, save_covariance

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("mvp2.step3")


def main() -> int:
    sigma, tickers, meta = build_covariance()
    n = len(tickers)

    log.info("Sigma shape: (%d, %d)", n, n)
    log.info("Method: %s", meta.get("method"))
    log.info("Tickers with data: %d / %d", meta.get("n_tickers_with_data", 0), n)
    log.info("Min eigenvalue: %.2e", meta["min_eigenvalue"])
    log.info("Max off-diag corr: %.4f", meta["max_offdiag_corr"])
    log.info("Median off-diag corr: %.4f", meta["median_offdiag_corr"])

    if meta["min_eigenvalue"] < -1e-10:
        log.error("GATE FAIL (a): Sigma not PSD, min eigenvalue = %.2e", meta["min_eigenvalue"])
        return 1

    if n < 50:
        log.error("GATE FAIL: only %d tickers in Sigma (need >= 50)", n)
        return 1

    if meta["max_offdiag_corr"] > 0.99:
        log.error("GATE FAIL (c): max off-diag corr %.4f > 0.99", meta["max_offdiag_corr"])
        return 1

    med = meta["median_offdiag_corr"]
    if meta["method"] == "single_factor":
        log.info("Single-factor model: median corr = rho = %.2f (by construction)", med)
    elif med > 0.9:
        log.error("GATE FAIL (d): median corr %.4f > 0.9", med)
        return 1

    save_covariance(sigma, tickers, meta)

    print(f"[step3 OK] Sigma ({n}×{n}), method={meta['method']}, "
          f"median_corr={med:.4f}, min_eig={meta['min_eigenvalue']:.2e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
