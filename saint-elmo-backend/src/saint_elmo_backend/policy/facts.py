"""
Builds the policy's input from the catalog and live offers, for quotes and orders.
"""

from saint_elmo_backend.catalog.dtos import ClaimCode
from saint_elmo_backend.catalog.models import Product
from saint_elmo_backend.offers.dtos import OfferLine
from saint_elmo_backend.offers.enums import OfferReasonCode
from saint_elmo_backend.policy.dtos import LineOffer, ProductFacts


def product_facts(product: Product) -> ProductFacts:
    """
    What the policy judges about a product. Load it with
    `catalog.crud.get_products_with_facts`.
    """
    return ProductFacts(
        category_code=product.category.code,
        vendor=product.vendor.name,
        country_of_origin=product.country_of_origin,
        claims=tuple(
            ClaimCode(type=claim.claim_type_code, element=claim.claim_element_code)
            for claim in product.claims
        ),
        labels=tuple(label.label_code for label in product.labels),
        diets=tuple(diet.diet_code for diet in product.diets),
        allergens={allergen.allergen_code: allergen.containment for allergen in product.allergens},
        delivery_reliability=product.delivery_reliability,
    )


def line_offer(offer: OfferLine) -> LineOffer:
    """
    An offer requested with a quantity, as the policy reads it.
    """
    assert offer.quantity is not None
    availability = offer.availability
    return LineOffer(
        unit_price=offer.price.per_sales_unit.net if offer.price else None,
        sales_blocked=availability.sales_blocked if availability else False,
        earliest_date=availability.earliest_date if availability else None,
        closing_time=availability.closing_time if availability else None,
        closing_time_passed=OfferReasonCode.CLOSING_TIME_PASSED in offer.reason_codes,
        logistic_model=availability.logistic_model if availability else None,
        available_amount=availability.available_amount if availability else None,
        quantity=offer.quantity.converted,
        line_total=offer.quantity.line_total.net if offer.quantity.line_total else None,
    )
