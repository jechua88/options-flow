from __future__ import annotations

import asyncio
import json
import logging
import random
from datetime import datetime, timezone
from typing import Any, Iterable, Sequence

import duckdb

from option_flow.config.settings import get_settings
from option_flow.ingest.nbbo_cache import NBBOCache
from option_flow.services.side_classifier import infer_side
from option_flow.services.sweep_cluster import SweepClusterer
from option_flow.storage.duckdb_client import get_connection
from option_flow.vendors import PolygonClient, parse_option_symbol

LOGGER = logging.getLogger(__name__)
CONTRACT_MULTIPLIER = 100


class DuckDBWriter:
    """Persist trade and quote context rows into DuckDB."""

    _RAW_SQL = (
        "INSERT INTO trades_raw (vendor_trade_id, symbol, expiry, strike, call_put, "
        "trade_ts_utc, price, size, notional, raw_payload) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    )
    _LABELED_SQL = (
        "INSERT INTO trades_labeled (vendor_trade_id, symbol, expiry, strike, call_put, "
        "trade_ts_utc, price, size, notional, premium, epsilon_used, side, is_0dte, "
        "sweep_id, nbbo_bid, nbbo_ask) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    )
    _NBBO_SQL = (
        "INSERT INTO nbbo_at_trade (vendor_trade_id, bid, ask, mid, bid_size, ask_size, nbbo_ts) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)"
    )

    def insert_trade(
        self,
        raw_params: Sequence[Any],
        labeled_params: Sequence[Any],
        nbbo_params: Sequence[Any] | None,
    ) -> bool:
        with get_connection(read_only=False) as con:
            try:
                con.execute(self._RAW_SQL, tuple(raw_params))
            except duckdb.ConstraintException:
                return False
            con.execute(self._LABELED_SQL, tuple(labeled_params))
            if nbbo_params is not None:
                con.execute(self._NBBO_SQL, tuple(nbbo_params))
        return True


class TradeEventProcessor:
    """Transforms Polygon events into persistence-friendly rows."""

    def __init__(
        self,
        *,
        allowed_underlyings: Iterable[str] | None = None,
        nbbo_cache: NBBOCache | None = None,
        sweep_clusterer: SweepClusterer | None = None,
        writer: DuckDBWriter | None = None,
        contract_multiplier: int = CONTRACT_MULTIPLIER,
    ) -> None:
        self._allowed_underlyings = (
            {symbol.upper() for symbol in allowed_underlyings}
            if allowed_underlyings
            else None
        )
        self._nbbo_cache = nbbo_cache or NBBOCache()
        self._sweeps = sweep_clusterer or SweepClusterer()
        self._writer = writer or DuckDBWriter()
        self._contract_multiplier = contract_multiplier
        self._log = logging.getLogger(__name__)

    def process_quote(self, event: dict[str, Any]) -> None:
        symbol = event.get("sym")
        if not symbol:
            return
        bid = event.get("bp")
        ask = event.get("ap")
        timestamp_ms = event.get("t")
        if bid is None or ask is None or timestamp_ms is None:
            return
        try:
            bid_f = float(bid)
            ask_f = float(ask)
            timestamp = datetime.fromtimestamp(int(timestamp_ms) / 1000.0, tz=timezone.utc)
        except (TypeError, ValueError, OverflowError):
            return
        bid_size_raw = event.get("bs")
        ask_size_raw = event.get("as")
        bid_size = int(bid_size_raw) if isinstance(bid_size_raw, (int, float)) else None
        ask_size = int(ask_size_raw) if isinstance(ask_size_raw, (int, float)) else None
        self._nbbo_cache.upsert(
            symbol,
            bid_f,
            ask_f,
            timestamp,
            bid_size=bid_size,
            ask_size=ask_size,
        )
        self._nbbo_cache.bulk_expire(now=timestamp)

    def process_trade(self, event: dict[str, Any]) -> bool:
        symbol = event.get("sym")
        if not symbol:
            return False
        try:
            contract = parse_option_symbol(symbol)
        except ValueError:
            self._log.debug("Skipping trade with unknown symbol %s", symbol)
            return False

        underlying = contract.underlying.upper()
        if self._allowed_underlyings and underlying not in self._allowed_underlyings:
            return False

        price = event.get("p")
        size = event.get("s")
        timestamp_ms = event.get("t")
        if price is None or size is None or timestamp_ms is None:
            return False
        try:
            price_f = float(price)
            size_i = int(size)
            timestamp = datetime.fromtimestamp(int(timestamp_ms) / 1000.0, tz=timezone.utc)
        except (TypeError, ValueError, OverflowError):
            self._log.debug("Skipping trade with invalid numeric fields: %s", event)
            return False
        if price_f <= 0 or size_i <= 0:
            return False

        self._nbbo_cache.bulk_expire(now=timestamp)
        quote = self._nbbo_cache.get(symbol, now=timestamp)
        side_result = infer_side(price_f, quote)
        sweep_id = self._sweeps.assign(symbol, side_result.side, timestamp)

        vendor_trade_id = self._build_trade_id(event, symbol, timestamp_ms)
        notional = price_f * size_i * self._contract_multiplier
        raw_payload = json.dumps(event, separators=(",", ":"), sort_keys=True)
        nbbo_bid = float(quote.bid) if quote else None
        nbbo_ask = float(quote.ask) if quote else None

        raw_params = (
            vendor_trade_id,
            underlying,
            contract.expiry,
            float(contract.strike),
            contract.option_type,
            timestamp,
            price_f,
            size_i,
            notional,
            raw_payload,
        )
        labeled_params = (
            vendor_trade_id,
            underlying,
            contract.expiry,
            float(contract.strike),
            contract.option_type,
            timestamp,
            price_f,
            size_i,
            notional,
            notional,
            float(side_result.epsilon),
            side_result.side,
            timestamp.date() == contract.expiry,
            sweep_id,
            nbbo_bid,
            nbbo_ask,
        )
        nbbo_params = None
        if quote:
            nbbo_params = (
                vendor_trade_id,
                float(quote.bid),
                float(quote.ask),
                float(quote.mid),
                quote.bid_size,
                quote.ask_size,
                quote.timestamp,
            )
        try:
            return self._writer.insert_trade(raw_params, labeled_params, nbbo_params)
        except duckdb.Error:
            self._log.exception("Failed to persist trade event: %s", event)
            return False

    def _build_trade_id(self, event: dict[str, Any], symbol: str, timestamp_ms: Any) -> str:
        trade_id = event.get("i") or event.get("id")
        if trade_id is not None:
            return str(trade_id)
        sequence = event.get("q") or event.get("seq") or event.get("sequence") or 0
        return f"{symbol}-{timestamp_ms}-{sequence}"


class LiveTradeService:
    """Manage the Polygon WebSocket lifecycle and delegate processing."""

    def __init__(
        self,
        *,
        polygon_client: PolygonClient | None = None,
        processor: TradeEventProcessor | None = None,
        symbols: Sequence[str] | None = None,
        reconnect_delay_seconds: int = 5,
        max_reconnect_delay_seconds: int = 60,
    ) -> None:
        settings = get_settings()
        allowed = set(settings.default_symbols)
        self._client = polygon_client or PolygonClient()
        self._processor = processor or TradeEventProcessor(allowed_underlyings=allowed)
        configured_symbols = symbols if symbols is not None else settings.polygon_stream_symbols
        self._symbols = list(configured_symbols) if configured_symbols else []
        self._base_reconnect_delay = float(reconnect_delay_seconds)
        self._max_reconnect_delay = max(float(max_reconnect_delay_seconds), self._base_reconnect_delay)
        self._log = logging.getLogger(__name__)
        if self._symbols:
            self._log.info("Subscribing to Polygon symbols: %s", ", ".join(self._symbols))
        else:
            self._log.info("Subscribing to all option symbols via wildcard")

    async def run(self) -> None:
        delay = self._base_reconnect_delay
        while True:
            try:
                async for payload in self._client.stream_trades(self._symbols):
                    await self._handle_payload(payload)
                    delay = self._base_reconnect_delay
            except asyncio.CancelledError:
                raise
            except Exception:
                jitter = random.uniform(0.8, 1.2)
                sleep_for = min(delay * jitter, self._max_reconnect_delay)
                self._log.exception(
                    "Polygon stream error; retrying in %.1f seconds",
                    sleep_for,
                )
                await asyncio.sleep(sleep_for)
                delay = min(max(self._base_reconnect_delay, delay * 2), self._max_reconnect_delay)
            else:
                delay = self._base_reconnect_delay

    async def _handle_payload(self, payload: Any) -> None:
        events = payload if isinstance(payload, list) else [payload]
        for event in events:
            if not isinstance(event, dict):
                continue
            event_type = event.get("ev")
            if event_type == "Q":
                self._processor.process_quote(event)
            elif event_type == "T":
                await asyncio.to_thread(self._processor.process_trade, event)
            elif event_type == "status":
                self._log.debug("Polygon status update: %s", event)
            else:
                self._log.debug("Unhandled Polygon event: %s", event)


__all__ = ["DuckDBWriter", "TradeEventProcessor", "LiveTradeService"]
