# Architecture Overview

## High-Level Components
- **Ingest** — `option_flow.ingest.worker` orchestrates rollups and the live Polygon stream. The worker pulls option trades/quotes over WebSocket, enriches them, and persists into DuckDB.
- **Storage** — DuckDB holds raw trades, labeled trades, NBBO snapshots, and rollups. `option_flow.storage.repository.DuckDBRepository` provides a thin query layer for API consumers.
- **API** — FastAPI (`option_flow.api.main`) exposes `/top`, `/prints`, `/ticker/{symbol}`, and `/health`. These endpoints power both the Streamlit UI and any external consumers.
- **UI** — Streamlit dashboard (`option_flow.ui.app`) visualises aggregates, prints, and ticker drill-downs. A shared `APIClient` handles HTTP calls to the FastAPI service.
- **Launchers** — CLI/desktop launchers start API, UI, and ingest processes together, making it easy to run locally or in Docker.

## Ingest Flow
1. **Polygon WebSocket** — `LiveTradeService` subscribes to Polygon trade/quote channels (filtered via `OPTION_FLOW_POLYGON_STREAM_SYMBOLS`).
2. **Validation** — Incoming payloads are parsed via pydantic models to ensure schema correctness before enrichment.
3. **Enrichment** — `TradeEventProcessor` looks up cached NBBO, infers buy/sell side, assigns sweep IDs, and emits persistence payloads.
4. **Batch Persistence** — `BatchWriter` batches trades and writes to DuckDB using `DuckDBWriter.insert_batch`, reducing commit overhead.
5. **Rollups** — A background coroutine refreshes per-minute aggregates in `rollups_min`, used by the API for time series views.

## DuckDB Tables
- `trades_raw` — Source payloads as received.
- `trades_labeled` — Enriched trades with premium, side, sweep ID, and NBBO context.
- `nbbo_at_trade` — Bid/ask snapshot captured at trade time.
- `rollups_min` — Minute-level aggregations by symbol.
- `open_interest_eod` — Placeholder for daily open interest snapshots.

Indexes on `trades_labeled` (`symbol, trade_ts_utc`) and `rollups_min` (`symbol, minute_bucket`) keep API queries responsive.

## Configuration
Settings are managed via `option_flow.config.settings.Settings`. Demo mode defaults to `true`; when set to `false`, a Polygon API key becomes mandatory. Stream symbol filters use JSON arrays (e.g., `OPTION_FLOW_POLYGON_STREAM_SYMBOLS=["O:SPY*","O:QQQ*"]`).

## Logging & Health
`option_flow.observability.logging` standardizes logging format. `/health` reports demo mode, ingest status, subscribed symbols, last trade timestamp, and a rolling 5-minute trade count.

