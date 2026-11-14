from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    backend_base_url: str = "http://localhost:8000"
    backend_timeout_seconds: float = 30.0

    mcp_host: str = "127.0.0.1"
    mcp_port: int = 8001


@lru_cache
def get_settings() -> Settings:
    return Settings()
