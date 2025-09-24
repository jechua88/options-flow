from __future__ import annotations

from datetime import date

import pytest

from option_flow.vendors.polygon import OptionContract, parse_option_symbol


def test_parse_option_symbol_basic() -> None:
    symbol = 'O:SPY240920C00460000'
    contract = parse_option_symbol(symbol)
    assert contract == OptionContract(underlying='SPY', expiry=date(2024, 9, 20), strike=460.0, option_type='C')


def test_parse_option_symbol_put() -> None:
    symbol = 'O:QQQ250117P00295000'
    contract = parse_option_symbol(symbol)
    assert contract.underlying == 'QQQ'
    assert contract.option_type == 'P'
    assert contract.expiry == date(2025, 1, 17)
    assert contract.strike == 295.0


@pytest.mark.parametrize('bad_symbol', ['', 'SPY', 'O:123', 'O:SPY240920X00460000', 'O:SPY240920Cfoo'])
def test_parse_option_symbol_invalid(bad_symbol: str) -> None:
    with pytest.raises(ValueError):
        parse_option_symbol(bad_symbol)
