from datetime import UTC, datetime, timedelta

from saint_elmo_backend.accounts.dtos import AuthenticatedUser, UserSessionClaims
from saint_elmo_backend.accounts.exceptions import InvalidCredentialsError
from saint_elmo_backend.core import exceptions, tokens
from saint_elmo_backend.core.settings import get_settings

ALGORITHM = "HS256"


# TODO(sw): add a better return type, i do not like tuples that much...
def sign(user: AuthenticatedUser) -> tuple[str, timedelta]:
    """
    Sign a user session. Returns the token and its lifetime.
    """

    settings = get_settings()
    now = datetime.now(UTC)
    lifetime = timedelta(minutes=settings.access_token_lifetime_minutes)

    token = tokens.sign(
        key=settings.jwt_secret.get_secret_value(),
        algorithm=ALGORITHM,
        audience=settings.user_token_audience,
        subject=user.public_id,
        organization_public_id=user.organization.public_id,
        issued_at=now,
        expires_at=now + lifetime,
        claims={"role": user.role},
    )
    return token, lifetime


def verify(token: str) -> UserSessionClaims:
    settings = get_settings()
    try:
        claims = tokens.verify(
            token,
            key=settings.jwt_secret.get_secret_value(),
            algorithm=ALGORITHM,
            audience=settings.user_token_audience,
        )
        return UserSessionClaims(
            user_public_id=tokens.uuid_claim(claims, "sub"),
            organization_public_id=tokens.uuid_claim(claims, "org_id"),
        )
    except exceptions.InvalidJWTError:
        raise InvalidCredentialsError() from None
