from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import duckdb
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "optionflow.duckdb"
SCHEMA_PATH = BASE_DIR / "storage" / "schema.sql"
DEMO_PARQUET = DATA_DIR / "demo_trades.parquet"


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_schema() -> str:
    return SCHEMA_PATH.read_text(encoding="utf-8")


def apply_schema(con: duckdb.DuckDBPyConnection) -> None:
    schema_sql = load_schema()
    con.execute(schema_sql)


def compute_rollups(trades_df: pd.DataFrame) -> pd.DataFrame:
    enriched = trades_df.assign(
        minute_bucket=lambda df: df["trade_ts_utc"].dt.floor("min"),
        buy_premium=lambda df: df.apply(
            lambda row: row["premium"] if row["side"] == "BUY" else 0.0, axis=1
        ),
        sell_premium=lambda df: df.apply(
            lambda row: row["premium"] if row["side"] == "SELL" else 0.0, axis=1
        ),
        zero_dte_premium=lambda df: df.apply(
            lambda row: row["premium"] if row["is_0dte"] else 0.0, axis=1
        ),
        call_premium=lambda df: df.apply(
            lambda row: row["premium"] if row["call_put"] == "C" else 0.0, axis=1
        ),
        put_premium=lambda df: df.apply(
            lambda row: row["premium"] if row["call_put"] == "P" else 0.0, axis=1
        ),
    )
    grouped = (
        enriched.groupby(["symbol", "minute_bucket"], as_index=False)
        .agg(
            total_premium=("premium", "sum"),
            call_premium=("call_premium", "sum"),
            put_premium=("put_premium", "sum"),
            buy_premium=("buy_premium", "sum"),
            sell_premium=("sell_premium", "sum"),
            zero_dte_premium=("zero_dte_premium", "sum"),
            trades_count=("vendor_trade_id", "count"),
        )
    )
    grouped["net_premium"] = grouped["buy_premium"] - grouped["sell_premium"]
    grouped["updated_at"] = datetime.now(timezone.utc)
    return grouped[
        [
            "symbol",
            "minute_bucket",
            "total_premium",
            "net_premium",
            "call_premium",
            "put_premium",
            "buy_premium",
            "sell_premium",
            "zero_dte_premium",
            "trades_count",
            "updated_at",
        ]
    ]


def seed_demo(con: duckdb.DuckDBPyConnection) -> None:
    start = datetime.now(timezone.utc) - timedelta(minutes=30)
    symbols = ["SPY", "QQQ", "AAPL"]
    records: list[dict[str, object]] = []
    nbbo_records: list[dict[str, object]] = []

    trade_id = 1
    for symbol in symbols:
        for minute in range(30):
            ts = start + timedelta(minutes=minute)
            expiry = (ts + timedelta(days=7)).date()
            strike = 400.0 + minute if symbol == "SPY" else 450.0 + minute
            call_put = "C" if minute % 2 == 0 else "P"
            price = 1.5 + (minute % 5) * 0.1
            size = 50 + (minute % 3) * 10
            notional = price * size * 100
            side = "BUY" if minute % 2 == 0 else "SELL"
            epsilon = max(0.01, 0.05 * 0.5)
            nbbo_bid = price - 0.05
            nbbo_ask = price + 0.05
            records.append(
                {
                    "vendor_trade_id": f"demo-{trade_id}",
                    "symbol": symbol,
                    "expiry": expiry,
                    "strike": strike,
                    "call_put": call_put,
                    "trade_ts_utc": ts,
                    "price": price,
                    "size": size,
                    "notional": notional,
                    "premium": notional,
                    "epsilon_used": epsilon,
                    "side": side,
                    "is_0dte": False,
                    "sweep_id": None,
                    "nbbo_bid": nbbo_bid,
                    "nbbo_ask": nbbo_ask,
                    "raw_payload": json.dumps(
                        {"symbol": symbol, "price": price, "size": size}
                    ),
                }
            )
            nbbo_records.append(
                {
                    "vendor_trade_id": f"demo-{trade_id}",
                    "bid": nbbo_bid,
                    "ask": nbbo_ask,
                    "mid": (nbbo_bid + nbbo_ask) / 2,
                    "bid_size": size + 20,
                    "ask_size": size + 20,
                    "nbbo_ts": ts,
                }
            )
            trade_id += 1

    trades_df = pd.DataFrame(records)
    trades_df["trade_ts_utc"] = pd.to_datetime(trades_df["trade_ts_utc"])
    nbbo_df = pd.DataFrame(nbbo_records)
    nbbo_df["nbbo_ts"] = pd.to_datetime(nbbo_df["nbbo_ts"])

    raw_df = trades_df[
        [
            "vendor_trade_id",
            "symbol",
            "expiry",
            "strike",
            "call_put",
            "trade_ts_utc",
            "price",
            "size",
            "notional",
            "raw_payload",
        ]
    ].copy()

    rollup_df = compute_rollups(trades_df)

    con.register("raw_df", raw_df)
    con.register("trades_df", trades_df)
    con.register("nbbo_df", nbbo_df)
    con.register("rollup_df", rollup_df)

    con.execute("DELETE FROM trades_raw")
    con.execute("DELETE FROM trades_labeled")
    con.execute("DELETE FROM nbbo_at_trade")
    con.execute("DELETE FROM rollups_min")

    con.execute("""\n        INSERT INTO trades_raw (\n            vendor_trade_id, symbol, expiry, strike, call_put, trade_ts_utc,\n            price, size, notional, raw_payload\n        )\n        SELECT\n            vendor_trade_id, symbol, expiry, strike, call_put, trade_ts_utc,\n            price, size, notional, raw_payload\n        FROM raw_df\n        """)
    con.execute(
        """
        INSERT INTO trades_labeled (
            vendor_trade_id, symbol, expiry, strike, call_put, trade_ts_utc,
            price, size, notional, premium, epsilon_used, side, is_0dte,
            sweep_id, nbbo_bid, nbbo_ask
        )
        SELECT
            vendor_trade_id, symbol, expiry, strike, call_put, trade_ts_utc,
            price, size, notional, premium, epsilon_used, side, is_0dte,
            sweep_id, nbbo_bid, nbbo_ask
        FROM trades_df
        """
    )
    con.execute("INSERT INTO nbbo_at_trade SELECT * FROM nbbo_df")
    con.execute(
        """
        INSERT INTO rollups_min (
            symbol, minute_bucket, total_premium, net_premium, call_premium,
            put_premium, buy_premium, sell_premium, zero_dte_premium, trades_count, updated_at
        )
        SELECT symbol, minute_bucket, total_premium, net_premium, call_premium,
               put_premium, buy_premium, sell_premium, zero_dte_premium, trades_count, updated_at
        FROM rollup_df
        """
    )

    trades_df.to_parquet(DEMO_PARQUET, index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize DuckDB schema and optional demo data")
    parser.add_argument("--demo", action="store_true", help="Load recorded demo dataset")
    args = parser.parse_args()

    ensure_dirs()
    con = duckdb.connect(str(DB_PATH))
    apply_schema(con)

    if args.demo:
        seed_demo(con)
        print(f"Demo data loaded into {DB_PATH} and {DEMO_PARQUET} created")
    else:
        print(f"Schema applied at {DB_PATH}")

    con.close()


if __name__ == "__main__":
    main()

