# Option Flow MVP

Option Flow MVP ingests Polygon.io options trades into DuckDB, exposes FastAPI endpoints, and renders a Streamlit dashboard for recent premium flow.

## Requirements
- Python 3.11+
- Polygon.io API key (Options subscription tier for live data)

## Setup
1. Create virtualenv and install dependencies:
```bash
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# macOS/Linux
source .venv/bin/activate
pip install -e .[dev]
```
2. Copy `.env.example` to `.env` and set `OPTION_FLOW_POLYGON_API_KEY` plus any overrides.
3. Initialize DuckDB and demo data (offline sample):
```bash
python scripts/init_db.py --demo
```

## Make Targets
- `make run` – start API (port 8000) and Streamlit UI (port 8501) against the local database.
- `make api` – run the FastAPI service only.
- `make ui` – run just the Streamlit dashboard.
- `make ingest` – launch the ingest worker (placeholder until Polygon stream wiring lands).
- `make demo` – start API + UI in demo mode (no Polygon access required).
- `make test` – run pytest suite.
- `make lint` – run Ruff + mypy.

## Demo Mode
Use `make demo` or set `OPTION_FLOW_DEMO_MODE=true` in `.env` to explore the recorded SPY/QQQ/AAPL dataset without hitting Polygon.

## Project Layout
- `src/option_flow` – application modules (ingest, services, api, ui, storage, vendors).
- `data/` – DuckDB database and parquet samples (gitignored).
- `tests/` – unit and smoke suites.
- `scripts/` – CLI helpers, including database bootstrap.

## Live Data Notes
Polygon’s live feed requires their streaming WebSocket (`wss://socket.polygon.io/options`) and appropriate permissions. The current worker contains scaffolding for integration; swap from demo to live by providing your API key and implementing the Polygon client stream.

## Licensing
Market data is provided by Polygon.io under their terms; no scraping. Secrets should remain outside version control.
