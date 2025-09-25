from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

import pandas as pd
import streamlit as st

from option_flow.config.settings import get_settings
from option_flow.ui.client import APIClient

API_BASE = os.getenv("OPTION_FLOW_API_BASE", "http://localhost:8000")
WINDOW_OPTIONS = ["5m", "15m", "30m", "60m", "560m"]
CALL_PUT_OPTIONS = {"Mixed": "both", "Calls": "calls", "Puts": "puts"}
API_CLIENT = APIClient(API_BASE)


@lru_cache(maxsize=1)
def settings_cached() -> Any:
    return get_settings()


def fetch_health() -> dict[str, Any]:
    try:
        return API_CLIENT.json("/health")
    except Exception:
        return {}


def fetch_json(path: str, params: dict[str, Any] | None = None) -> Any:
    return API_CLIENT.json(path, params=params)


def fetch_csv(path: str, params: dict[str, Any] | None = None) -> bytes:
    return API_CLIENT.bytes(path, params=params)


st.set_page_config(page_title="Option Flow", layout="wide")
st.title("Option Flow Dashboard")
settings = settings_cached()
health = fetch_health()

if health:
    status = health.get("status", "unknown")
    st.caption(f"API status: {status}")
    recent = health.get("recent_trades_5m")
    if recent is not None:
        st.metric("Trades last 5 min", recent)
else:
    st.error("API is unreachable at the moment.")

if health.get("demo_mode", settings.demo_mode) or os.getenv("OPTION_FLOW_DEMO_MODE", "").lower() in {"1", "true", "yes"}:
    st.info("Demo mode active - displaying recorded trade sample.")

if not health.get("ingest_enabled", True):
    st.warning("Live ingest loop is disabled; data may be stale.")

if callable(getattr(st, "autorefresh", None)):
    st.autorefresh(interval=1000, key="auto-refresh")

with st.sidebar:
    st.header("Filters")
    window = st.selectbox("Window", WINDOW_OPTIONS, index=WINDOW_OPTIONS.index("30m"))
    min_notional = st.number_input("Minimum Notional ($)", min_value=0, value=250000, step=50000)
    call_put_label = st.selectbox("Calls/Puts", list(CALL_PUT_OPTIONS.keys()), index=0)
    zero_dte_only = st.checkbox("0DTE Only", value=False)

params = {
    "window": window,
    "min_notional": min_notional,
    "call_put": CALL_PUT_OPTIONS[call_put_label],
    "zero_dte_only": str(zero_dte_only).lower(),
}

try:
    table_data = fetch_json("/top", params=params)
except Exception as exc:  # pragma: no cover - UI path
    st.error(f"Failed to load table data: {exc}")
    table_data = []

if table_data:
    table_df = pd.DataFrame(table_data)
    st.subheader("Top Flow")
    st.dataframe(table_df, use_container_width=True)
else:
    st.warning("No trades available for the selected filters.")

col_left, col_right = st.columns([2, 1])

with col_left:
    st.subheader("Large Prints")
    try:
        prints = fetch_json("/prints", params={"min_notional": max(min_notional, 250000)})
    except Exception as exc:  # pragma: no cover - UI path
        st.error(f"Failed to load prints: {exc}")
        prints = []

    if prints:
        prints_df = pd.DataFrame(prints)
        prints_df = prints_df[["trade_ts_utc", "symbol", "option", "notional", "side", "is_0dte", "sweep_id"]]
        st.dataframe(prints_df, use_container_width=True, height=400)
    else:
        st.caption("No large prints found.")

with col_right:
    st.subheader("Ticker Detail")
    symbol_options = [row["symbol"] for row in table_data] or settings.default_symbols
    selected_symbol = st.selectbox("Ticker", options=symbol_options, index=0)

    try:
        detail = fetch_json(f"/ticker/{selected_symbol}", params={"window": window})
    except Exception as exc:  # pragma: no cover
        st.error(f"Failed to load ticker detail: {exc}")
        detail = None

    if detail:
        st.markdown(f"**Window:** {detail['window_minutes']} minutes")
        minute_bars = detail.get("by_minute", [])
        if minute_bars:
            minute_df = pd.DataFrame(minute_bars)
            minute_df.set_index("minute_bucket", inplace=True)
            st.line_chart(minute_df["total_premium"], height=180)
        largest = detail.get("largest_prints", [])
        if largest:
            largest_df = pd.DataFrame(largest)
            st.dataframe(largest_df[["trade_ts_utc", "option", "notional", "side"]], use_container_width=True, height=250)
        strikes = detail.get("top_strikes", [])
        if strikes:
            st.markdown("**Top Strikes:**")
            for strike in strikes:
                st.write(f"• {strike}")

try:
    csv_bytes = fetch_csv("/export.csv", params=params)
except Exception as exc:  # pragma: no cover - UI path
    st.error(f"Failed to generate CSV: {exc}")
    csv_bytes = b""

st.download_button(
    "Download CSV",
    data=csv_bytes,
    file_name="option-flow.csv",
    mime="text/csv",
    disabled=not csv_bytes,
)
