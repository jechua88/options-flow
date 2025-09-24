from __future__ import annotations

import duckdb
import pytest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.init_db as init_db  # noqa: E402
from option_flow.config import settings as settings_module


@pytest.fixture(autouse=True)
def seeded_database(tmp_path, monkeypatch):
    db_path = tmp_path / "test.duckdb"
    parquet_path = tmp_path / "demo.parquet"

    con = duckdb.connect(str(db_path))
    init_db.apply_schema(con)
    monkeypatch.setattr(init_db, "DEMO_PARQUET", parquet_path)
    init_db.seed_demo(con)
    con.close()

    monkeypatch.setenv("OPTION_FLOW_DUCKDB_PATH", str(db_path))
    monkeypatch.setenv("OPTION_FLOW_DEMO_MODE", "true")
    settings_module.get_settings.cache_clear()
    yield
    settings_module.get_settings.cache_clear()
