from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Iterator

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.init_db as init_db  # noqa: E402
from option_flow.config import settings as settings_module


@pytest.fixture(scope="session")
def integration_db(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Path]:
    db_dir = tmp_path_factory.mktemp("duckdb")
    db_path = db_dir / "test.duckdb"
    parquet_path = db_dir / "demo.parquet"

    original_demo_parquet = init_db.DEMO_PARQUET

    con = duckdb.connect(str(db_path))
    init_db.apply_schema(con)
    init_db.DEMO_PARQUET = parquet_path
    init_db.seed_demo(con)
    con.close()

    prev_path = os.environ.get("OPTION_FLOW_DUCKDB_PATH")
    prev_demo = os.environ.get("OPTION_FLOW_DEMO_MODE")

    os.environ["OPTION_FLOW_DUCKDB_PATH"] = str(db_path)
    os.environ["OPTION_FLOW_DEMO_MODE"] = "true"
    settings_module.get_settings.cache_clear()

    try:
        yield db_path
    finally:
        init_db.DEMO_PARQUET = original_demo_parquet
        settings_module.get_settings.cache_clear()
        if prev_path is None:
            os.environ.pop("OPTION_FLOW_DUCKDB_PATH", None)
        else:
            os.environ["OPTION_FLOW_DUCKDB_PATH"] = prev_path
        if prev_demo is None:
            os.environ.pop("OPTION_FLOW_DEMO_MODE", None)
        else:
            os.environ["OPTION_FLOW_DEMO_MODE"] = prev_demo
