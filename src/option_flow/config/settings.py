from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any

from pydantic import BeforeValidator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _parse_symbols(value: Any) -> list[str]:
    if isinstance(value, str):
        return [item.strip().upper() for item in value.split(',') if item.strip()]
    if isinstance(value, (list, tuple)):
        return [str(item).upper() for item in value]
    raise TypeError('default_symbols must be a comma string or list')


def _parse_path(value: Any) -> Path:
    if isinstance(value, Path):
        return value
    return Path(str(value))


DefaultSymbols = Annotated[list[str], BeforeValidator(_parse_symbols)]
DuckDBPath = Annotated[Path, BeforeValidator(_parse_path)]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_prefix='OPTION_FLOW_',
        extra='ignore',
    )

    theta_api_key: str | None = None
    theta_api_secret: str | None = None
    duckdb_path: DuckDBPath = Path('data/optionflow.duckdb')
    default_symbols: DefaultSymbols = ['SPY', 'QQQ', 'AAPL']
    window_minutes: int = 30
    min_notional_usd: int = 250_000
    nbbo_cache_ttl_seconds: int = 30
    demo_mode: bool = False
    log_level: str = 'INFO'

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        def custom_env_settings() -> dict[str, Any]:
            data: dict[str, Any] = {}
            prefix = 'OPTION_FLOW_'
            plen = len(prefix)
            for key, value in os.environ.items():
                if key.startswith(prefix):
                    field_name = key[plen:].lower()
                    data[field_name] = value
            return data

        return (
            init_settings,
            custom_env_settings,
            dotenv_settings,
            file_secret_settings,
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
