from __future__ import annotations

from datetime import datetime, timedelta

from option_flow.ingest.nbbo_cache import NBBOCache


def test_cache_returns_recent_quote():
    cache = NBBOCache()
    now = datetime.utcnow()
    cache.upsert('contract', 1.0, 1.2, now)
    quote = cache.get('contract', now=now + timedelta(seconds=5))
    assert quote is not None


def test_cache_expires_stale_quote():
    cache = NBBOCache()
    now = datetime.utcnow()
    cache.upsert('contract', 1.0, 1.2, now - timedelta(seconds=120))
    assert cache.get('contract', now=now) is None
