from __future__ import annotations

from pathlib import Path

import duckdb

SCHEMA_SQL = Path('storage/schema.sql').read_text(encoding='utf-8')


def test_schema_creates_tables():
    con = duckdb.connect(database=':memory:')
    con.execute(SCHEMA_SQL)
    tables = {row[0] for row in con.execute('SHOW TABLES').fetchall()}
    expected = {'trades_raw', 'nbbo_at_trade', 'trades_labeled', 'rollups_min', 'open_interest_eod'}
    assert expected.issubset(tables)
