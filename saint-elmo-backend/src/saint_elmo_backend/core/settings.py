from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
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
    db_url: str

    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout: int = 30
    db_echo: bool = False

    token_issuer: str = "saint-elmo"

    # User sessions
    jwt_secret: SecretStr = Field(min_length=32)
    user_token_audience: str = "saint-elmo:user"
    access_token_lifetime_minutes: int = 60

    # Agent tokens
    agent_token_signing_key: SecretStr
    agent_token_audience: str = "saint-elmo:agent"

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
