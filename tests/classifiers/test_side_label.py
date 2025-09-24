from __future__ import annotations

from datetime import datetime

from option_flow.ingest.nbbo_cache import NBBOQuote
from option_flow.services.side_classifier import calculate_epsilon, infer_side


def test_calculate_epsilon_respects_floor():
    assert calculate_epsilon(1.0, 1.05) == 0.01


def test_infer_buy_side():
    quote = NBBOQuote(bid=1.0, ask=1.2, timestamp=datetime.utcnow())
    result = infer_side(1.19, quote)
    assert result.side == 'BUY'


def test_infer_sell_side():
    quote = NBBOQuote(bid=1.0, ask=1.2, timestamp=datetime.utcnow())
    result = infer_side(1.01, quote)
    assert result.side == 'SELL'


def test_infer_mid_when_no_nbbo():
    result = infer_side(1.1, None)
    assert result.side == 'MID'
