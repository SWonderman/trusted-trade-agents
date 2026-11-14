from typing import Literal

from pydantic import Field

from fastapi import APIRouter

type Language = Literal["en", "fi", "sv"]

router = APIRouter()


# TODO(#7): require auth once the auth ticket lands; the catalogue is global, non-tenant data
@router.post("/search")
async def search_products(
    query: str | None = Field(
        default=None,
        description="Free text matched against fi, sv and en names and texts at once",
    ),
    language: Language = Field(
        default="en",
        description="Language of the returned texts; falls back to fi when missing",
    ),
    limit: int = Field(default=20, ge=1, le=100),
    offset: int = Field(default=0, ge=0)
):
    pass
