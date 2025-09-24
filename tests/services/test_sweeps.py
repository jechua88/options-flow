from __future__ import annotations

from datetime import datetime, timedelta

from option_flow.services.sweep_cluster import SweepClusterer


def test_sweep_clusters_within_window():
    clusterer = SweepClusterer(window_ms=200)
    ts = datetime.utcnow()
    first = clusterer.assign('SPY-20251024-400C', 'BUY', ts)
    second = clusterer.assign('SPY-20251024-400C', 'BUY', ts + timedelta(milliseconds=150))
    assert first == second


def test_sweep_new_cluster_after_window():
    clusterer = SweepClusterer(window_ms=200)
    ts = datetime.utcnow()
    first = clusterer.assign('SPY-20251024-400C', 'BUY', ts)
    second = clusterer.assign('SPY-20251024-400C', 'BUY', ts + timedelta(milliseconds=300))
    assert first != second
