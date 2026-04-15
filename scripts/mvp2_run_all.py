"""MVP-2 — Run all steps sequentially.

Usage: python scripts/mvp2_run_all.py [start_step]
  start_step: 1-10 (default: 1). Resumes from a specific step.
"""
from __future__ import annotations

import importlib
import sys
import time

STEPS = [
    ("mvp2_step1_preflight", "Step 1: Preflight"),
    ("mvp2_step2_bulk_retrieve", "Step 2: Bulk retrieve"),
    ("mvp2_step3_covariance", "Step 3: Covariance matrix"),
    ("mvp2_step4_graph", "Step 4: Relationship graph"),
    ("mvp2_step5_hypotheses", "Step 5: Hypotheses"),
    ("mvp2_step6_propagation", "Step 6: Propagation"),
    ("mvp2_step7_mc", "Step 7: Monte Carlo"),
    ("mvp2_step8_optimize", "Step 8: CVaR optimizer"),
    ("mvp2_step9_validate", "Step 9: Validator"),
    ("mvp2_step10_submit", "Step 10: Submit"),
]


def main() -> int:
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    t0 = time.monotonic()

    for i, (module_name, label) in enumerate(STEPS, 1):
        if i < start:
            continue
        print(f"\n{'='*60}")
        print(f"  {label}")
        print(f"{'='*60}")
        mod = importlib.import_module(f"scripts.{module_name}")
        rc = mod.main()
        if rc != 0:
            print(f"\n*** HALTED at {label} (exit code {rc}) ***")
            return rc

    elapsed = time.monotonic() - t0
    print(f"\n{'='*60}")
    print(f"  MVP-2 complete in {elapsed/60:.1f} min")
    print(f"{'='*60}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
