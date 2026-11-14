from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from saint_elmo_backend.api.dependencies import (
    get_offer_cache,
    get_session,
    get_valio_aimo_client,
)
from saint_elmo_backend.offers.cache import OfferCache
from saint_elmo_backend.valio_aimo.client import ValioAimoClient

ASession = Annotated[AsyncSession, Depends(get_session)]
AValioAimoClient = Annotated[ValioAimoClient, Depends(get_valio_aimo_client)]
AOfferCache = Annotated[OfferCache, Depends(get_offer_cache)]
