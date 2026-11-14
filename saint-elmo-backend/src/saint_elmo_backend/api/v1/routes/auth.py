from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from saint_elmo_backend.accounts import services, tokens
from saint_elmo_backend.accounts.exceptions import InvalidCredentialsError
from saint_elmo_backend.accounts.schemas import AccessTokenResponse, MeOutput
from saint_elmo_backend.api.annotations import ASession
from saint_elmo_backend.api.exceptions import InvalidCredentials, to_response_error
from saint_elmo_backend.api.v1.auth import CurrentUser

router = APIRouter()


@router.post(
    "/token",
    response_model=AccessTokenResponse,
    responses=to_response_error(InvalidCredentials),
)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: ASession,
) -> AccessTokenResponse:
    """
    OAuth 2.0 password grant: `username` is the user's email. The frontend keeps the
    returned token in an httpOnly cookie and forwards it as `Authorization: Bearer`.
    """

    try:
        user = await services.authenticate_user(
            session, email=form_data.username, password=form_data.password
        )
    except InvalidCredentialsError:
        raise InvalidCredentials(detail="Incorrect email or password") from None

    access_token, lifetime = tokens.sign(user)
    return AccessTokenResponse(
        access_token=access_token,
        expires_in=int(lifetime.total_seconds()),
    )


@router.get(
    "/me",
    response_model=MeOutput,
    responses=to_response_error(InvalidCredentials),
)
async def me(user: CurrentUser) -> MeOutput:
    return MeOutput.from_user(user)
