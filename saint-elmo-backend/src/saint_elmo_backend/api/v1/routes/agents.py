from typing import Annotated

from fastapi import APIRouter, Depends

from saint_elmo_backend.agents.enums import Scope
from saint_elmo_backend.api.annotations import ASession
from saint_elmo_backend.api.exceptions import (
    InvalidCredentials,
    MandateNotFound,
    PermissionDenied,
    to_response_error,
)
from saint_elmo_backend.api.v1.auth import Principal, authenticate
from saint_elmo_backend.mandates import services as mandate_services
from saint_elmo_backend.mandates.exceptions import MandateNotFoundError
from saint_elmo_backend.mandates.schemas import MandateResponse

router = APIRouter()


@router.get(
    "/me/mandate",
    response_model=MandateResponse,
    responses=to_response_error(InvalidCredentials, PermissionDenied, MandateNotFound),
    summary="Read the calling agent's mandate",
    description="Every limit Saint Elmo applies to this agent's quotes and orders, and "
    "how much of the current spend period is left. Use it to pre-check a proposal before "
    "quoting. The mandate is the one the Agent token's agent holds now; an agent can read "
    "it but never change it.",
)
async def get_my_mandate(
    principal: Annotated[Principal, Depends(authenticate(agent_scope=Scope.MANDATE_READ))],
    session: ASession,
) -> MandateResponse:
    assert principal.agent is not None
    try:
        mandate = await mandate_services.get_agent_mandate(
            session, organization_id=principal.organization.id, agent_id=principal.agent.id
        )
    except MandateNotFoundError as exc:
        raise MandateNotFound() from exc
    return MandateResponse.from_mandate(principal.agent, mandate)
