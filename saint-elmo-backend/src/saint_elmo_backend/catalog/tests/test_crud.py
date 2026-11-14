"""
Catalogue queries, run against the test database.
"""

from saint_elmo_backend.catalog import crud
from saint_elmo_backend.catalog.tests.factories import make_product


async def test_browse_without_query_matches_every_product(reference_data, session):
    milk = await make_product(session)
    butter = await make_product(session)

    product_ids = await crud.search_product_ids(session, limit=20, offset=0)

    assert set(product_ids) == {milk.id, butter.id}


async def test_count_without_query_counts_every_product(reference_data, session):
    await make_product(session)
    await make_product(session)

    assert await crud.count_products(session) == 2


async def test_load_products_returns_them_with_translations(reference_data, session):
    milk = await make_product(session, code="100001", names={"en": "Milk", "fi": "Maito"})
    await make_product(session)
    session.expunge_all()

    [loaded] = await crud.load_products(session, [milk.id])

    assert loaded.code == "100001"
    assert {t.language: t.name for t in loaded.translations} == {"en": "Milk", "fi": "Maito"}
