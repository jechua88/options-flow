from __future__ import annotations

from datetime import datetime, timedelta, timezone

import duckdb
import pytest

from option_flow.config import settings
pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("integration_db")]

from option_flow.ingest.live import DuckDBWriter, TradeEventProcessor


def _connect_db() -> duckdb.DuckDBPyConnection:
    db_path = settings.get_settings().duckdb_path
    return duckdb.connect(str(db_path))


def test_process_trade_inserts_rows():
    processor = TradeEventProcessor(allowed_underlyings={"SPY"})
    writer = DuckDBWriter()

    quote_ts = datetime(2025, 1, 16, 14, 0, tzinfo=timezone.utc)
    quote_event = {
        "ev": "Q",
        "sym": "O:SPY250117C00500000",
        "bp": 1.5,
        "ap": 1.6,
        "bs": 25,
        "as": 30,
        "t": int(quote_ts.timestamp() * 1000),
    }
    processor.process_quote(quote_event)

    trade_ts = quote_ts + timedelta(seconds=10)
    trade_event = {
        "ev": "T",
        "sym": "O:SPY250117C00500000",
        "p": 1.6,
        "s": 10,
        "i": "abc-123",
        "t": int(trade_ts.timestamp() * 1000),
    }

    payload = processor.process_trade(trade_event)
    assert payload is not None
    writer.insert_batch([payload])

    con = _connect_db()
    raw_row = con.execute(
        "SELECT symbol, price, size, notional FROM trades_raw WHERE vendor_trade_id = ?",
        ["abc-123"],
    ).fetchone()
    assert raw_row is not None
    assert raw_row[0] == "SPY"
    assert raw_row[1] == pytest.approx(1.6)
    assert raw_row[2] == 10
    assert raw_row[3] == pytest.approx(1.6 * 10 * 100)

    labeled_row = con.execute(
        "SELECT side, epsilon_used, nbbo_bid, nbbo_ask, is_0dte, sweep_id FROM trades_labeled WHERE vendor_trade_id = ?",
        ["abc-123"],
    ).fetchone()
    assert labeled_row is not None
    assert labeled_row[0] == "BUY"
    assert labeled_row[1] == pytest.approx(0.01)
    assert labeled_row[2] == pytest.approx(1.5)
    assert labeled_row[3] == pytest.approx(1.6)
    assert labeled_row[4] is False
    assert labeled_row[5]

    nbbo_row = con.execute(
        "SELECT bid, ask, mid, bid_size, ask_size FROM nbbo_at_trade WHERE vendor_trade_id = ?",
        ["abc-123"],
    ).fetchone()
    assert nbbo_row is not None
    assert nbbo_row[0] == pytest.approx(1.5)
    assert nbbo_row[1] == pytest.approx(1.6)
    assert nbbo_row[2] == pytest.approx((1.5 + 1.6) / 2)
    assert nbbo_row[3] == 25
    assert nbbo_row[4] == 30
    con.close()


def test_duplicate_trade_ignored():
    processor = TradeEventProcessor(allowed_underlyings={"SPY"})
    writer = DuckDBWriter()
    trade_ts = datetime(2025, 1, 16, 15, 0, tzinfo=timezone.utc)
    trade_event = {
        "ev": "T",
        "sym": "O:SPY250117P00450000",
        "p": 2.1,
        "s": 20,
        "i": "dup-1",
        "t": int(trade_ts.timestamp() * 1000),
    }

    con = _connect_db()
    initial_count = con.execute("SELECT COUNT(*) FROM trades_raw").fetchone()[0]
    con.close()

    payload = processor.process_trade(trade_event)
    assert payload is not None
    writer.insert_batch([payload])

    con = _connect_db()
    after_first = con.execute("SELECT COUNT(*) FROM trades_raw").fetchone()[0]
    assert after_first == initial_count + 1
    con.close()

    payload_dup = processor.process_trade(trade_event)
    assert payload_dup is not None
    writer.insert_batch([payload_dup])

    con = _connect_db()
    after_second = con.execute("SELECT COUNT(*) FROM trades_raw").fetchone()[0]
    assert after_second == initial_count + 1
    con.close()
