# Option Flow MVP

Option Flow MVP ingests ThetaData options trades into DuckDB, exposes FastAPI endpoints, and renders a Streamlit dashboard for recent premium flow.

## Requirements
- Python 3.11+
- DuckDB 0.10+

## Setup
1. Create virtualenv and install deps:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```
2. Copy `.env.example` to `.env` and fill in ThetaData credentials (not required for demo mode).
3. Initialize DuckDB and demo data:
```bash
python scripts/init_db.py --demo
```

## Make Targets
- `make run` – start ingest worker, API (port 8000), and Streamlit UI (port 8501).
- `make api` – run API only.
- `make ui` – run Streamlit UI only.
- `make ingest` – run ingest worker.
- `make demo` – start API + UI pointed at offline demo dataset.
- `make test` – execute unit tests.
- `make lint` – run Ruff and mypy.

## Demo Mode
Use `make demo` or set `demo_mode=true` in `.env` to explore recorded SPY/QQQ/AAPL trades without external connectivity.

## Project Layout
- `src/option_flow` – application modules (ingest, services, api, ui, storage).
- `data/` – DuckDB database and parquet samples (gitignored).
- `tests/` – unit and e2e smoke suites.
- `scripts/` – CLI helpers.

## Licensing
Market data requires ThetaData license; no scraping.
