"""
Signing and verifying Agent tokens: EdDSA (Ed25519) JWTs, shaped as RFC 9068 JWT access
tokens (`typ: at+jwt`), whose public key is published as a JWKS (ADR 0003).

This module only answers "did Saint Elmo sign this, for agents, and is it unexpired?".
Whether a valid token is still honoured (revocation, disabled agent) is decided against
its credential row in `services`.
"""

import base64
import hashlib
import json
from collections.abc import Collection
from datetime import datetime
from functools import lru_cache
from uuid import UUID

import jwt
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from jwt.algorithms import OKPAlgorithm
from jwt.exceptions import InvalidTokenError

from saint_elmo_backend.agents.dtos import AgentTokenClaims
from saint_elmo_backend.agents.enums import Scope
from saint_elmo_backend.agents.exceptions import InvalidAgentTokenError
from saint_elmo_backend.core import exceptions, tokens
from saint_elmo_backend.core.settings import get_settings

ALGORITHM = "EdDSA"
TOKEN_TYPE = "at+jwt"


def _b64url_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


@lru_cache
def _load_private_key(encoded: str) -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(_b64url_decode(encoded))


def _private_key() -> Ed25519PrivateKey:
    return _load_private_key(get_settings().agent_token_signing_key.get_secret_value())


def public_jwk() -> dict[str, str]:
    """
    The verification key as a JWK, for `/.well-known/jwks.json`.
    """

    jwk: dict[str, str] = OKPAlgorithm.to_jwk(_private_key().public_key(), as_dict=True)
    return {**jwk, "kid": key_id(), "use": "sig", "alg": ALGORITHM}


def key_id() -> str:
    """
    RFC 7638 thumbprint of the public key: stable for a key and new for a rotated one,
    with no extra configuration.
    """

    jwk = OKPAlgorithm.to_jwk(_private_key().public_key(), as_dict=True)
    members = json.dumps(
        {"crv": jwk["crv"], "kty": jwk["kty"], "x": jwk["x"]},
        separators=(",", ":"),
        sort_keys=True,
    )
    return _b64url_encode(hashlib.sha256(members.encode()).digest())


def sign(
    *,
    jti: UUID,
    agent_public_id: UUID,
    organization_public_id: UUID,
    mandate_public_id: UUID,
    scopes: Collection[Scope],
    issued_at: datetime,
    expires_at: datetime,
) -> str:
    return tokens.sign(
        key=_private_key(),
        algorithm=ALGORITHM,
        audience=get_settings().agent_token_audience,
        subject=agent_public_id,
        organization_public_id=organization_public_id,
        issued_at=issued_at,
        expires_at=expires_at,
        claims={
            "scope": " ".join(sorted(scopes)),
            "mandate_id": str(mandate_public_id),
            "jti": str(jti),
        },
        headers={"kid": key_id(), "typ": TOKEN_TYPE},
    )


def verify(token: str) -> AgentTokenClaims:
    try:
        if jwt.get_unverified_header(token).get("typ") != TOKEN_TYPE:
            raise InvalidAgentTokenError()

        claims = tokens.verify(
            token,
            key=_private_key().public_key(),
            algorithm=ALGORITHM,
            audience=get_settings().agent_token_audience,
            required=("scope", "mandate_id", "jti"),
        )
        return AgentTokenClaims(
            jti=tokens.uuid_claim(claims, "jti"),
            agent_public_id=tokens.uuid_claim(claims, "sub"),
            organization_public_id=tokens.uuid_claim(claims, "org_id"),
            mandate_public_id=tokens.uuid_claim(claims, "mandate_id"),
            scopes=frozenset(Scope(scope) for scope in str(claims["scope"]).split()),
        )
    except (InvalidTokenError, exceptions.InvalidJWTError, ValueError):
        raise InvalidAgentTokenError() from None
