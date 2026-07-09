from __future__ import annotations

import json
import pickle
import re
from datetime import datetime
from pathlib import Path

import networkx as nx
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
SUBMISSIONS = DATA / "submissions"
RUNS = DATA / "runs"
SUBMISSION_PATTERNS = ("mvp_run_*.json", "mvp2_run_*.json")
SUBMISSION_RE = re.compile(r"^(?P<pipeline>mvp2|mvp)_run_(?P<stamp>\d{8}_\d{6})\.json$")
RUN_REF_PREFIX = "run:"
RUN_ARTIFACTS = {
    "hypotheses": "hypotheses.json",
    "dag": "dag.json",
    "portfolio": "portfolio.json",
    "graph": "graph.gpickle",
    "graph_summary": "graph_summary.json",
}
ARTIFACTS = {
    "mvp": {
        "hypotheses": DATA / "hypotheses" / "semi.json",
        "dag": DATA / "dag" / "mvp.json",
        "portfolio": DATA / "portfolios" / "mvp.json",
        "graph": DATA / "graph" / "mvp.gpickle",
        "graph_summary": DATA / "graph" / "mvp_summary.json",
    },
    "mvp2": {
        "hypotheses": DATA / "hypotheses" / "mvp2.json",
        "dag": DATA / "dag" / "mvp2.json",
        "portfolio": DATA / "portfolios" / "mvp2.json",
        "graph": DATA / "graph" / "mvp2.gpickle",
        "graph_summary": DATA / "graph" / "mvp2_summary.json",
    },
}


def _submission_files() -> list[Path]:
    files_by_name: dict[str, Path] = {}
    for pattern in SUBMISSION_PATTERNS:
        for path in SUBMISSIONS.glob(pattern):
            files_by_name[path.name] = path
    return sorted(files_by_name.values(), key=lambda p: (_submission_timestamp(p.name, p.stat().st_mtime), p.name))


def _submission_timestamp(filename: str, mtime: float | None = None) -> datetime:
    match = SUBMISSION_RE.match(filename)
    if match:
        return datetime.strptime(match.group("stamp"), "%Y%m%d_%H%M%S")
    if mtime is not None:
        return datetime.fromtimestamp(mtime)
    return datetime.min


def _submission_pipeline(filename: str) -> str:
    match = SUBMISSION_RE.match(filename)
    if not match:
        return "Unknown"
    return "MVP-2" if match.group("pipeline") == "mvp2" else "MVP-1"


def _submission_artifact_key(filename: str) -> str:
    match = SUBMISSION_RE.match(filename)
    if not match:
        return "mvp2"
    return match.group("pipeline")


def _run_id(filename: str) -> str:
    return Path(filename).stem


def _snapshot_dir(run_id: str) -> Path:
    return RUNS / run_id


def _snapshot_manifest_path(run_id: str) -> Path:
    return _snapshot_dir(run_id) / "manifest.json"


def _artifact_ref(filename: str) -> str:
    run_id = _run_id(filename)
    if _snapshot_manifest_path(run_id).exists():
        return f"{RUN_REF_PREFIX}{run_id}"
    return _submission_artifact_key(filename)


def _artifact_path(artifact_key: str, kind: str) -> Path:
    if artifact_key.startswith(RUN_REF_PREFIX):
        run_id = artifact_key.removeprefix(RUN_REF_PREFIX)
        return _snapshot_dir(run_id) / RUN_ARTIFACTS[kind]
    return ARTIFACTS.get(artifact_key, ARTIFACTS["mvp2"])[kind]


def _path_mtime(path: Path) -> float:
    return path.stat().st_mtime if path.exists() else 0.0


def _latest_submission_file() -> Path:
    files = _submission_files()
    if not files:
        raise FileNotFoundError("No submission files found in data/submissions/")
    return files[-1]


@st.cache_data
def _load_submission_data(filename: str, mtime: float) -> dict:
    path = SUBMISSIONS / filename
    return json.loads(path.read_text(encoding="utf-8"))


def load_submission(filename: str) -> tuple[dict, str]:
    path = SUBMISSIONS / filename
    return _load_submission_data(filename, path.stat().st_mtime), filename


def load_latest_submission(filename: str) -> tuple[dict, str]:
    return load_submission(filename)


def _history_row(filename: str, mtime: float, submission: dict) -> dict:
    request = submission.get("request") or {}
    response = submission.get("response") or {}
    transactions = request.get("transactions") or []
    run_id = _run_id(filename)
    manifest = _load_run_manifest(run_id)
    artifact_key = _artifact_ref(filename)
    snapshot_status = "snapshotted" if manifest else "legacy"
    total_invested = response.get("total_invested")
    if total_invested is None:
        total_invested = sum(float(tx.get("amount") or 0) for tx in transactions)
    total_value = response.get("total_value")
    return_pct = None
    if total_invested and total_value is not None:
        return_pct = (float(total_value) / float(total_invested) - 1) * 100

    success = response.get("success")
    if success is True:
        status = "success"
    elif success is False:
        status = "failed"
    else:
        status = submission.get("status", "unknown")

    return {
        "filename": filename,
        "run_id": run_id,
        "timestamp": _submission_timestamp(filename, mtime),
        "artifact_key": artifact_key,
        "artifact_label": run_id if snapshot_status == "snapshotted" else _submission_artifact_key(filename),
        "snapshot_status": snapshot_status,
        "snapshot_path": str(_snapshot_dir(run_id)) if manifest else "",
        "hypotheses_count": manifest.get("hypotheses_count") if manifest else None,
        "graph_nodes": manifest.get("graph_nodes") if manifest else None,
        "graph_edges": manifest.get("graph_edges") if manifest else None,
        "pipeline": _submission_pipeline(filename),
        "status": status,
        "http_status": submission.get("status"),
        "submission_id": response.get("submission_id", ""),
        "agent": request.get("model_agent_name", ""),
        "version": request.get("model_agent_version", ""),
        "total_invested": total_invested,
        "total_value": total_value,
        "return_pct": return_pct,
        "n_transactions": len(transactions),
    }


@st.cache_data
def load_submission_history(file_state: tuple[tuple[str, float, float], ...]) -> list[dict]:
    rows = []
    for filename, mtime, _manifest_mtime in file_state:
        submission = _load_submission_data(filename, mtime)
        rows.append(_history_row(filename, mtime, submission))
    return sorted(rows, key=lambda r: (r["timestamp"], r["filename"]), reverse=True)


def get_submission_history() -> list[dict]:
    files = _submission_files()
    file_state = tuple(
        (
            path.name,
            path.stat().st_mtime,
            _path_mtime(_snapshot_manifest_path(_run_id(path.name))),
        )
        for path in files
    )
    return load_submission_history(file_state)


def get_latest_submission() -> tuple[dict, str]:
    latest = _latest_submission_file()
    return load_submission(latest.name)


def _load_run_manifest(run_id: str) -> dict:
    path = _snapshot_manifest_path(run_id)
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return raw if isinstance(raw, dict) else {}


@st.cache_data
def _load_json_artifact(path_str: str, mtime: float) -> object:
    try:
        return json.loads(Path(path_str).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def get_hypotheses(artifact_key: str = "mvp2") -> list[dict]:
    path = _artifact_path(artifact_key, "hypotheses")
    raw = _load_json_artifact(str(path), _path_mtime(path))
    if isinstance(raw, dict):
        raw_hypotheses = raw.get("hypotheses") or []
    elif isinstance(raw, list):
        raw_hypotheses = raw
    else:
        raw_hypotheses = []
    return [_normalize_hypothesis(h, artifact_key, i) for i, h in enumerate(raw_hypotheses)]


@st.cache_data
def load_hypotheses(mtime: float) -> list[dict]:
    path = _artifact_path("mvp2", "hypotheses")
    raw = _load_json_artifact(str(path), mtime)
    return raw if isinstance(raw, list) else []


def get_dag(artifact_key: str = "mvp2", hypotheses: list[dict] | None = None) -> list[dict]:
    path = _artifact_path(artifact_key, "dag")
    raw = _load_json_artifact(str(path), _path_mtime(path))
    if isinstance(raw, list):
        return [_normalize_dag_entry(e) for e in raw if isinstance(e, dict)]
    if hypotheses is None:
        hypotheses = get_hypotheses(artifact_key)
    return _dag_from_hypotheses(hypotheses)


@st.cache_data
def load_dag(mtime: float) -> list[dict]:
    path = _artifact_path("mvp2", "dag")
    raw = _load_json_artifact(str(path), mtime)
    return raw if isinstance(raw, list) else []


def get_portfolio(artifact_key: str = "mvp2") -> dict:
    path = _artifact_path(artifact_key, "portfolio")
    raw = _load_json_artifact(str(path), _path_mtime(path))
    if isinstance(raw, dict):
        raw.setdefault("weights", {})
        return raw
    return {"weights": {}, "solver": "—", "n_nonzero_tickers": 0}


@st.cache_data
def load_portfolio(mtime: float) -> dict:
    path = _artifact_path("mvp2", "portfolio")
    raw = _load_json_artifact(str(path), mtime)
    return raw if isinstance(raw, dict) else {"weights": {}}


def get_graph_mtime(artifact_key: str = "mvp2") -> float:
    return _path_mtime(_artifact_path(artifact_key, "graph"))


def get_graph_summary_mtime(artifact_key: str = "mvp2") -> float:
    return _path_mtime(_artifact_path(artifact_key, "graph_summary"))


@st.cache_resource
def load_graph(artifact_key: str = "mvp2", mtime: float | None = None) -> nx.DiGraph | None:
    path = _artifact_path(artifact_key, "graph")
    if not path.exists():
        return None
    try:
        with open(path, "rb") as f:
            return pickle.load(f)
    except Exception:
        return None


@st.cache_data
def load_graph_summary(artifact_key: str = "mvp2", mtime: float | None = None) -> dict:
    path = _artifact_path(artifact_key, "graph_summary")
    raw = _load_json_artifact(str(path), _path_mtime(path) if mtime is None else mtime)
    return raw if isinstance(raw, dict) else {}


@st.cache_data
def build_hypothesis_subgraph(
    artifact_key: str,
    graph_mtime: float,
    origin_uuids: frozenset,
    portfolio_tickers: frozenset,
    depth: int,
) -> list[str]:
    G = load_graph(artifact_key, graph_mtime)
    if G is None:
        return []
    G_und = G.to_undirected(as_view=True)
    nodes: set[str] = set()
    for seed in origin_uuids:
        if seed in G_und:
            ego = nx.ego_graph(G_und, seed, radius=depth)
            nodes.update(ego.nodes())
    for node, data in G.nodes(data=True):
        if data.get("is_ndx") and data.get("ticker", "") in portfolio_tickers:
            nodes.add(node)
    return list(nodes)


def _normalize_hypothesis(h: dict, artifact_key: str, index: int) -> dict:
    probability = h.get("probability", h.get("trigger_probability", 0))
    magnitude = h.get("magnitude", h.get("effect_magnitude", 0))
    effect_target = h.get("effect_target")
    origin_uuid = h.get("origin_entity_uuid") or h.get("origin_uuid") or ""
    return {
        **h,
        "id": h.get("id", f"{artifact_key.upper()}_{index + 1:02d}"),
        "trigger": h.get("trigger", ""),
        "origin_entity_uuid": origin_uuid,
        "probability": probability,
        "magnitude": magnitude,
        "horizon_days": h.get("horizon_days", "—"),
        "sources": h.get("sources") or [],
        "source_dates": h.get("source_dates") or [],
        "effect_target": effect_target,
    }


def _normalize_dag_entry(entry: dict) -> dict:
    affected = entry.get("affected_tickers") or []
    return {
        **entry,
        "hypothesis_id": entry.get("hypothesis_id") or entry.get("id", ""),
        "origin_uuid": entry.get("origin_uuid") or entry.get("origin_entity_uuid", ""),
        "origin_name": entry.get("origin_name", ""),
        "affected_tickers": affected,
        "n_affected": entry.get("n_affected", len(affected)),
    }


def _dag_from_hypotheses(hypotheses: list[dict]) -> list[dict]:
    rows = []
    for h in hypotheses:
        target = h.get("effect_target")
        affected = []
        if target:
            affected.append({
                "ticker": target,
                "name": target,
                "shift": h.get("magnitude", 0),
            })
        rows.append({
            "hypothesis_id": h.get("id", ""),
            "origin_uuid": h.get("origin_entity_uuid", ""),
            "origin_name": target or "MVP-1",
            "affected_tickers": affected,
            "n_affected": len(affected),
        })
    return rows
