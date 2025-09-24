CREATE TABLE IF NOT EXISTS trades_raw (
    vendor_trade_id VARCHAR,
    symbol VARCHAR,
    expiry DATE,
    strike DOUBLE,
    call_put VARCHAR,
    trade_ts_utc TIMESTAMP,
    price DOUBLE,
    size BIGINT,
    notional DOUBLE,
    raw_payload JSON,
    ingest_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (vendor_trade_id)
);

CREATE TABLE IF NOT EXISTS nbbo_at_trade (
    vendor_trade_id VARCHAR,
    bid DOUBLE,
    ask DOUBLE,
    mid DOUBLE,
    bid_size BIGINT,
    ask_size BIGINT,
    nbbo_ts TIMESTAMP,
    PRIMARY KEY (vendor_trade_id)
);

CREATE TABLE IF NOT EXISTS trades_labeled (
    vendor_trade_id VARCHAR,
    symbol VARCHAR,
    expiry DATE,
    strike DOUBLE,
    call_put VARCHAR,
    trade_ts_utc TIMESTAMP,
    price DOUBLE,
    size BIGINT,
    notional DOUBLE,
    premium DOUBLE,
    epsilon_used DOUBLE,
    side VARCHAR,
    is_0dte BOOLEAN,
    sweep_id VARCHAR,
    nbbo_bid DOUBLE,
    nbbo_ask DOUBLE,
    ingest_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (vendor_trade_id)
);

CREATE TABLE IF NOT EXISTS rollups_min (
    symbol VARCHAR,
    minute_bucket TIMESTAMP,
    total_premium DOUBLE,
    net_premium DOUBLE,
    call_premium DOUBLE,
    put_premium DOUBLE,
    buy_premium DOUBLE,
    sell_premium DOUBLE,
    zero_dte_premium DOUBLE,
    trades_count BIGINT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (symbol, minute_bucket)
);

CREATE TABLE IF NOT EXISTS open_interest_eod (
    symbol VARCHAR,
    expiry DATE,
    strike DOUBLE,
    call_put VARCHAR,
    date DATE,
    open_interest BIGINT,
    PRIMARY KEY (symbol, expiry, strike, call_put, date)
);
