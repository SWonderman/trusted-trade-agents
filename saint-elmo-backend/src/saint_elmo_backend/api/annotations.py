from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from saint_elmo_backend.api.dependencies import get_session

ASession = Annotated[AsyncSession, Depends(get_session)]
