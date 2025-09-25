from __future__ import annotations


from datetime import datetime, timezone
from io import StringIO
from threading import Lock
from time import monotonic
from typing import Any, Callable, Hashable

import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from option_flow.config.settings import Settings, get_settings
from option_flow.storage.repository import DuckDBRepository

app = FastAPI(title="Option Flow API", version="0.1.0")

REPO = DuckDBRepository()

WINDOW_OPTIONS: dict[str, int] = {"5m": 5, "15m": 15, "30m": 30, "60m": 60, "560m": 560}
CALL_PUT_FILTER = {"both", "calls", "puts"}


class TTLCache:
    def __init__(self, ttl_seconds: float):
        self._ttl = ttl_seconds
        self._store: dict[Hashable, tuple[Any, float]] = {}
        self._lock = Lock()

    def get(self, key: Hashable, loader: Callable[[], Any]) -> Any:
        now = monotonic()
        with self._lock:
            value = self._store.get(key)
            if value and now < value[1]:
                return value[0]
        result = loader()
        with self._lock:
            self._store[key] = (result, now + self._ttl)
        return result

    def clear(self) -> None:
        with self._lock:
            self._store.clear()


TABLE_CACHE = TTLCache(2.0)
PRINTS_CACHE = TTLCache(1.0)
TICKER_CACHE = TTLCache(2.0)


class TableRow(BaseModel):
    symbol: str
    net_premium: float
    total_premium: float
    call_premium: float
    put_premium: float
    zero_dte_percent: float
    top_strikes: list[str]


class PrintRow(BaseModel):
    trade_id: str
    trade_ts_utc: datetime
    symbol: str
    option: str
    price: float
    size: int
    notional: float
    side: str
    is_0dte: bool
    sweep_id: str | None


class MinuteBar(BaseModel):
    minute_bucket: datetime
    buy_premium: float
    sell_premium: float
    call_premium: float
    put_premium: float
    total_premium: float


class TickerDetail(BaseModel):
    symbol: str
    window_minutes: int
    by_minute: list[MinuteBar]
    largest_prints: list[PrintRow]
    top_strikes: list[str]


def get_valid_window(window: str) -> int:
    if window not in WINDOW_OPTIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported window '{window}'")
    return WINDOW_OPTIONS[window]


def parse_call_put_filter(value: str) -> str:
    if value not in CALL_PUT_FILTER:
        raise HTTPException(status_code=400, detail=f"Invalid put/call filter '{value}'")
    return value



def get_last_trade_timestamp() -> datetime | None:
    df = REPO.fetch_df("SELECT max(trade_ts_utc) AS last_trade FROM trades_labeled")
    if df.empty:
        return None
    value = df.iloc[0]["last_trade"]
    if pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    return value

def load_window_trades(minutes: int) -> pd.DataFrame:
    cutoff_expr = f"now() - INTERVAL {minutes} MINUTE"
    return REPO.fetch_df(
        f"""
        SELECT *
        FROM trades_labeled
        WHERE trade_ts_utc >= {cutoff_expr}
        """
    )


def summarize_symbols(df: pd.DataFrame) -> list[TableRow]:
    if df.empty:
        return []

    totals = df.groupby("symbol", as_index=False)["premium"].sum().rename(columns={"premium": "total_premium"})

    def metric(mask: pd.Series) -> pd.Series:
        return df[mask].groupby("symbol")["premium"].sum()

    call_premium = metric(df["call_put"] == "C")
    put_premium = metric(df["call_put"] == "P")
    buy_premium = metric(df["side"] == "BUY")
    sell_premium = metric(df["side"] == "SELL")
    zero_dte_premium = metric(df["is_0dte"])

    totals["call_premium"] = totals["symbol"].map(call_premium).fillna(0.0)
    totals["put_premium"] = totals["symbol"].map(put_premium).fillna(0.0)
    totals["buy_premium"] = totals["symbol"].map(buy_premium).fillna(0.0)
    totals["sell_premium"] = totals["symbol"].map(sell_premium).fillna(0.0)
    totals["zero_dte_premium"] = totals["symbol"].map(zero_dte_premium).fillna(0.0)
    totals["net_premium"] = totals["buy_premium"] - totals["sell_premium"]
    totals["zero_dte_percent"] = totals.apply(
        lambda row: (row["zero_dte_premium"] / row["total_premium"] * 100.0) if row["total_premium"] else 0.0,
        axis=1,
    )

    top_strikes_map: dict[str, list[str]] = {}
    grouped_strikes = df.groupby(["symbol", "expiry", "strike", "call_put"], as_index=False)["premium"].sum()
    for symbol, sub in grouped_strikes.groupby("symbol"):
        ordered = sub.sort_values("premium", ascending=False).head(3)
        top_strikes_map[symbol] = [
            f"{row['strike']:.2f}{row['call_put']} ({row['expiry']})"
            for _, row in ordered.iterrows()
        ]

    rows: list[TableRow] = []
    for _, row in totals.iterrows():
        symbol = row["symbol"]
        rows.append(
            TableRow(
                symbol=symbol,
                net_premium=float(row["net_premium"]),
                total_premium=float(row["total_premium"]),
                call_premium=float(row["call_premium"]),
                put_premium=float(row["put_premium"]),
                zero_dte_percent=float(row["zero_dte_percent"]),
                top_strikes=top_strikes_map.get(symbol, []),
            )
        )

    rows.sort(key=lambda r: abs(r.net_premium), reverse=True)
    return rows


def _load_top_flow(minutes: int, min_notional: float, call_put: str, zero_dte_only: bool) -> list[dict[str, Any]]:
    df = load_window_trades(minutes)
    if df.empty:
        return []
    if min_notional > 0:
        df = df[df["notional"] >= min_notional]
    if call_put != "both":
        df = df[df["call_put"] == ("C" if call_put == "calls" else "P")]
    if zero_dte_only:
        df = df[df["is_0dte"]]
    rows = summarize_symbols(df)
    return [row.model_dump() for row in rows]


def _load_prints(min_notional: float, limit: int) -> list[dict[str, Any]]:
    df = REPO.fetch_df(
        """
        SELECT *
        FROM trades_labeled
        WHERE notional >= ?
        ORDER BY trade_ts_utc DESC
        LIMIT ?
        """,
        [min_notional, limit],
    )
    if df.empty:
        return []
    return [
        {
            "trade_id": row["vendor_trade_id"],
            "trade_ts_utc": row["trade_ts_utc"],
            "symbol": row["symbol"],
            "option": f"{row['symbol']} {row['expiry']} {row['strike']:.2f}{row['call_put']}",
            "price": float(row["price"]),
            "size": int(row["size"]),
            "notional": float(row["notional"]),
            "side": row["side"],
            "is_0dte": bool(row["is_0dte"]),
            "sweep_id": row["sweep_id"] if row["sweep_id"] else None,
        }
        for _, row in df.iterrows()
    ]


def _load_ticker_detail(symbol: str, minutes: int) -> dict[str, Any]:
    cutoff_expr = f"now() - INTERVAL {minutes} MINUTE"
    df = REPO.fetch_df(
        """
        SELECT *
        FROM trades_labeled
        WHERE symbol = ? AND trade_ts_utc >= {cutoff_expr}
        """,
        [symbol],
    )
    if df.empty:
        detail = TickerDetail(symbol=symbol, window_minutes=minutes, by_minute=[], largest_prints=[], top_strikes=[])
        return detail.model_dump()

    df["minute_bucket"] = pd.to_datetime(df["trade_ts_utc"]).dt.floor("min")
    minute_totals = df.groupby("minute_bucket", as_index=True)["premium"].sum()

    def minute_metric(mask: pd.Series) -> pd.Series:
        return df[mask].groupby("minute_bucket")["premium"].sum()

    buy = minute_metric(df["side"] == "BUY").reindex(minute_totals.index, fillna(0.0))
    sell = minute_metric(df["side"] == "SELL").reindex(minute_totals.index, fillna(0.0))
    call = minute_metric(df["call_put"] == "C").reindex(minute_totals.index, fillna(0.0))
    put = minute_metric(df["call_put"] == "P").reindex(minute_totals.index, fillna(0.0))

    by_minute = [
        MinuteBar(
            minute_bucket=index.to_pydatetime(),
            buy_premium=float(buy.loc[index]),
            sell_premium=float(sell.loc[index]),
            call_premium=float(call.loc[index]),
            put_premium=float(put.loc[index]),
            total_premium=float(minute_totals.loc[index]),
        )
        for index in minute_totals.sort_index().index
    ]

    largest = (
        df.sort_values("notional", ascending=False)
        .head(10)
        .apply(
            lambda row: PrintRow(
                trade_id=row["vendor_trade_id"],
                trade_ts_utc=row["trade_ts_utc"],
                symbol=row["symbol"],
                option=f"{row['symbol']} {row['expiry']} {row['strike']:.2f}{row['call_put']}",
                price=float(row["price"]),
                size=int(row["size"]),
                notional=float(row["notional"]),
                side=row["side"],
                is_0dte=bool(row["is_0dte"]),
                sweep_id=row["sweep_id"] if row["sweep_id"] else None,
            ),
            axis=1,
        )
        .tolist()
    )

    strike_summary = (
        df.groupby(["strike", "expiry", "call_put"], as_index=False)["premium"].sum()
        .sort_values("premium", ascending=False)
        .head(5)
    )
    strikes = [
        f"{row['strike']:.2f}{row['call_put']} ({row['expiry']}): ${row['premium']:.0f}"
        for _, row in strike_summary.iterrows()
    ]

    detail = TickerDetail(
        symbol=symbol,
        window_minutes=minutes,
        by_minute=by_minute,
        largest_prints=largest,
        top_strikes=strikes,
    )
    return detail.model_dump()


@app.get("/health")
def health(settings: Settings = Depends(get_settings)) -> dict[str, Any]:
    last_trade = get_last_trade_timestamp()
    subscribed = list(settings.polygon_stream_symbols or [])
    return {
        "status": "ok",
        "demo_mode": settings.demo_mode,
        "ingest_enabled": not settings.demo_mode,
        "ingest_subscribed_symbols": subscribed,
        "last_trade_utc": last_trade.isoformat() if last_trade else None,
    }


@app.get("/top", response_model=list[TableRow])
def top_flow(
    window: str = Query("30m"),
    min_notional: float = Query(0.0, ge=0.0),
    call_put: str = Query("both"),
    zero_dte_only: bool = Query(False),
) -> list[TableRow]:
    minutes = get_valid_window(window)
    call_put = parse_call_put_filter(call_put)
    cache_key = (minutes, float(min_notional), call_put, bool(zero_dte_only))
    data = TABLE_CACHE.get(cache_key, lambda: _load_top_flow(minutes, min_notional, call_put, zero_dte_only))
    return [TableRow.model_validate(item) for item in data]


@app.get("/prints", response_model=list[PrintRow])
def prints_feed(
    min_notional: float = Query(250_000.0, ge=0.0),
    limit: int = Query(50, ge=1, le=500),
) -> list[PrintRow]:
    cache_key = (float(min_notional), int(limit))
    data = PRINTS_CACHE.get(cache_key, lambda: _load_prints(min_notional, limit))
    return [PrintRow.model_validate(item) for item in data]


@app.get("/ticker/{symbol}", response_model=TickerDetail)
def ticker_detail(
    symbol: str,
    window: str = Query("30m"),
) -> TickerDetail:
    symbol = symbol.upper()
    minutes = get_valid_window(window)
    cutoff_expr = f"now() - INTERVAL {minutes} MINUTE"
    df = query_df(
        f"""
        SELECT *
        FROM trades_labeled
        WHERE symbol = ? AND trade_ts_utc >= {cutoff_expr}
        """,
        [symbol],
    )

    if df.empty:
        return TickerDetail(symbol=symbol, window_minutes=minutes, by_minute=[], largest_prints=[], top_strikes=[])

    df["minute_bucket"] = pd.to_datetime(df["trade_ts_utc"]).dt.floor("min")
    minute_totals = df.groupby("minute_bucket", as_index=True)["premium"].sum()

    def minute_metric(mask: pd.Series) -> pd.Series:
        return df[mask].groupby("minute_bucket")["premium"].sum()

    buy = minute_metric(df["side"] == "BUY").reindex(minute_totals.index, fillna(0.0))
    sell = minute_metric(df["side"] == "SELL").reindex(minute_totals.index, fillna(0.0))
    call = minute_metric(df["call_put"] == "C").reindex(minute_totals.index, fillna(0.0))
    put = minute_metric(df["call_put"] == "P").reindex(minute_totals.index, fillna(0.0))

    by_minute = [
        MinuteBar(
            minute_bucket=index.to_pydatetime(),
            buy_premium=float(buy.loc[index]),
            sell_premium=float(sell.loc[index]),
            call_premium=float(call.loc[index]),
            put_premium=float(put.loc[index]),
            total_premium=float(minute_totals.loc[index]),
        )
        for index in minute_totals.sort_index().index
    ]

    largest = (
        df.sort_values("notional", ascending=False)
        .head(10)
        .apply(
            lambda row: PrintRow(
                trade_id=row["vendor_trade_id"],
                trade_ts_utc=row["trade_ts_utc"],
                symbol=row["symbol"],
                option=f"{row['symbol']} {row['expiry']} {row['strike']:.2f}{row['call_put']}",
                price=float(row["price"]),
                size=int(row["size"]),
                notional=float(row["notional"]),
                side=row["side"],
                is_0dte=bool(row["is_0dte"]),
                sweep_id=row["sweep_id"] if row["sweep_id"] else None,
            ),
            axis=1,
        )
        .tolist()
    )

    strike_summary = (
        df.groupby(["strike", "expiry", "call_put"], as_index=False)["premium"].sum()
        .sort_values("premium", ascending=False)
        .head(5)
    )
    strikes = [
        f"{row['strike']:.2f}{row['call_put']} ({row['expiry']}): ${row['premium']:.0f}"
        for _, row in strike_summary.iterrows()
    ]

    return TickerDetail(
        symbol=symbol,
        window_minutes=minutes,
        by_minute=by_minute,
        largest_prints=largest,
        top_strikes=strikes,
    )


@app.get("/export.csv")
def export_csv(
    window: str = Query("30m"),
    min_notional: float = Query(0.0, ge=0.0),
    call_put: str = Query("both"),
    zero_dte_only: bool = Query(False),
) -> StreamingResponse:
    rows = top_flow(window=window, min_notional=min_notional, call_put=call_put, zero_dte_only=zero_dte_only)
    df = pd.DataFrame([row.model_dump() for row in rows])
    if df.empty:
        df = pd.DataFrame(columns=["symbol", "net_premium", "total_premium", "call_premium", "put_premium", "zero_dte_percent", "top_strikes"])
    df["top_strikes"] = df["top_strikes"].apply(lambda values: ";".join(values))
    csv_io = StringIO()
    df.to_csv(csv_io, index=False)
    csv_io.seek(0)
    filename = f"option-flow-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.csv"
    headers = {"Content-Disposition": f"attachment; filename={filename}"}
    return StreamingResponse(iter([csv_io.getvalue()]), media_type="text/csv", headers=headers)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

