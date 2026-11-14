"""
Load the vendored GS1 code lists into their reference tables.

Upserts by code, so names and definitions follow the XML files on every run, and
non-standard codes the catalogue seeder added are upgraded once GS1 lists them.
"""

from loguru import logger
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from saint_elmo_backend.catalog import code_lists
from saint_elmo_backend.catalog.models import (
    ActivityType,
    Allergen,
    ClaimElement,
    ClaimType,
    Diet,
    FishingArea,
    FishingMethod,
    Label,
    MeasurementUnit,
    Nutrient,
)

CODE_LIST_MODELS: dict[str, type] = {
    code_lists.ALLERGEN_TYPE: Allergen,
    code_lists.NUTRIENT_TYPE: Nutrient,
    code_lists.MEASUREMENT_UNIT: MeasurementUnit,
    code_lists.CLAIM_TYPE: ClaimType,
    code_lists.CLAIM_ELEMENT: ClaimElement,
    code_lists.DIET_TYPE: Diet,
    code_lists.PACKAGING_LABEL: Label,
    code_lists.PRODUCT_ACTIVITY_TYPE: ActivityType,
    code_lists.CATCH_METHOD: FishingMethod,
    code_lists.CATCH_AREA: FishingArea,
}


async def seed_code_lists(session: AsyncSession) -> None:
    for list_name, model in CODE_LIST_MODELS.items():
        entries = code_lists.load_code_list(list_name)
        statement = insert(model).values(
            [
                {
                    "code": e.code,
                    "name": e.name,
                    "definition": e.definition,
                    "is_standard": e.is_standard,
                }
                for e in entries.values()
            ]
        )
        await session.execute(
            statement.on_conflict_do_update(
                index_elements=["code"],
                set_={
                    "name": statement.excluded.name,
                    "definition": statement.excluded.definition,
                    "is_standard": statement.excluded.is_standard,
                },
            )
        )

    logger.info(f"GS1 code lists loaded: {len(CODE_LIST_MODELS)} lists")
