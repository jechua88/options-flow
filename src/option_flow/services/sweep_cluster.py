from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class SweepState:
    sweep_id: str
    timestamp: datetime


class SweepClusterer:
    """Cluster trades into sweeps using a fixed time threshold."""

    def __init__(self, *, window_ms: int = 200) -> None:
        self._window = timedelta(milliseconds=window_ms)
        self._state: dict[tuple[str, str], SweepState] = {}
        self._counter = 0

    def assign(self, contract: str, side: str, timestamp: datetime) -> str:
        key = (contract, side)
        state = self._state.get(key)
        if state and timestamp - state.timestamp <= self._window:
            sweep_id = state.sweep_id
        else:
            self._counter += 1
            sweep_id = f"sweep-{self._counter}"
        self._state[key] = SweepState(sweep_id=sweep_id, timestamp=timestamp)
        return sweep_id


__all__ = ["SweepClusterer", "SweepState"]
