from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

from option_flow.config.settings import get_settings


@dataclass
class NBBOQuote:
    bid: float
    ask: float
    timestamp: datetime

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2


class NBBOCache:
    """Simple in-memory NBBO cache keyed by option contract."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._store: Dict[str, NBBOQuote] = {}

    def _ttl(self) -> timedelta:
        return timedelta(seconds=self._settings.nbbo_cache_ttl_seconds)

    def upsert(self, contract: str, bid: float, ask: float, timestamp: datetime) -> None:
        self._store[contract] = NBBOQuote(bid=bid, ask=ask, timestamp=timestamp)

    def get(self, contract: str, *, now: Optional[datetime] = None) -> Optional[NBBOQuote]:
        quote = self._store.get(contract)
        if not quote:
            return None
        now = now or datetime.utcnow()
        if now - quote.timestamp > self._ttl():
            self._store.pop(contract, None)
            return None
        return quote

    def bulk_expire(self, *, now: Optional[datetime] = None) -> None:
        now = now or datetime.utcnow()
        ttl = self._ttl()
        stale_keys = [key for key, quote in self._store.items() if now - quote.timestamp > ttl]
        for key in stale_keys:
            self._store.pop(key, None)


__all__ = ["NBBOCache", "NBBOQuote"]
