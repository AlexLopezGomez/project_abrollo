"""Thin REST wrapper around the Cala API.

Auth: `X-API-KEY` header. 429 is rate-limit-per-minute; we back off + retry once.
All other non-2xx errors raise `CalaError` with the status and payload attached.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

import requests

from abrollo.config import CALA_BASE_URL, require_cala_key

log = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 120.0
SLEEP_BETWEEN_CALLS = 0.15
BACKOFF_ON_429 = 10.0


class CalaError(RuntimeError):
    def __init__(self, status: int, body: Any, url: str):
        self.status = status
        self.body = body
        self.url = url
        super().__init__(f"Cala {status} on {url}: {str(body)[:200]}")


@dataclass
class CalaClient:
    api_key: str | None = None
    base_url: str = CALA_BASE_URL
    throttle_seconds: float = SLEEP_BETWEEN_CALLS

    def __post_init__(self) -> None:
        self.api_key = self.api_key or require_cala_key()
        self._session = requests.Session()
        self._session.headers.update(
            {
                "X-API-KEY": self.api_key,
                "Accept": "application/json",
                "User-Agent": "abrollo-mvp/0.0.1",
            }
        )
        self._last_call_at: float = 0.0

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_call_at
        if elapsed < self.throttle_seconds:
            time.sleep(self.throttle_seconds - elapsed)

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        retried_on_429: bool = False,
    ) -> Any:
        self._throttle()
        url = f"{self.base_url}{path}"
        resp = self._session.request(
            method,
            url,
            params=params,
            json=json_body,
            timeout=DEFAULT_TIMEOUT,
        )
        self._last_call_at = time.monotonic()

        if resp.status_code == 429 and not retried_on_429:
            log.warning("Cala 429 on %s — sleeping %.1fs and retrying once", path, BACKOFF_ON_429)
            time.sleep(BACKOFF_ON_429)
            return self._request(
                method, path, params=params, json_body=json_body, retried_on_429=True
            )

        if not resp.ok:
            try:
                body = resp.json()
            except Exception:
                body = resp.text
            raise CalaError(resp.status_code, body, url)

        try:
            return resp.json()
        except ValueError:
            return resp.text

    # --- Public API -----------------------------------------------------

    def entity_search(
        self, name: str, entity_types: list[str] | None = None, limit: int = 20
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"name": name, "limit": limit}
        if entity_types:
            params["entity_types"] = entity_types
        return self._request("GET", "/v1/entities", params=params)

    def entity_introspection(self, entity_id: str) -> dict[str, Any]:
        return self._request("GET", f"/v1/entities/{entity_id}/introspection")

    def retrieve_entity(
        self,
        entity_id: str,
        *,
        properties: list[str] | None = None,
        relationships: dict[str, Any] | None = None,
        numerical_observations: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {}
        if properties:
            body["properties"] = properties
        if relationships is not None:
            body["relationships"] = relationships
        if numerical_observations is not None:
            body["numerical_observations"] = numerical_observations
        return self._request("POST", f"/v1/entities/{entity_id}", json_body=body)

    def knowledge_query(self, input_str: str) -> dict[str, Any]:
        return self._request("POST", "/v1/knowledge/query", json_body={"input": input_str})

    def knowledge_search(self, input_str: str) -> dict[str, Any]:
        return self._request("POST", "/v1/knowledge/search", json_body={"input": input_str})

    def openapi(self) -> dict[str, Any]:
        return self._request("GET", "/openapi.json")
