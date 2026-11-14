from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    debug: bool = True

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "DEBUG"

    # Database
    db_url: str  # owner role (app_migrator), used by Alembic
    app_db_url: str  # non-superuser role the app connects as (app_runtime, RLS applies)

    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout: int = 30
    db_echo: bool = False

    # Cryptography (Fernet keys for EncryptedString; first key encrypts, all decrypt)
    credential_keys: list[str] = []

    # Static Valio Aimo data set (product JSON + CSVs), loaded by the catalogue seeder
    catalog_data_dir: Path = Path("../data")
    # Date the static data set was exported; reported as provenance on catalogue responses
    catalog_snapshot_date: date

    # Valio Aimo API (live price and availability). Optional so the app starts and
    # catalog-only development works without them; calls then fail as not configured.
    valio_aimo_api_url: str | None = None
    valio_aimo_api_key: SecretStr | None = None
    valio_aimo_max_attempts: int = 3  # in total, including the first
    valio_aimo_backoff_base_seconds: float = 0.5


@lru_cache
def get_settings() -> Settings:
    return Settings()
