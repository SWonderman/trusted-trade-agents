"""
Catalogue queries, run against the test database.
"""

from decimal import Decimal

import pytest

from saint_elmo_backend.catalog import crud
from saint_elmo_backend.catalog.tests.factories import make_product


async def test_browse_without_query_matches_every_product(reference_data, session):
    milk = await make_product(session)
    butter = await make_product(session)

    matches = await crud.search_products(session, query=None, limit=20, offset=0)

    assert {match.product.id for match in matches} == {milk.id, butter.id}


async def test_browse_orders_by_reliability_desc_nulls_last_then_code(
    reference_data, session
):
    unknown = await make_product(session, code="100001", delivery_reliability=None)
    reliable_b = await make_product(session, code="100003", delivery_reliability=Decimal("0.95"))
    reliable_a = await make_product(session, code="100002", delivery_reliability=Decimal("0.95"))
    shaky = await make_product(session, code="100004", delivery_reliability=Decimal("0.40"))

    matches = await crud.search_products(session, query=None, limit=20, offset=0)

    assert [match.product.id for match in matches] == [
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

    matches = await crud.search_products(session, query=None, limit=2, offset=1)

    assert [match.product.id for match in matches] == [second.id, third.id]


async def test_count_without_query_counts_every_product(reference_data, session):
    await make_product(session)
    await make_product(session)

    assert await crud.count_products(session, query=None) == 2


async def test_search_returns_products_with_translations_loaded(reference_data, session):
    await make_product(session, code="100001", names={"en": "Milk", "fi": "Maito"})
    session.expunge_all()

    [match] = await crud.search_products(session, query=None, limit=20, offset=0)

    # Accessing an unloaded relationship on an async session raises, so this proves
    # the translations were loaded eagerly
    assert {t.language: t.name for t in match.product.translations} == {"en": "Milk", "fi": "Maito"}


@pytest.mark.parametrize("query", ["milk", "maito", "mjölk"], ids=["en", "fi", "sv"])
async def test_query_finds_a_product_by_its_name_in_each_language(
    reference_data, session, query
):
    milk = await make_product(
        session,
        names={"en": "Lactose free milk", "fi": "Laktoositon maito", "sv": "Laktosfri mjölk"},
    )
    await make_product(session, names={"en": "Butter", "fi": "Voi", "sv": "Smör"})

    matches = await crud.search_products(session, query=query, limit=20, offset=0)

    assert [match.product.id for match in matches] == [milk.id]


async def test_query_ranks_a_name_match_above_a_marketing_text_match(reference_data, session):
    # The text match is more reliable, so it would come first if ranking were ignored
    text_match = await make_product(
        session,
        names={"en": "Cocoa drink"},
        marketing_texts={"en": "Tastes best with cold milk"},
        delivery_reliability=Decimal("0.99"),
    )
    name_match = await make_product(
        session, names={"en": "Whole milk"}, delivery_reliability=Decimal("0.10")
    )

    matches = await crud.search_products(session, query="milk", limit=20, offset=0)

    assert [match.product.id for match in matches] == [name_match.id, text_match.id]
    name_relevance, text_relevance = (match.relevance for match in matches)
    assert name_relevance is not None and text_relevance is not None
    assert name_relevance > text_relevance


async def test_product_matching_in_several_languages_is_returned_once(reference_data, session):
    await make_product(session, names={"en": "Oat milk", "sv": "Havremjölk med milk"})

    matches = await crud.search_products(session, query="milk", limit=20, offset=0)

    assert len(matches) == 1
    assert await crud.count_products(session, query="milk") == 1


async def test_count_with_query_counts_only_matches(reference_data, session):
    await make_product(session, names={"en": "Whole milk"})
    await make_product(session, names={"en": "Skimmed milk"})
    await make_product(session, names={"en": "Butter"})

    assert await crud.count_products(session, query="milk") == 2


async def test_browse_has_no_relevance(reference_data, session):
    await make_product(session)

    [match] = await crud.search_products(session, query=None, limit=20, offset=0)

    assert match.relevance is None


async def test_misspelled_query_finds_the_product_by_trigram_similarity(
    reference_data, session
):
    milk = await make_product(session, names={"en": "Lactose free milk"})
    await make_product(session, names={"en": "Butter"})

    matches = await crud.search_products(session, query="lactose fre mlik", limit=20, offset=0)

    assert [match.product.id for match in matches] == [milk.id]
    assert await crud.count_products(session, query="lactose fre mlik") == 1


async def test_text_match_ranks_above_a_fuzzy_match(reference_data, session):
    # The fuzzy match is more reliable, so it would come first if ranking were ignored
    fuzzy = await make_product(
        session, names={"en": "Milkk"}, delivery_reliability=Decimal("0.99")
    )
    exact = await make_product(
        session, names={"en": "Whole milk"}, delivery_reliability=Decimal("0.10")
    )

    matches = await crud.search_products(session, query="milk", limit=20, offset=0)

    assert [match.product.id for match in matches] == [exact.id, fuzzy.id]


@pytest.mark.parametrize("query", [None, "milk"], ids=["browse", "query"])
async def test_search_loads_category_vendor_and_brand(reference_data, session, query):
    await make_product(
        session, names={"en": "Milk"}, category="C200", vendor="Valio Oy", brand="Valio"
    )
    session.expunge_all()

    [match] = await crud.search_products(session, query=query, limit=20, offset=0)

    assert match.product.category.code == "C200"
    assert match.product.vendor.name == "Valio Oy"
    assert match.product.brand is not None
    assert match.product.brand.name == "Valio"


@pytest.mark.parametrize("query", [None, "milk"], ids=["browse", "query"])
async def test_search_loads_units_deposits_claims_diets_and_labels(
    reference_data, session, query
):
    await make_product(
        session,
        names={"en": "Milk"},
        base_unit="ST",
        units={"ST": Decimal("1"), "KI": Decimal("12")},
        deposits=["PANT1"],
        claims=[("FREE_FROM", "LACTOSE")],
        diets=["VEGAN"],
        labels=["EU_ORGANIC_FARMING"],
    )
    session.expunge_all()

    [match] = await crud.search_products(session, query=query, limit=20, offset=0)

    product = match.product
    assert {unit.unit_code: unit.size_in_base_units for unit in product.units} == {
        "ST": Decimal("1"),
        "KI": Decimal("12"),
    }
    assert [deposit.material_code for deposit in product.deposits] == ["PANT1"]
    assert [(c.claim_type_code, c.claim_element_code) for c in product.claims] == [
        ("FREE_FROM", "LACTOSE")
    ]
    assert [diet.diet_code for diet in product.diets] == ["VEGAN"]
    assert [label.label_code for label in product.labels] == ["EU_ORGANIC_FARMING"]
