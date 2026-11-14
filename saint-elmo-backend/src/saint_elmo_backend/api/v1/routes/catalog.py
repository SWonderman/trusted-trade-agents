from fastapi import APIRouter

from saint_elmo_backend.api.annotations import ASession
from saint_elmo_backend.catalog import services
from saint_elmo_backend.catalog.schemas import VocabularyResponse

router = APIRouter()


# TODO(#7): require auth once the auth ticket lands; the catalogue is global, non-tenant data
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
