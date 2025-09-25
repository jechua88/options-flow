from __future__ import annotations


import pytest

from option_flow.config import settings
from option_flow.ingest.live import LiveTradeService


class DummyClient:
    def __init__(self) -> None:
        self.seen = None

    async def stream_trades(self, symbols):
        self.seen = symbols
        yield []


class DummyProcessor:
    def process_quote(self, event):  # pragma: no cover - simple stub
        return None

    def process_trade(self, event):  # pragma: no cover - simple stub
        return False


@pytest.fixture(autouse=True)
def clear_settings(monkeypatch):
    settings.get_settings.cache_clear()
    yield
    settings.get_settings.cache_clear()


def test_live_service_uses_stream_symbols(monkeypatch):
    monkeypatch.setenv('OPTION_FLOW_POLYGON_STREAM_SYMBOLS', 'O:SPY*,O:QQQ*')
    service = LiveTradeService(polygon_client=DummyClient(), processor=DummyProcessor())
    assert service._symbols == ['O:SPY*', 'O:QQQ*']


def test_live_service_defaults_to_wildcard():
    service = LiveTradeService(polygon_client=DummyClient(), processor=DummyProcessor())
    assert service._symbols == []
