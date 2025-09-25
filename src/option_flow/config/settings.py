from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any

from pydantic import BeforeValidator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _parse_symbols(value: Any) -> list[str]:
    if isinstance(value, str):
        return [item.strip().upper() for item in value.split(',') if item.strip()]
    if isinstance(value, (list, tuple)):
        return [str(item).upper() for item in value]
    raise TypeError('default_symbols must be a comma string or list')


def _parse_optional_symbols(value: Any) -> list[str] | None:
    if value in (None, '', []):
        return None
    return _parse_symbols(value)


def _parse_path(value: Any) -> Path:
    if isinstance(value, Path):
        return value
    return Path(str(value))


DefaultSymbols = Annotated[list[str], BeforeValidator(_parse_symbols)]
OptionalSymbols = Annotated[list[str] | None, BeforeValidator(_parse_optional_symbols)]
DuckDBPath = Annotated[Path, BeforeValidator(_parse_path)]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_prefix='OPTION_FLOW_',
        extra='ignore',
    )

    polygon_api_key: str | None = None
    polygon_ws_url: str = 'wss://socket.polygon.io/options'
    polygon_rest_base_url: str = 'https://api.polygon.io'
    polygon_stream_symbols: OptionalSymbols = None
    duckdb_path: DuckDBPath = Path('data/optionflow.duckdb')
    default_symbols: DefaultSymbols = ['SPY', 'QQQ', 'AAPL']
    window_minutes: int = 30
    min_notional_usd: int = 250_000
    nbbo_cache_ttl_seconds: int = 30
    demo_mode: bool = True
    log_level: str = 'INFO'


@model_validator(mode="after")
def validate_polygon_config(cls, values):
    if not values.demo_mode and not values.polygon_api_key:
        raise ValidationError("polygon_api_key must be set when OPTION_FLOW_DEMO_MODE is false")
    return values

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
                if not key.startswith(prefix):
                    continue
                field_name = key[plen:].lower()
                # Remove handled keys to prevent default env source from re-processing them
                os.environ.pop(key, None)
                if field_name == 'default_symbols':
                    parsed_symbols = _parse_symbols(value)
                    data[field_name] = parsed_symbols
                    os.environ[key] = json.dumps(parsed_symbols)
                elif field_name == 'polygon_stream_symbols':
                    parsed = _parse_optional_symbols(value)
                    if parsed is not None:
                        data[field_name] = parsed
                        os.environ[key] = json.dumps(parsed)
                else:
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

