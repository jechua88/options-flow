from __future__ import annotations

from option_flow.services.rollups import RollupService
from option_flow.storage.duckdb_client import query_df


def test_rollup_service_refreshes_data():
    service = RollupService()
    service.refresh_recent_minutes(60)
    df = query_df('SELECT COUNT(*) AS cnt FROM rollups_min')
    assert int(df.iloc[0]['cnt']) > 0
