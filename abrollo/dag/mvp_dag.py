"""5-node Bayesian DAG for the MVP, hand-wired from hypotheses semi.json.

Structure:

    TSMC_event  (F/T)          export_control  (F/T)
           \\                      /
            \\                    /
             +--> supply_delta <-+
                    (none/mild/severe)
                         |
                  +------+------+
                  v             v
              NVDA_return   AMD_return
              (up/flat/down)  (up/flat/down)

Root priors are taken from the matching semi hypotheses:
  - TSMC_event     p=0.12  (H_SEMI_03 Taiwan Strait escalation)
  - export_control p=0.65  (H_SEMI_01 US export controls expansion)

Leaf discretization (up/flat/down) becomes the conditioning variable for
Step 8's Monte Carlo: continuous returns are sampled from a Normal centered on
each state's mean with fixed σ=0.15.
"""
from __future__ import annotations

import pickle
from pathlib import Path

try:
    from pgmpy.models import DiscreteBayesianNetwork as _BN
except ImportError:  # older pgmpy
    from pgmpy.models import BayesianNetwork as _BN

from pgmpy.factors.discrete import TabularCPD
from pgmpy.inference import VariableElimination

from abrollo.config import data_path


STATE_NAMES = {
    "TSMC_event": ["F", "T"],
    "export_control": ["F", "T"],
    "supply_delta": ["none", "mild", "severe"],
    "NVDA_return": ["up", "flat", "down"],
    "AMD_return": ["up", "flat", "down"],
}


def build_model() -> _BN:
    model = _BN(
        [
            ("TSMC_event", "supply_delta"),
            ("export_control", "supply_delta"),
            ("supply_delta", "NVDA_return"),
            ("supply_delta", "AMD_return"),
        ]
    )

    # Root priors (from hypothesis trigger_probability).
    cpd_tsmc = TabularCPD(
        "TSMC_event",
        2,
        [[0.88], [0.12]],
        state_names={"TSMC_event": STATE_NAMES["TSMC_event"]},
    )
    cpd_ec = TabularCPD(
        "export_control",
        2,
        [[0.35], [0.65]],
        state_names={"export_control": STATE_NAMES["export_control"]},
    )

    # supply_delta | TSMC, EC
    # Column order matches evidence_card order: TSMC (2) × EC (2) = 4 cols.
    # Columns: (TSMC=F,EC=F) (TSMC=F,EC=T) (TSMC=T,EC=F) (TSMC=T,EC=T)
    cpd_supply = TabularCPD(
        "supply_delta",
        3,
        values=[
            # none
            [0.85, 0.20, 0.05, 0.02],
            # mild
            [0.12, 0.65, 0.35, 0.18],
            # severe
            [0.03, 0.15, 0.60, 0.80],
        ],
        evidence=["TSMC_event", "export_control"],
        evidence_card=[2, 2],
        state_names={
            "supply_delta": STATE_NAMES["supply_delta"],
            "TSMC_event": STATE_NAMES["TSMC_event"],
            "export_control": STATE_NAMES["export_control"],
        },
    )

    # NVDA_return | supply_delta
    cpd_nvda = TabularCPD(
        "NVDA_return",
        3,
        values=[
            # up
            [0.55, 0.25, 0.05],
            # flat
            [0.35, 0.40, 0.20],
            # down
            [0.10, 0.35, 0.75],
        ],
        evidence=["supply_delta"],
        evidence_card=[3],
        state_names={
            "NVDA_return": STATE_NAMES["NVDA_return"],
            "supply_delta": STATE_NAMES["supply_delta"],
        },
    )

    # AMD_return | supply_delta (less severe tail than NVDA because not an AI monopoly)
    cpd_amd = TabularCPD(
        "AMD_return",
        3,
        values=[
            [0.50, 0.30, 0.10],
            [0.35, 0.40, 0.30],
            [0.15, 0.30, 0.60],
        ],
        evidence=["supply_delta"],
        evidence_card=[3],
        state_names={
            "AMD_return": STATE_NAMES["AMD_return"],
            "supply_delta": STATE_NAMES["supply_delta"],
        },
    )

    model.add_cpds(cpd_tsmc, cpd_ec, cpd_supply, cpd_nvda, cpd_amd)
    assert model.check_model(), "DAG structure/CPDs invalid"
    return model


def save(model: _BN) -> tuple[Path, Path]:
    pkl = data_path("dag", "mvp.pkl")
    with pkl.open("wb") as f:
        pickle.dump(model, f)
    # A human-readable JSON-ish dump of the CPDs.
    human = data_path("dag", "mvp.json")
    lines = ["# MVP DAG — CPDs", ""]
    for cpd in model.get_cpds():
        lines.append(str(cpd))
        lines.append("")
    human.write_text("\n".join(lines), encoding="utf-8")
    return pkl, human


def query_nvda_conditional(model: _BN) -> float:
    """Return P(NVDA_return=down | TSMC=T, export_control=T) as a sanity check."""
    infer = VariableElimination(model)
    q = infer.query(
        variables=["NVDA_return"],
        evidence={"TSMC_event": "T", "export_control": "T"},
        show_progress=False,
    )
    idx_down = STATE_NAMES["NVDA_return"].index("down")
    return float(q.values[idx_down])
