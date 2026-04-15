"""NASDAQ-100 ticker list fetch + UUID resolution against Cala.

We scrape the Wikipedia NASDAQ-100 table, then call `entity_search` per name to
resolve to a Cala Company UUID. Rate-limited at ~1 call / 1.1s to stay under the
~60/min Cala ceiling observed in Step 1.
"""
from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import asdict, dataclass
from typing import Any

import requests
from bs4 import BeautifulSoup

from abrollo.cala.client import CalaClient, CalaError
from abrollo.config import data_path

log = logging.getLogger(__name__)

WIKI_URL = "https://en.wikipedia.org/wiki/Nasdaq-100"
SAFE_THROTTLE = 1.1  # seconds per call — stay under ~55/min

# Wikipedia's short name for these tickers yields subsidiaries in entity_search.
# Override with a more specific search string. Keys are Wikipedia-exact ticker symbols.
SEARCH_OVERRIDES: dict[str, str] = {
    "INTC": "Intel Corporation",
}

# Suffixes we strip to improve fuzzy matching against Cala names.
_COMPANY_SUFFIXES = re.compile(
    r"\b(inc\.?|incorporated|corp\.?|corporation|company|co\.?|"
    r"ltd\.?|limited|plc|holdings?|group|the)\b",
    re.IGNORECASE,
)
_NON_WORD = re.compile(r"[^a-z0-9 ]+")


@dataclass
class TickerResolution:
    ticker: str
    name: str
    uuid: str | None
    match_name: str | None
    strategy: str  # "exact", "prefix", "token", or "miss"


def normalize(name: str) -> str:
    n = name.lower()
    n = _COMPANY_SUFFIXES.sub(" ", n)
    n = _NON_WORD.sub(" ", n)
    return " ".join(n.split())


def first_token(name: str) -> str:
    toks = normalize(name).split()
    return toks[0] if toks else ""


def fetch_ndx_from_wikipedia() -> list[tuple[str, str]]:
    """Return [(ticker, company_name), ...] scraped from Wikipedia."""
    log.info("Fetching NASDAQ-100 table from %s", WIKI_URL)
    r = requests.get(WIKI_URL, headers={"User-Agent": "abrollo-mvp/0.0.1"}, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")

    # Find the table with a "Ticker" or "Symbol" header and a "Company" header.
    target = None
    for table in soup.find_all("table", class_="wikitable"):
        headers = [th.get_text(strip=True).lower() for th in table.find_all("th")]
        if any(h in headers for h in ("ticker", "symbol")) and "company" in headers:
            target = table
            break
    if target is None:
        raise RuntimeError("Could not locate NASDAQ-100 constituents table on Wikipedia")

    header_cells = [th.get_text(strip=True).lower() for th in target.find("tr").find_all("th")]
    try:
        ticker_idx = next(i for i, h in enumerate(header_cells) if h in ("ticker", "symbol"))
        company_idx = header_cells.index("company")
    except (StopIteration, ValueError) as e:
        raise RuntimeError(f"Wikipedia table headers unexpected: {header_cells}") from e

    rows: list[tuple[str, str]] = []
    for tr in target.find_all("tr")[1:]:
        cells = tr.find_all(["td", "th"])
        if len(cells) <= max(ticker_idx, company_idx):
            continue
        ticker = cells[ticker_idx].get_text(strip=True)
        company = cells[company_idx].get_text(strip=True)
        if ticker and company:
            rows.append((ticker.upper(), company))
    log.info("Parsed %d NASDAQ-100 rows", len(rows))
    return rows


def pick_best_company(query_name: str, entities: list[dict[str, Any]]) -> tuple[dict | None, str]:
    """Given entity_search results, pick the best Company match.

    Preference order (lower score = better):
      0  exact token-list match after normalization (e.g. "intel" == normalize("INTEL CORP"))
      1  candidate is a prefix of query tokens (query has extra qualifier like "Holdings")
      2+ query is a prefix of candidate (candidate has *extra* tokens — often a subsidiary,
         penalty grows with each extra token)
     10+ loose token overlap (last resort)
    """
    q_tokens = normalize(query_name).split()
    if not q_tokens:
        return None, "miss"
    q_set = set(q_tokens)

    companies = [e for e in entities if (e.get("entity_type") or "").lower() == "company"]
    pool = companies or entities

    scored: list[tuple[int, int, dict, str]] = []
    for e in pool:
        n_tokens = normalize(e.get("name", "")).split()
        if not n_tokens:
            continue
        if n_tokens == q_tokens:
            score, strat = 0, "exact"
        elif len(n_tokens) < len(q_tokens) and q_tokens[: len(n_tokens)] == n_tokens:
            score, strat = 1 + (len(q_tokens) - len(n_tokens)), "prefix"
        elif len(n_tokens) > len(q_tokens) and n_tokens[: len(q_tokens)] == q_tokens:
            score, strat = 2 + (len(n_tokens) - len(q_tokens)), "prefix"
        else:
            overlap = len(set(n_tokens) & q_set)
            if overlap == 0:
                continue
            score, strat = 10 + (len(n_tokens) - overlap), "token"
        scored.append((score, len(n_tokens), e, strat))

    if not scored:
        return None, "miss"
    scored.sort(key=lambda x: (x[0], x[1]))
    best = scored[0]
    # Reject loose-token-only matches: they're almost always wrong companies.
    if best[0] >= 10:
        return None, "miss"
    return best[2], best[3]


def resolve_tickers(
    pairs: list[tuple[str, str]],
    client: CalaClient | None = None,
    throttle: float = SAFE_THROTTLE,
) -> list[TickerResolution]:
    client = client or CalaClient(throttle_seconds=throttle)
    # Ensure the shared client's throttle is honored even if caller passed one in.
    client.throttle_seconds = max(client.throttle_seconds, throttle)

    out: list[TickerResolution] = []
    for i, (ticker, name) in enumerate(pairs, 1):
        query = SEARCH_OVERRIDES.get(ticker, name)
        try:
            resp = client.entity_search(query, entity_types=["Company"], limit=20)
        except CalaError as e:
            log.warning("[%d/%d] %s '%s' -> Cala error %s", i, len(pairs), ticker, name, e.status)
            out.append(TickerResolution(ticker, name, None, None, "miss"))
            continue

        entities = resp.get("entities", [])
        hit, strategy = pick_best_company(query, entities)
        if hit:
            out.append(
                TickerResolution(
                    ticker=ticker,
                    name=name,
                    uuid=hit.get("id"),
                    match_name=hit.get("name"),
                    strategy=strategy,
                )
            )
            log.info(
                "[%3d/%3d] %-6s %-35s -> %s (%s)",
                i,
                len(pairs),
                ticker,
                name[:35],
                hit.get("name", "")[:40],
                strategy,
            )
        else:
            out.append(TickerResolution(ticker, name, None, None, "miss"))
            log.warning(
                "[%3d/%3d] %-6s %-35s -> MISS (%d candidates)",
                i,
                len(pairs),
                ticker,
                name[:35],
                len(entities),
            )
    return out


def save_resolutions(resolutions: list[TickerResolution]) -> None:
    hits = [r for r in resolutions if r.uuid]
    misses = [r for r in resolutions if not r.uuid]
    payload = {
        "count": len(resolutions),
        "hit_count": len(hits),
        "miss_count": len(misses),
        "resolved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "hits": [asdict(r) for r in hits],
        "misses": [asdict(r) for r in misses],
    }
    out = data_path("nasdaq100_uuids.json")
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    log.info("Saved %s — %d hits, %d misses", out, len(hits), len(misses))


def load_resolutions() -> dict[str, Any]:
    p = data_path("nasdaq100_uuids.json")
    return json.loads(p.read_text(encoding="utf-8"))
