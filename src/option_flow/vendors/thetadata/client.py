from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from typing import Any

import httpx

from option_flow.config.settings import get_settings


class ThetaDataClient:
    """Stubbed ThetaData client with pluggable HTTP session factory."""

    def __init__(self, *, session_factory: Callable[[], httpx.AsyncClient] | None = None) -> None:
        self._settings = get_settings()
        self._session_factory = session_factory or (lambda: httpx.AsyncClient(timeout=10.0))

    async def stream_trades(self, symbols: list[str]) -> AsyncIterator[dict[str, Any]]:
        """Yield trade messages for the provided symbols (stubbed)."""

        del symbols  # placeholder until real integration
        await asyncio.sleep(0)
        if False:
            yield {}

    async def fetch_nbbo_snapshot(self, contract: str) -> dict[str, Any] | None:
        del contract
        async with self._session_factory() as session:
            del session
        return None

    async def fetch_open_interest(self, date: str) -> list[dict[str, Any]]:
        del date
        async with self._session_factory() as session:
            del session
        return []


__all__ = ["ThetaDataClient"]
