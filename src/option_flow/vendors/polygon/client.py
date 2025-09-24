from __future__ import annotations

import json
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from datetime import date
from typing import Any, Literal

import httpx
import websockets

from option_flow.config.settings import get_settings

OPTION_TYPE = Literal["C", "P"]


@dataclass
class OptionContract:
    underlying: str
    expiry: date
    strike: float
    option_type: OPTION_TYPE


def parse_option_symbol(symbol: str) -> OptionContract:
    """Parse Polygon OCC-style option symbol, e.g. O:SPY240920C00460000."""

    if not symbol.startswith("O:"):
        raise ValueError(f"invalid Polygon option symbol: {symbol}")

    body = symbol[2:]
    idx = 0
    while idx < len(body) and body[idx].isalpha():
        idx += 1
    if idx == 0:
        raise ValueError(f"missing underlying in option symbol: {symbol}")

    underlying = body[:idx]
    if len(body) - idx < 7:
        raise ValueError(f"option identifier too short: {symbol}")

    expiry_raw = body[idx : idx + 6]
    option_type = body[idx + 6].upper()
    if option_type not in ("C", "P"):
        raise ValueError(f"unknown option type '{option_type}' in symbol {symbol}")

    strike_raw = body[idx + 7 :]
    if not strike_raw.isdigit():
        raise ValueError(f"invalid strike in symbol {symbol}")

    year = 2000 + int(expiry_raw[0:2])
    month = int(expiry_raw[2:4])
    day = int(expiry_raw[4:6])
    expiry = date(year, month, day)
    strike = int(strike_raw) / 1000.0

    return OptionContract(
        underlying=underlying,
        expiry=expiry,
        strike=strike,
        option_type=option_type,  # type: ignore[arg-type]
    )


class PolygonClient:
    """Thin wrapper around Polygon.io streaming and REST APIs."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        ws_url: str | None = None,
        rest_base_url: str | None = None,
        session_factory: Callable[[], httpx.AsyncClient] | None = None,
    ) -> None:
        settings = get_settings()
        self._api_key = api_key or getattr(settings, "polygon_api_key", None)
        self._ws_url = ws_url or settings.polygon_ws_url
        self._rest_base_url = rest_base_url or settings.polygon_rest_base_url
        self._session_factory = session_factory or (lambda: httpx.AsyncClient(timeout=10.0))

    async def stream_trades(self, symbols: list[str]) -> AsyncIterator[dict[str, Any]]:
        """Yield Polygon trade/quote messages for the provided option symbols."""

        if not self._api_key:
            raise RuntimeError("Polygon API key not configured")

        channel_params = self._build_channel_params(symbols)
        async with websockets.connect(self._ws_url, ping_interval=20, ping_timeout=20) as ws:
            await ws.send(json.dumps({"action": "auth", "params": self._api_key}))
            await ws.send(json.dumps({"action": "subscribe", "params": channel_params}))

            async for message in ws:
                payload = json.loads(message)
                yield payload

    def _build_channel_params(self, symbols: list[str]) -> str:
        if not symbols:
            return "T.O.*,Q.O.*"
        params: list[str] = []
        for symbol in symbols:
            params.append(f"T.O.{symbol}")
            params.append(f"Q.O.{symbol}")
        return ",".join(params)

    async def fetch_open_interest(self, underlying: str, *, as_of: date) -> list[dict[str, Any]]:
        """Fetch daily open interest snapshot for an underlying."""

        if not self._api_key:
            raise RuntimeError("Polygon API key not configured")

        endpoint = f"{self._rest_base_url}/v3/reference/options/contracts"
        params = {
            "underlying_ticker": underlying,
            "as_of": as_of.isoformat(),
            "apiKey": self._api_key,
        }
        async with self._session_factory() as session:
            response = await session.get(endpoint, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])


__all__ = ["PolygonClient", "OptionContract", "parse_option_symbol"]
