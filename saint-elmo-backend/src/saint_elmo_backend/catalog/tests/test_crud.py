"""
Catalogue queries, run against the test database.
"""

from decimal import Decimal

from saint_elmo_backend.catalog import crud
from saint_elmo_backend.catalog.tests.factories import make_product


async def test_browse_without_query_matches_every_product(reference_data, session):
    milk = await make_product(session)
    butter = await make_product(session)

    products = await crud.search_products(session, limit=20, offset=0)

    assert {product.id for product in products} == {milk.id, butter.id}


async def test_browse_orders_by_reliability_desc_nulls_last_then_code(
    reference_data, session
):
    unknown = await make_product(session, code="100001", delivery_reliability=None)
    reliable_b = await make_product(session, code="100003", delivery_reliability=Decimal("0.95"))
    reliable_a = await make_product(session, code="100002", delivery_reliability=Decimal("0.95"))
    shaky = await make_product(session, code="100004", delivery_reliability=Decimal("0.40"))

    products = await crud.search_products(session, limit=20, offset=0)

    assert [product.id for product in products] == [
        reliable_a.id,
        reliable_b.id,
        shaky.id,
        unknown.id,
    ]


async def test_search_returns_the_requested_page(reference_data, session):
    await make_product(session, code="100001")
    second = await make_product(session, code="100002")
    third = await make_product(session, code="100003")
    await make_product(session, code="100004")

    products = await crud.search_products(session, limit=2, offset=1)

    assert [product.id for product in products] == [second.id, third.id]


async def test_count_without_query_counts_every_product(reference_data, session):
    await make_product(session)
    await make_product(session)

    assert await crud.count_products(session) == 2


async def test_search_returns_products_with_translations_loaded(reference_data, session):
    await make_product(session, code="100001", names={"en": "Milk", "fi": "Maito"})
    session.expunge_all()

    [product] = await crud.search_products(session, limit=20, offset=0)

    # Accessing an unloaded relationship on an async session raises, so this proves
    # the translations were loaded eagerly
    assert {t.language: t.name for t in product.translations} == {"en": "Milk", "fi": "Maito"}
