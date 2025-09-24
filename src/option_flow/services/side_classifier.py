from __future__ import annotations

from dataclasses import dataclass

from option_flow.ingest.nbbo_cache import NBBOQuote


@dataclass
class SideInferenceResult:
    side: str
    epsilon: float


def calculate_epsilon(bid: float, ask: float) -> float:
    spread = max(ask - bid, 0.0)
    return max(0.01, 0.05 * spread)


def infer_side(price: float, quote: NBBOQuote | None) -> SideInferenceResult:
    if quote is None:
        return SideInferenceResult(side="MID", epsilon=0.0)

    epsilon = calculate_epsilon(quote.bid, quote.ask)
    if price >= quote.ask - epsilon:
        return SideInferenceResult(side="BUY", epsilon=epsilon)
    if price <= quote.bid + epsilon:
        return SideInferenceResult(side="SELL", epsilon=epsilon)
    return SideInferenceResult(side="MID", epsilon=epsilon)


__all__ = ["SideInferenceResult", "infer_side", "calculate_epsilon"]
