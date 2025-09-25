from __future__ import annotations

from typing import Iterable, Mapping, Sequence

import duckdb
import pandas as pd

from option_flow.storage.duckdb_client import get_connection


class DuckDBRepository:
    """Thin wrapper around DuckDB connections for consistent query patterns."""

    def fetch_df(self, sql: str, params: Mapping[str, object] | Sequence[object] | None = None) -> pd.DataFrame:
        with get_connection(read_only=True) as con:
            return _execute(con, sql, params).df()

    def fetch_all(self, sql: str, params: Mapping[str, object] | Sequence[object] | None = None) -> list[tuple]:
        with get_connection(read_only=True) as con:
            return _execute(con, sql, params).fetchall()

    def fetch_one(self, sql: str, params: Mapping[str, object] | Sequence[object] | None = None) -> tuple | None:
        with get_connection(read_only=True) as con:
            result = _execute(con, sql, params)
            return result.fetchone()

    def execute(self, sql: str, params: Mapping[str, object] | Sequence[object] | None = None) -> None:
        with get_connection(read_only=False) as con:
            _execute(con, sql, params)

    def executemany(self, sql: str, rows: Iterable[Sequence[object]]) -> None:
        with get_connection(read_only=False) as con:
            con.executemany(sql, rows)


def _execute(con: duckdb.DuckDBPyConnection, sql: str, params: Mapping[str, object] | Sequence[object] | None) -> duckdb.DuckDBPyRelation:
    if params is None:
        return con.execute(sql)
    if isinstance(params, Mapping):
        return con.execute(sql, params)
    return con.execute(sql, list(params))


__all__ = ["DuckDBRepository"]
