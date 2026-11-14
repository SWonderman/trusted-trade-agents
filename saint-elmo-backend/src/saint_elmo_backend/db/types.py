from functools import lru_cache
from typing import override

from cryptography.fernet import Fernet, MultiFernet
from sqlalchemy import JSON, Dialect, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import TypeDecorator

from saint_elmo_backend.core.settings import get_settings

# JSONB on Postgres, plain JSON elsewhere
JSONB_ = JSON().with_variant(JSONB, "postgresql")


@lru_cache
def _cipher() -> MultiFernet:
    keys = get_settings().credential_keys
    if not keys:
        raise RuntimeError("No credentials key configured - cannot use EncryptedString type")

    return MultiFernet([Fernet(k.encode()) for k in keys])


class EncryptedString(TypeDecorator[str | None]):
    """
    Encrypt/decrypt a string at the DB boundary.
    """

    impl = Text
    cache_ok: bool | None = True

    @override
    def process_bind_param(self, value: str | None, dialect: Dialect) -> str | None:
        if value is None:
            return None
        return _cipher().encrypt(value.encode()).decode()

    @override
    def process_result_value(self, value: str | None, dialect: Dialect) -> str | None:
        if value is None:
            return None
        return _cipher().decrypt(value.encode()).decode()
