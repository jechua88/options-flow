from __future__ import annotations

from datetime import datetime

from option_flow.storage.duckdb_client import get_connection


class RollupService:
    """Handles aggregation of trades into minute-level rollups."""

    def refresh_recent_minutes(self, minutes: int = 60) -> None:
        cutoff_expr = f"(now() - INTERVAL {minutes} MINUTE)"
        with get_connection(read_only=False) as con:
            con.execute(
                f"DELETE FROM rollups_min WHERE minute_bucket >= {cutoff_expr}"
            )
            con.execute(
                f"""
                WITH agg AS (
                    SELECT
                        symbol,
                        date_trunc('minute', trade_ts_utc) AS minute_bucket,
                        SUM(premium) AS total_premium,
                        SUM(CASE WHEN side = 'BUY' THEN premium ELSE 0 END) AS buy_premium,
                        SUM(CASE WHEN side = 'SELL' THEN premium ELSE 0 END) AS sell_premium,
                        SUM(CASE WHEN call_put = 'C' THEN premium ELSE 0 END) AS call_premium,
                        SUM(CASE WHEN call_put = 'P' THEN premium ELSE 0 END) AS put_premium,
                        SUM(CASE WHEN is_0dte THEN premium ELSE 0 END) AS zero_dte_premium,
                        COUNT(*) AS trades_count
                    FROM trades_labeled
                    WHERE trade_ts_utc >= {cutoff_expr}
                    GROUP BY 1,2
                )
                INSERT INTO rollups_min (
                    symbol,
                    minute_bucket,
                    total_premium,
                    net_premium,
                    call_premium,
                    put_premium,
                    buy_premium,
                    sell_premium,
                    zero_dte_premium,
                    trades_count,
                    updated_at
                )
                SELECT
                    symbol,
                    minute_bucket,
                    total_premium,
                    buy_premium - sell_premium AS net_premium,
                    call_premium,
                    put_premium,
                    buy_premium,
                    sell_premium,
                    zero_dte_premium,
                    trades_count,
                    now()
                FROM agg
                """
            )


__all__ = ["RollupService"]

