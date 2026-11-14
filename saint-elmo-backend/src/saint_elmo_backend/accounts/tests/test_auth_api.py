"""
User login (POST /api/v1/auth/token) and sessions (GET /api/v1/auth/me), exercised over HTTP.
"""

from datetime import UTC, datetime, timedelta

import jwt
import pytest

from saint_elmo_backend.accounts.enums import Role
from saint_elmo_backend.accounts.tests.factories import (
    DEFAULT_PASSWORD,
    make_organization,
    make_user,
    user_session_headers,
)
from saint_elmo_backend.core.settings import get_settings

TOKEN_URL = "/api/v1/auth/token"
ME_URL = "/api/v1/auth/me"


def _session_claims(user, **overrides) -> dict:
    settings = get_settings()
    now = datetime.now(UTC)
    claims = {
        "iss": settings.token_issuer,
        "aud": settings.user_token_audience,
        "sub": str(user.public_id),
        "org_id": str(user.organization.public_id),
        "role": user.role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=5)).timestamp()),
    }
    claims.update(overrides)
    return claims


def _sign(claims: dict, secret: str | None = None, algorithm: str = "HS256") -> dict[str, str]:
    key = secret or get_settings().jwt_secret.get_secret_value()
    return {"Authorization": f"Bearer {jwt.encode(claims, key, algorithm=algorithm)}"}


def _assert_invalid_credentials(response) -> None:
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"
    assert response.headers["WWW-Authenticate"] == "Bearer"


async def test_login_returns_a_bearer_token_that_opens_a_session(clean_db, session, client):
    organization = await make_organization(session, name="Hotel chain")
    await make_user(session, organization, email="admin@hotel.example", role=Role.APPROVER)
    await session.commit()

    response = await client.post(
        TOKEN_URL, data={"username": "Admin@Hotel.example", "password": DEFAULT_PASSWORD}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == get_settings().access_token_lifetime_minutes * 60

    me = await client.get(ME_URL, headers={"Authorization": f"Bearer {body['access_token']}"})

    assert me.status_code == 200
    assert me.json()["email"] == "admin@hotel.example"
    assert me.json()["role"] == "APPROVER"
    assert me.json()["organization"] == {
        "publicId": str(organization.public_id),
        "name": "Hotel chain",
    }


@pytest.mark.parametrize(
    ("email", "password"),
    [
        ("admin@hotel.example", "wrong-password"),
        ("nobody@hotel.example", DEFAULT_PASSWORD),
    ],
    ids=["wrong password", "unknown email"],
)
async def test_login_rejects_bad_credentials(clean_db, session, client, email, password):
    organization = await make_organization(session)
    await make_user(session, organization, email="admin@hotel.example")
    await session.commit()

    response = await client.post(TOKEN_URL, data={"username": email, "password": password})

    _assert_invalid_credentials(response)


@pytest.mark.parametrize(
    ("user_active", "organization_active"),
    [(False, True), (True, False)],
    ids=["inactive user", "inactive buyer organisation"],
)
async def test_login_rejects_inactive_accounts(
    clean_db, session, client, user_active, organization_active
):
    organization = await make_organization(session, is_active=organization_active)
    await make_user(session, organization, email="admin@hotel.example", is_active=user_active)
    await session.commit()

    response = await client.post(
        TOKEN_URL, data={"username": "admin@hotel.example", "password": DEFAULT_PASSWORD}
    )

    _assert_invalid_credentials(response)


async def test_session_is_required(clean_db, client):
    _assert_invalid_credentials(await client.get(ME_URL))


async def test_session_is_refused_once_the_user_is_deactivated(clean_db, session, client):
    organization = await make_organization(session)
    user = await make_user(session, organization)
    headers = user_session_headers(user)
    user.is_active = False
    await session.commit()

    _assert_invalid_credentials(await client.get(ME_URL, headers=headers))


@pytest.mark.parametrize(
    "tamper",
    [
        lambda user: _sign(
            _session_claims(user), secret="not-the-jwt-secret-but-just-as-long-0123"
        ),
        lambda user: _sign(_session_claims(user, exp=int(datetime.now(UTC).timestamp()) - 60)),
        lambda user: _sign(_session_claims(user, aud="saint-elmo:agent")),
        lambda user: _sign(_session_claims(user, iss="someone-else")),
        lambda user: _sign(_session_claims(user, org_id=str(user.public_id))),
        lambda user: _sign({k: v for k, v in _session_claims(user).items() if k != "org_id"}),
        lambda user: {"Authorization": user_session_headers(user)["Authorization"][:-2] + "xx"},
        lambda user: {"Authorization": "Bearer not-a-jwt"},
    ],
    ids=[
        "wrong key",
        "expired",
        "wrong audience",
        "wrong issuer",
        "other buyer organisation",
        "missing org_id",
        "tampered signature",
        "malformed",
    ],
)
async def test_invalid_sessions_are_refused(clean_db, session, client, tamper):
    organization = await make_organization(session)
    user = await make_user(session, organization)
    await session.commit()

    _assert_invalid_credentials(await client.get(ME_URL, headers=tamper(user)))


async def test_user_session_scheme_is_in_openapi(client):
    schema = (await client.get("/openapi.json")).json()

    scheme = schema["components"]["securitySchemes"]["UserSession"]
    assert scheme["type"] == "oauth2"
    assert scheme["flows"]["password"]["tokenUrl"] == "/api/v1/auth/token"
    assert schema["paths"][ME_URL]["get"]["security"] == [{"UserSession": []}]
