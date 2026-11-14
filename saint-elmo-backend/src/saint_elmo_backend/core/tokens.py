"""
JWT mechanics shared by user sessions (accounts.tokens) and Agent tokens (agents.tokens).
"""

from collections.abc import Collection, Mapping
from datetime import datetime
from typing import Any
from uuid import UUID

import jwt
from jwt.exceptions import InvalidTokenError

from saint_elmo_backend.core.exceptions import InvalidJWTError
from saint_elmo_backend.core.settings import get_settings

_CORE_CLAIMS = ("iss", "aud", "sub", "org_id", "iat", "exp")


def sign(
    *,
    key: Any,
    algorithm: str,
    audience: str,
    subject: UUID,
    organization_public_id: UUID,
    issued_at: datetime,
    expires_at: datetime,
    claims: Mapping[str, Any] | None = None,
    headers: Mapping[str, str] | None = None,
) -> str:
    payload = {
        "iss": get_settings().token_issuer,
        "aud": audience,
        "sub": str(subject),
        "org_id": str(organization_public_id),
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
        **(claims or {}),
    }
    return jwt.encode(payload, key, algorithm=algorithm, headers=dict(headers or {}))


def verify(
    token: str,
    *,
    key: Any,
    algorithm: str,
    audience: str,
    required: Collection[str] = (),
) -> dict[str, Any]:
    """
    The token's claims, once its signature, issuer, audience, expiry and required claims
    check out.
    """

    try:
        return jwt.decode(
            token,
            key,
            algorithms=[algorithm],
            issuer=get_settings().token_issuer,
            audience=audience,
            options={"require": [*_CORE_CLAIMS, *required]},
        )
    except InvalidTokenError:
        raise InvalidJWTError() from None


def uuid_claim(claims: Mapping[str, Any], name: str) -> UUID:
    try:
        return UUID(claims[name])
    except (KeyError, TypeError, ValueError):
        raise InvalidJWTError() from None
