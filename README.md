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
- `make test-unit` - run fast unit tests (skips integration).
- `make test-integration` - run DB-backed integration tests.
- `make lint` – run Ruff + mypy.

## Demo Mode
Use `make demo` or set `OPTION_FLOW_DEMO_MODE=true` in `.env` to explore the recorded SPY/QQQ/AAPL dataset without hitting Polygon.

## Launcher & Desktop App

### CLI Launcher
Run `python -m option_flow.launcher.cli` to start the API, UI, and ingest worker together. Add `--demo` to use the bundled DuckDB sample or `--open-browser` to launch the dashboard automatically. Launcher logs are written to `logs/launcher.log` by default; override with `--log-file`. Use `Ctrl+C` to stop all services.

### Desktop App
Install the optional GUI dependencies with `pip install .[desktop]`, then launch `python -m option_flow.desktop.app`. The desktop controller lets you toggle demo mode, start/stop services, and open the dashboard without touching a terminal. Logs from the desktop launcher are stored at `logs/desktop-launcher.log`.

### Desktop Shortcut
On Windows you can create a shortcut on your desktop by running `python -m option_flow.desktop.shortcut`. Use `--name` and `--log-file` options to customize the link; by default it points to your current Python interpreter and launches `python -m option_flow.desktop.app`.

### Packaging
To build a standalone desktop binary (requires PyInstaller), run `make desktop-package`. The output appears under `dist/option-flow-desktop`.

### CLI Launcher
Run `python -m option_flow.launcher.cli` to start the API, UI, and ingest worker together. Add `--demo` to use the bundled DuckDB sample or `--open-browser` to launch the dashboard automatically. Use `Ctrl+C` to stop all services.

### Desktop App
Install the optional GUI dependencies with `pip install .[desktop]`, then launch `python -m option_flow.desktop.app`. The desktop controller lets you toggle demo mode, start/stop services, and open the dashboard without touching a terminal.


## Project Layout
- `src/option_flow` – application modules (ingest, services, api, ui, storage, vendors).
- `data/` – DuckDB database and parquet samples (gitignored).
- `tests/` – unit and smoke suites.
- `scripts/` – CLI helpers, including database bootstrap.

## Live Data Notes
Polygon’s live feed requires their streaming WebSocket (`wss://socket.polygon.io/options`) and appropriate permissions. The current worker contains scaffolding for integration; swap from demo to live by providing your API key, setting any OPTION_FLOW_POLYGON_STREAM_SYMBOLS filters you need, and implementing the Polygon client stream."

## Licensing
Market data is provided by Polygon.io under their terms; no scraping. Secrets should remain outside version control.

