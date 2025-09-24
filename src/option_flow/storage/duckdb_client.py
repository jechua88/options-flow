from __future__ import annotations

from collections.abc import Mapping, Sequence
from contextlib import contextmanager
from typing import Any, Iterator

import duckdb
import pandas as pd

from option_flow.config.settings import get_settings


@contextmanager
def get_connection(read_only: bool = True) -> Iterator[duckdb.DuckDBPyConnection]:
    settings = get_settings()
    con = duckdb.connect(str(settings.duckdb_path), read_only=read_only)
    try:
        yield con
    finally:
        con.close()


def query_df(sql: str, params: Mapping[str, Any] | Sequence[Any] | None = None) -> pd.DataFrame:
    with get_connection(read_only=True) as con:
        if params is None:
            result = con.execute(sql)
        elif isinstance(params, Mapping):
            result = con.execute(sql, params)
        else:
            result = con.execute(sql, list(params))
        return result.df()
