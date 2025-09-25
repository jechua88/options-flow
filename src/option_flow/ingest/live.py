from __future__ import annotations

import asyncio
import json
import logging
import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, List, Sequence

import duckdb
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from option_flow.config.settings import get_settings
from option_flow.ingest.nbbo_cache import NBBOCache
from option_flow.services.side_classifier import infer_side
from option_flow.services.sweep_cluster import SweepClusterer
from option_flow.storage.duckdb_client import get_connection
from option_flow.vendors import PolygonClient, parse_option_symbol

LOGGER = logging.getLogger(__name__)
CONTRACT_MULTIPLIER = 100


class PolygonTrade(BaseModel):
    ev: str
    sym: str
    p: float
    s: int
    t: int
    i: str | None = None
    q: int | None = Field(default=None, alias="q")
    seq: int | None = Field(default=None, alias="seq")

    model_config = ConfigDict(extra="allow")


class PolygonQuote(BaseModel):
    ev: str
    sym: str
    bp: float
    ap: float
    t: int
    bid_size: int | None = Field(default=None, alias="bs")
    ask_size: int | None = Field(default=None, alias="as")

    model_config = ConfigDict(extra="allow")


@dataclass(slots=True)
class PersistPayload:
    raw: Sequence[Any]
    labeled: Sequence[Any]
    nbbo: Sequence[Any] | None


class DuckDBWriter:
    """Persist trade and quote context rows into DuckDB."""

    _RAW_SQL = (
        "INSERT OR IGNORE INTO trades_raw (vendor_trade_id, symbol, expiry, strike, call_put, "
        "trade_ts_utc, price, size, notional, raw_payload) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    )
    _LABELED_SQL = (
        "INSERT OR REPLACE INTO trades_labeled (vendor_trade_id, symbol, expiry, strike, call_put, "
        "trade_ts_utc, price, size, notional, premium, epsilon_used, side, is_0dte, "
        "sweep_id, nbbo_bid, nbbo_ask) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    )
    _NBBO_SQL = (
        "INSERT OR REPLACE INTO nbbo_at_trade (vendor_trade_id, bid, ask, mid, bid_size, ask_size, nbbo_ts) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)"
    )

    def insert_batch(self, payloads: Sequence[PersistPayload]) -> None:
        if not payloads:
            return
        with get_connection(read_only=False) as con:
            raw_rows = [payload.raw for payload in payloads]
            labeled_rows = [payload.labeled for payload in payloads]
            nbbo_rows = [payload.nbbo for payload in payloads if payload.nbbo is not None]
            con.executemany(self._RAW_SQL, raw_rows)
            con.executemany(self._LABELED_SQL, labeled_rows)
            if nbbo_rows:
                con.executemany(self._NBBO_SQL, nbbo_rows)


class TradeEventProcessor:
    """Transforms Polygon events into persistence-friendly rows."""

    def __init__(
        self,
        *,
        allowed_underlyings: Iterable[str] | None = None,
        nbbo_cache: NBBOCache | None = None,
        sweep_clusterer: SweepClusterer | None = None,
        contract_multiplier: int = CONTRACT_MULTIPLIER,
    ) -> None:
        self._allowed_underlyings = (
            {symbol.upper() for symbol in allowed_underlyings}
            if allowed_underlyings
            else None
        )
        self._nbbo_cache = nbbo_cache or NBBOCache()
        self._sweeps = sweep_clusterer or SweepClusterer()
        self._contract_multiplier = contract_multiplier
        self._log = logging.getLogger(__name__)

    def process_quote(self, event: dict[str, Any]) -> None:
        try:
            quote = PolygonQuote.model_validate(event)
        except ValidationError:
            self._log.debug("Invalid quote payload skipped: %s", event)
            return
        symbol = quote.sym
        bid = float(quote.bp)
        ask = float(quote.ap)
        timestamp = datetime.fromtimestamp(int(quote.t) / 1000.0, tz=timezone.utc)
        bid_size = int(quote.bid_size) if isinstance(quote.bid_size, (int, float)) else None
        ask_size = int(quote.ask_size) if isinstance(quote.ask_size, (int, float)) else None
        self._nbbo_cache.upsert(
            symbol,
            bid,
            ask,
            timestamp,
            bid_size=bid_size,
            ask_size=ask_size,
        )
        self._nbbo_cache.bulk_expire(now=timestamp)

    def process_trade(self, event: dict[str, Any]) -> PersistPayload | None:
        try:
            trade = PolygonTrade.model_validate(event)
        except ValidationError:
            self._log.debug("Invalid trade payload skipped: %s", event)
            return None
        symbol = trade.sym
        if not symbol:
            return None
        try:
            contract = parse_option_symbol(symbol)
        except ValueError:
            self._log.debug("Skipping trade with unknown symbol %s", symbol)
            return None

        underlying = contract.underlying.upper()
        if self._allowed_underlyings and underlying not in self._allowed_underlyings:
            return None

        price_f = float(trade.p)
        size_i = int(trade.s)
        if price_f <= 0 or size_i <= 0:
            return None
        timestamp = datetime.fromtimestamp(int(trade.t) / 1000.0, tz=timezone.utc)
        self._nbbo_cache.bulk_expire(now=timestamp)
        quote = self._nbbo_cache.get(symbol, now=timestamp)
        side_result = infer_side(price_f, quote)
        sweep_id = self._sweeps.assign(symbol, side_result.side, timestamp)

        vendor_trade_id = self._build_trade_id(trade, symbol)
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
        return PersistPayload(raw=raw_params, labeled=labeled_params, nbbo=nbbo_params)

    def _build_trade_id(self, trade: PolygonTrade, symbol: str) -> str:
        if trade.i is not None:
            return str(trade.i)
        sequence = trade.q or trade.seq or 0
        return f"{symbol}-{trade.t}-{sequence}"


class BatchWriter:
    def __init__(self, writer: DuckDBWriter, *, max_batch_size: int = 200, flush_interval: float = 1.0) -> None:
        self._writer = writer
        self._max_batch_size = max_batch_size
        self._flush_interval = flush_interval
        self._pending: List[PersistPayload] = []
        self._lock = asyncio.Lock()
        self._last_flush = time.monotonic()

    async def add(self, payload: PersistPayload) -> None:
        async with self._lock:
            self._pending.append(payload)
            if len(self._pending) >= self._max_batch_size or (time.monotonic() - self._last_flush) >= self._flush_interval:
                await self._flush_locked()

    async def flush(self) -> None:
        async with self._lock:
            await self._flush_locked()

    async def _flush_locked(self) -> None:
        if not self._pending:
            return
        batch = list(self._pending)
        self._pending.clear()
        self._last_flush = time.monotonic()
        await asyncio.to_thread(self._writer.insert_batch, batch)


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
        max_batch_size: int = 200,
        flush_interval: float = 1.0,
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
        self._batch_writer = BatchWriter(DuckDBWriter(), max_batch_size=max_batch_size, flush_interval=flush_interval)
        if self._symbols:
            self._log.info("Subscribing to Polygon symbols: %s", ", ".join(self._symbols))
        else:
            self._log.info("Subscribing to all option symbols via wildcard")

    async def run(self) -> None:
        delay = self._base_reconnect_delay
        try:
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
        finally:
            await self._batch_writer.flush()

    async def _handle_payload(self, payload: Any) -> None:
        events = payload if isinstance(payload, list) else [payload]
        trades: List[PersistPayload] = []
        for event in events:
            if not isinstance(event, dict):
                continue
            event_type = event.get("ev")
            if event_type == "Q":
                self._processor.process_quote(event)
            elif event_type == "T":
                result = self._processor.process_trade(event)
                if result is not None:
                    trades.append(result)
            elif event_type == "status":
                self._log.debug("Polygon status update: %s", event)
            else:
                self._log.debug("Unhandled Polygon event: %s", event)
        for trade in trades:
            await self._batch_writer.add(trade)


__all__ = ["DuckDBWriter", "TradeEventProcessor", "LiveTradeService", "BatchWriter", "PersistPayload"]
