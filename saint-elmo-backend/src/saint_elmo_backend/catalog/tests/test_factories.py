from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from saint_elmo_backend.catalog.enums import AllergenContainment
from saint_elmo_backend.catalog.models import Product
from saint_elmo_backend.catalog.tests.factories import make_product


async def _load(session, code: str) -> Product:
    session.expunge_all()
    return await session.scalar(
        select(Product)
        .where(Product.code == code)
        .options(
            selectinload(Product.category),
            selectinload(Product.vendor),
            selectinload(Product.brand),
            selectinload(Product.translations),
            selectinload(Product.units),
            selectinload(Product.claims),
            selectinload(Product.diets),
            selectinload(Product.labels),
            selectinload(Product.allergens),
        )
    )


async def test_make_product_round_trips_every_attribute(reference_data, session):
    await make_product(
        session,
        code="463038",
        names={"en": "Lactose free milk drink 10 l", "fi": "Laktoositon maitojuoma 10 l"},
        category="C101",
        vendor="Valio",
        brand="Valio Eila",
        sales_unit="KI",
        base_unit="ST",
        units={"ST": Decimal("1"), "KI": Decimal("2")},
        claims=[("FREE_FROM", "LACTOSE")],
        diets=["VEGETARIAN"],
        labels=["EU_ORGANIC_FARMING"],
        allergens={"AM": AllergenContainment.CONTAINS, "AW": AllergenContainment.FREE_FROM},
        delivery_reliability=Decimal("0.95"),
        carbon_footprint=Decimal("1.230"),
        country_of_origin="fi",
    )
    await session.commit()

    product = await _load(session, "463038")

    assert product.category.code == "C101"
    assert product.vendor.name == "Valio"
    assert product.brand is not None
    assert product.brand.name == "Valio Eila"
    assert {t.language: t.name for t in product.translations} == {
        "en": "Lactose free milk drink 10 l",
        "fi": "Laktoositon maitojuoma 10 l",
    }
    assert product.sales_unit == "KI"
    assert {u.unit_code: u.size_in_base_units for u in product.units} == {
        "ST": Decimal("1"),
        "KI": Decimal("2"),
    }
    assert [(c.claim_type_code, c.claim_element_code) for c in product.claims] == [
        ("FREE_FROM", "LACTOSE")
    ]
    assert [d.diet_code for d in product.diets] == ["VEGETARIAN"]
    assert [lbl.label_code for lbl in product.labels] == ["EU_ORGANIC_FARMING"]
    assert {a.allergen_code: a.containment for a in product.allergens} == {
        "AM": AllergenContainment.CONTAINS,
        "AW": AllergenContainment.FREE_FROM,
    }
    assert product.delivery_reliability == Decimal("0.950")
    assert product.carbon_footprint == Decimal("1.230")
    assert product.country_of_origin == "fi"


async def test_make_product_defaults_and_shares_category_and_vendor(reference_data, session):
    first = await make_product(session)
    second = await make_product(session)
    await session.commit()

    assert first.code != second.code
    assert first.category_id == second.category_id
    assert first.vendor_id == second.vendor_id
    assert first.brand_id is None

    product = await _load(session, first.code)
    assert [t.language for t in product.translations] == ["en"]
    assert [(u.unit_code, u.size_in_base_units) for u in product.units] == [
        ("ST", Decimal("1"))
    ]
    assert product.claims == []
    assert product.allergens == []
    assert product.delivery_reliability is None
