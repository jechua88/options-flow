# Deployment Guide

## Local Launchers
- **CLI** — `python -m option_flow.launcher.cli --demo --open-browser` starts API, UI, and ingest in demo mode. Add `--no-ui` or `--no-ingest` to selectively disable services; `--log-file` controls launcher logs.
- **Desktop** — `python -m option_flow.desktop.app` (or the installed shortcut) offers a GUI toggle for demo/live mode, status monitoring, and log links.

## Docker Compose
1. Build and run:
   ```bash
   make compose
   # or
   docker compose up --build
   ```
2. The compose file exposes the API on `localhost:8000` and Streamlit on `localhost:8501`. Live deployments should mount a persistent volume for `data/` and set environment overrides (e.g., `OPTION_FLOW_DEMO_MODE=false`, `OPTION_FLOW_POLYGON_API_KEY=...`).
3. Stop the stack with `docker compose down`.

## Production Notes
- **Environment** — Ensure `OPTION_FLOW_POLYGON_API_KEY` is set and `OPTION_FLOW_POLYGON_STREAM_SYMBOLS` scopes subscriptions appropriately to control cost and load.
- **Persistence** — Back up `data/optionflow.duckdb` or redirect `OPTION_FLOW_DUCKDB_PATH` to a managed volume.
- **Observability** — Tail `logs/launcher.log` or the desktop log to monitor ingest health. `/health` surfaces ingest status, subscribed symbols, and recent trade counts for external monitoring.
- **Service Managers** — For bare-metal/server deployments, wrap the CLI launcher in systemd or a supervisor to restart on failure; the launcher exits non-zero if any subprocess dies unexpectedly.

