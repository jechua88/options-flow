from __future__ import annotations

import httpx
from typing import Any, Mapping


class APIClient:
    def __init__(self, base_url: str, *, timeout: float = 5.0) -> None:
        self._base_url = base_url.rstrip('/')
        self._client = httpx.Client(timeout=timeout)

    def json(self, path: str, params: Mapping[str, Any] | None = None) -> Any:
        response = self._client.get(self._url(path), params=params)
        response.raise_for_status()
        return response.json()

    def bytes(self, path: str, params: Mapping[str, Any] | None = None) -> bytes:
        response = self._client.get(self._url(path), params=params)
        response.raise_for_status()
        return response.content

    def close(self) -> None:
        self._client.close()

    def _url(self, path: str) -> str:
        if path.startswith('http'):
            return path
        if not path.startswith('/'):
            path = '/' + path
        return f"{self._base_url}{path}"


__all__ = ["APIClient"]
