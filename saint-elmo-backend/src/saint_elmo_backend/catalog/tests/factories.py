"""
Insert catalogue rows for integration tests.

The catalogue is read-only at runtime, so tests arrange it directly in the
database. Claim, diet, label and allergen codes must exist in the code-list tables:
request the `reference_data` fixture.
"""

from collections.abc import Sequence
from decimal import Decimal
from itertools import count
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from saint_elmo_backend.catalog.enums import AllergenContainment
from saint_elmo_backend.catalog.models import (
    Brand,
    Category,
    Product,
    ProductAllergen,
    ProductClaim,
    ProductDiet,
    ProductLabel,
    ProductTranslation,
    ProductUnit,
    Vendor,
)

_codes = count(900000)


async def _get_or_create[T](session: AsyncSession, model: type[T], **key: Any) -> T:
    row = await session.scalar(select(model).filter_by(**key))
    if row is None:
        row = model(**key)
        session.add(row)
    return row


async def make_product(
    session: AsyncSession,
    *,
    code: str | None = None,
    names: dict[str, str] | None = None,
    marketing_texts: dict[str, str] | None = None,
    category: str = "C100",
    vendor: str = "Test Vendor",
    brand: str | None = None,
    sales_unit: str = "ST",
    base_unit: str = "ST",
    allowed_lot_size: Decimal = Decimal("0.01"),
    units: dict[str, Decimal] | None = None,
    claims: Sequence[tuple[str, str]] = (),
    diets: Sequence[str] = (),
    labels: Sequence[str] = (),
    allergens: dict[str, AllergenContainment] | None = None,
    **fields: Any,
) -> Product:
    """
    One product with the given attributes; every other column is left at its
    model default. Category, vendor and brand are reused by name.
    """
    code = code or str(next(_codes))
    names = names or {"en": f"Test product {code}"}
    marketing_texts = marketing_texts or {}
    units = units or {base_unit: Decimal("1")}

    product = Product(
        code=code,
        sales_unit=sales_unit,
        base_unit=base_unit,
        allowed_lot_size=allowed_lot_size,
        category=await _get_or_create(session, Category, code=category),
        vendor=await _get_or_create(session, Vendor, name=vendor),
        brand=await _get_or_create(session, Brand, name=brand) if brand else None,
        translations=[
            ProductTranslation(
                language=language,
                name=names.get(language),
                marketing_text=marketing_texts.get(language),
            )
            for language in names | marketing_texts
        ],
        units=[
            ProductUnit(unit_code=unit_code, size_in_base_units=size)
            for unit_code, size in units.items()
        ],
        claims=[
            ProductClaim(claim_type_code=claim_type, claim_element_code=element)
            for claim_type, element in claims
        ],
        diets=[ProductDiet(diet_code=diet) for diet in diets],
        labels=[ProductLabel(label_code=label) for label in labels],
        allergens=[
            ProductAllergen(allergen_code=allergen, containment=containment)
            for allergen, containment in (allergens or {}).items()
        ],
        **fields,
    )
    session.add(product)
    await session.flush()
    return product
