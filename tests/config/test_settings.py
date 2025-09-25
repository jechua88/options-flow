from __future__ import annotations

import os

from option_flow.config import settings


def test_default_symbols_parse(monkeypatch):
    monkeypatch.setenv('OPTION_FLOW_DEFAULT_SYMBOLS', '["spy", "qqq", "aapl"]')
    settings.get_settings.cache_clear()
    cfg = settings.get_settings()
    assert cfg.default_symbols == ['SPY', 'QQQ', 'AAPL']
    settings.get_settings.cache_clear()
