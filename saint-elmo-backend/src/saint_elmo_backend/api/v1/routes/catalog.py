from fastapi import APIRouter, Depends

from saint_elmo_backend.agents.enums import Scope
from saint_elmo_backend.api.annotations import ASession
from saint_elmo_backend.api.exceptions import (
    InvalidCredentials,
    PermissionDenied,
    to_response_error,
)
from saint_elmo_backend.api.v1.auth import authenticate
from saint_elmo_backend.catalog import services
from saint_elmo_backend.catalog.schemas import VocabularyResponse

# The catalogue is global, so the principal only gates access: it doesn't filter results
router = APIRouter(
    dependencies=[Depends(authenticate(users=True, agent_scope=Scope.CATALOG_READ))],
    responses=to_response_error(InvalidCredentials, PermissionDenied),
)


@router.get(
    "/vocabulary",
    response_model=VocabularyResponse,
    summary="List the filter codes products use",
    description="The claim, diet, label, allergen and category codes at least one product "
    "uses, with their GS1 name, definition and product count. Use it to discover valid "
    "search filter codes instead of guessing them.",
)
async def get_vocabulary(session: ASession) -> VocabularyResponse:
    return VocabularyResponse.from_vocabulary(await services.get_vocabulary(session))
