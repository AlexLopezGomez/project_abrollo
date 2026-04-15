"""Shared MVP configuration constants."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"

load_dotenv(REPO_ROOT / ".env")

CALA_API_KEY = os.getenv("CALA_API_KEY", "").strip()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()

CALA_BASE_URL = "https://api.cala.ai"
CUTOFF_DATE = "2025-04-15"

ANTHROPIC_MODEL = "claude-sonnet-4-6"

SEMI_ANCHOR_TICKERS = ["NVDA", "AMD", "INTC", "QCOM", "AVGO"]


def require_cala_key() -> str:
    if not CALA_API_KEY:
        raise RuntimeError("CALA_API_KEY missing from environment / .env")
    return CALA_API_KEY


def require_anthropic_key() -> str:
    if not ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY missing from environment / .env")
    return ANTHROPIC_API_KEY


def data_path(*parts: str) -> Path:
    p = DATA_DIR.joinpath(*parts)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p
