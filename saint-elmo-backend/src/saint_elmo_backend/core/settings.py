from functools import lru_cache
from typing import Literal

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
