"""
Contract of the shared DB fixtures in the root conftest.
"""

from sqlalchemy import func, select

from saint_elmo_backend.catalog.models import (
    Allergen,
    ClaimElement,
    Label,
    Product,
    ProductTranslation,
)
from saint_elmo_backend.catalog.tests.factories import make_product
from saint_elmo_backend.db.engine import get_sessionmaker


async def test_reference_data_seeds_code_lists_and_no_products(reference_data, session):
    allergens = set((await session.scalars(select(Allergen.code))).all())
    claim_elements = set((await session.scalars(select(ClaimElement.code))).all())
    labels = set((await session.scalars(select(Label.code))).all())

    assert {"AM", "AW"} <= allergens
    assert "LACTOSE" in claim_elements
    assert "EU_ORGANIC_FARMING" in labels
    assert await session.scalar(select(func.count()).select_from(Product)) == 0
    assert await session.scalar(select(func.count()).select_from(ProductTranslation)) == 0


async def test_client_app_reads_the_test_database(reference_data, session, client):
    product = await make_product(session, names={"en": "Smoke test milk"})
    await session.commit()

    response = await client.get("/")
    async with get_sessionmaker()() as app_session:
        name = await app_session.scalar(
            select(ProductTranslation.name).where(ProductTranslation.product_id == product.id)
        )

    assert response.status_code == 200
    assert name == "Smoke test milk"
