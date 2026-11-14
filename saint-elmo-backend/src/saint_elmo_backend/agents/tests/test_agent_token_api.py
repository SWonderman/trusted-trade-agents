"""
Agent tokens and user sessions on protected routes, exercised over HTTP.

Product search is the protected route under test: it accepts both schemes and requires
`catalog:read` from agents.
"""

import base64
import json
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated, Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from saint_elmo_backend.accounts.tests.factories import (
    make_organization,
    make_user,
    user_session_headers,
)
from saint_elmo_backend.agents.enums import AgentStatus, Scope
from saint_elmo_backend.agents.models import AgentCredential
from saint_elmo_backend.agents.tests.factories import bearer, issue_token, make_agent
from saint_elmo_backend.api.error_handlers import register_error_handlers
from saint_elmo_backend.api.v1.auth import Principal, authenticate
from saint_elmo_backend.core.settings import get_settings

SEARCH_URL = "/api/v1/products/search"
ME_URL = "/api/v1/auth/me"


def _signing_key() -> Ed25519PrivateKey:
    encoded = get_settings().agent_token_signing_key.get_secret_value()
    return Ed25519PrivateKey.from_private_bytes(base64.urlsafe_b64decode(encoded + "=="))


def _resign(
    token: str,
    *,
    key: Any = None,
    algorithm: str = "EdDSA",
    headers: dict[str, str] | None = None,
    **claims: Any,
) -> str:
    """
    A real Agent token with some claims changed (None removes one), signed again.
    """

    payload = jwt.decode(token, options={"verify_signature": False})
    for name, value in claims.items():
        if value is None:
            payload.pop(name)
        else:
            payload[name] = value
    return jwt.encode(
        payload,
        key if key is not None else _signing_key(),
        algorithm=algorithm,
        # Keep kid and typ; `alg` follows the forging algorithm
        headers={
            **{k: v for k, v in jwt.get_unverified_header(token).items() if k != "alg"},
            **(headers or {}),
        },
    )


def _widen_scope_keeping_signature(token: str) -> str:
    header, payload, signature = token.split(".")
    claims = jwt.decode(token, options={"verify_signature": False})
    widened = json.dumps({**claims, "scope": "catalog:read order:place"}).encode()
    return f"{header}.{base64.urlsafe_b64encode(widened).rstrip(b'=').decode()}.{signature}"


def _assert_invalid_credentials(response) -> None:
    assert response.status_code == 401, response.text
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def _assert_permission_denied(response, message: str) -> None:
    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"
    assert message in response.json()["error"]["message"]


@pytest.mark.parametrize(
    ("method", "url"),
    [("POST", SEARCH_URL), ("GET", "/api/v1/products/100001")],
    ids=["search", "detail"],
)
async def test_catalog_requires_credentials(clean_db, client, method, url):
    _assert_invalid_credentials(await client.request(method, url, json={}))


async def test_agent_token_opens_the_catalog(clean_db, session, client):
    agent = await make_agent(session, await make_organization(session))
    token = await issue_token(session, agent, scopes=[Scope.CATALOG_READ])
    await session.commit()

    response = await client.post(SEARCH_URL, json={}, headers=bearer(token))

    assert response.status_code == 200, response.text


async def test_user_session_opens_the_catalog(clean_db, session, client):
    user = await make_user(session, await make_organization(session))
    await session.commit()

    response = await client.post(SEARCH_URL, json={}, headers=user_session_headers(user))

    assert response.status_code == 200, response.text


async def test_use_is_recorded_on_the_credential(clean_db, session, client):
    agent = await make_agent(session, await make_organization(session))
    token = await issue_token(session, agent)
    await session.commit()

    await client.post(SEARCH_URL, json={}, headers=bearer(token))

    credential = await session.scalar(
        select(AgentCredential).where(AgentCredential.jti == token.jti)
    )
    await session.refresh(credential)
    assert credential.last_used_at is not None


_FORGERIES: dict[str, Callable[[str], str]] = {
    "tampered payload": _widen_scope_keeping_signature,
    "signed by another key": lambda token: _resign(token, key=Ed25519PrivateKey.generate()),
    "expired": lambda token: _resign(token, exp=int(datetime.now(UTC).timestamp()) - 60),
    "wrong audience": lambda token: _resign(token, aud=get_settings().user_token_audience),
    "wrong issuer": lambda token: _resign(token, iss="someone-else"),
    "missing mandate_id": lambda token: _resign(token, mandate_id=None),
    "scope changed and re-signed": lambda token: _resign(token, scope="catalog:read order:place"),
    "not typed as an access token": lambda token: _resign(token, headers={"typ": "JWT"}),
    "other agent's id": lambda token: _resign(token, sub="00000000-0000-0000-0000-000000000000"),
    "unknown jti": lambda token: _resign(token, jti="00000000-0000-0000-0000-000000000000"),
    "unsigned (alg none)": lambda token: _resign(token, key="", algorithm="none"),
    "agent claims under the user session key": lambda token: _resign(
        token, key=get_settings().jwt_secret.get_secret_value(), algorithm="HS256"
    ),
}


@pytest.mark.parametrize("forge", _FORGERIES.values(), ids=_FORGERIES.keys())
async def test_forged_agent_tokens_are_refused(clean_db, session, client, forge):
    agent = await make_agent(session, await make_organization(session))
    token = await issue_token(session, agent)
    await session.commit()

    _assert_invalid_credentials(
        await client.post(SEARCH_URL, json={}, headers=bearer(forge(token.token)))
    )


async def test_revoked_token_is_refused_on_the_next_request(clean_db, session, client):
    agent = await make_agent(session, await make_organization(session))
    token = await issue_token(session, agent)
    await session.commit()
    assert (await client.post(SEARCH_URL, json={}, headers=bearer(token))).status_code == 200

    credential = await session.scalar(
        select(AgentCredential).where(AgentCredential.jti == token.jti)
    )
    credential.revoked_at = datetime.now(UTC)
    await session.commit()

    _assert_invalid_credentials(await client.post(SEARCH_URL, json={}, headers=bearer(token)))


async def test_disabled_agent_has_all_its_tokens_refused(clean_db, session, client):
    agent = await make_agent(session, await make_organization(session))
    tokens = [await issue_token(session, agent) for _ in range(2)]
    agent.status = AgentStatus.DISABLED
    await session.commit()

    for token in tokens:
        _assert_invalid_credentials(await client.post(SEARCH_URL, json={}, headers=bearer(token)))


async def test_inactive_buyer_organisation_has_its_agents_refused(clean_db, session, client):
    organization = await make_organization(session)
    token = await issue_token(session, await make_agent(session, organization))
    organization.is_active = False
    await session.commit()

    _assert_invalid_credentials(await client.post(SEARCH_URL, json={}, headers=bearer(token)))


async def test_token_without_the_routes_scope_is_forbidden(clean_db, session, client):
    agent = await make_agent(session, await make_organization(session))
    token = await issue_token(session, agent, scopes=[Scope.ORDER_READ])
    await session.commit()

    response = await client.post(SEARCH_URL, json={}, headers=bearer(token))

    _assert_permission_denied(response, "catalog:read")


async def test_agent_token_is_not_a_user_session(clean_db, session, client):
    agent = await make_agent(session, await make_organization(session))
    token = await issue_token(session, agent)
    await session.commit()

    _assert_permission_denied(
        await client.get(ME_URL, headers=bearer(token)), "not available to agents"
    )


async def test_user_session_is_not_an_agent_token(clean_db, session, client):
    """
    No agent-only route exists yet (#11 brings the first), so one is mounted here.
    """

    agent_only = FastAPI()
    register_error_handlers(agent_only)

    @agent_only.get("/agent-only")
    async def _route(
        _principal: Annotated[Principal, Depends(authenticate(agent_scope=Scope.MANDATE_READ))],
    ) -> None:
        return None

    user = await make_user(session, await make_organization(session))
    await session.commit()

    async with AsyncClient(
        transport=ASGITransport(app=agent_only), base_url="http://test"
    ) as agent_only_client:
        response = await agent_only_client.get("/agent-only", headers=user_session_headers(user))

    _assert_permission_denied(response, "only available to agents")


async def test_jwks_verifies_an_issued_token_with_standard_tooling(clean_db, session, client):
    agent = await make_agent(session, await make_organization(session))
    token = await issue_token(session, agent, scopes=[Scope.CATALOG_READ, Scope.ORDER_READ])
    await session.commit()

    jwks = jwt.PyJWKSet.from_dict((await client.get("/.well-known/jwks.json")).json())
    kid = jwt.get_unverified_header(token.token)["kid"]
    key = next(key for key in jwks.keys if key.key_id == kid)

    claims = jwt.decode(
        token.token,
        key,
        algorithms=["EdDSA"],
        audience=get_settings().agent_token_audience,
        issuer=get_settings().token_issuer,
    )
    assert claims["sub"] == str(agent.public_id)
    assert claims["org_id"] == str(agent.organization.public_id)
    assert claims["scope"] == "catalog:read order:read"
    assert claims["jti"] == str(token.jti)
    assert {"mandate_id", "iat", "exp"} <= claims.keys()


async def test_jwks_publishes_only_the_public_key(client):
    (key,) = (await client.get("/.well-known/jwks.json")).json()["keys"]

    assert key["kty"] == "OKP"
    assert key["crv"] == "Ed25519"
    assert key["alg"] == "EdDSA"
    assert key["use"] == "sig"
    assert "d" not in key


async def test_security_schemes_are_in_openapi(client):
    schema = (await client.get("/openapi.json")).json()

    schemes = schema["components"]["securitySchemes"]
    assert schemes["AgentToken"]["type"] == "http"
    assert schemes["AgentToken"]["scheme"] == "bearer"
    assert schemes["UserSession"]["type"] == "oauth2"
    # Either scheme, with the scope agents need
    assert schema["paths"][SEARCH_URL]["post"]["security"] == [
        {"UserSession": []},
        {"AgentToken": ["catalog:read"]},
    ]
