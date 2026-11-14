"""
Ranked substitutes for a product that can't meet a need.

Candidates are generated deterministically: the product's curated substitutes, then
products in its category, both passing the mandate's requirements plus the request's
filters and expressible in the buyer unit. At most `MAX_CANDIDATES` of them
are priced from live offers, ranked (`ranking.py`) and previewed by the policy as a
substitute line for the original.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from saint_elmo_backend.audit import services as audit_services
from saint_elmo_backend.audit.enums import AuditEventType
from saint_elmo_backend.catalog import crud as catalog_crud
from saint_elmo_backend.catalog import services as catalog_services
from saint_elmo_backend.catalog.dtos import ClaimCode, ProductFilters
from saint_elmo_backend.catalog.exceptions import ProductNotFoundError, UnknownCodesError
from saint_elmo_backend.catalog.models import Product
from saint_elmo_backend.core.calendar import BUYER_TIMEZONE
from saint_elmo_backend.mandates import services as mandate_services
from saint_elmo_backend.mandates.dtos import AgentMandate, MandateTerms
from saint_elmo_backend.offers import services as offer_services
from saint_elmo_backend.offers.cache import OfferCache
from saint_elmo_backend.offers.dtos import OfferLine, RequestedProduct
from saint_elmo_backend.offers.quantity import BUYER_UNITS, may_express
from saint_elmo_backend.policy.dtos import (
    PolicyInput,
    PolicyJudgement,
    PolicyLine,
    SubstitutedProduct,
)
from saint_elmo_backend.policy.engine import evaluate
from saint_elmo_backend.policy.facts import line_offer, product_facts
from saint_elmo_backend.policy.schemas import PolicyReasonOut
from saint_elmo_backend.substitutes.dtos import (
    Substitute,
    Substitutes,
    SubstitutesRequest,
    TradeOffs,
)
from saint_elmo_backend.substitutes.enums import SubstitutesReasonCode
from saint_elmo_backend.substitutes.ranking import CandidateFacts, rank_candidates
from saint_elmo_backend.valio_aimo.client import ValioAimoClient

# Live offers are fetched for at most this many candidates
MAX_CANDIDATES = 50
# The preview judges the candidate as the only line of a quote
_PREVIEW_LINE_REF = "1"
_PCT_STEP = Decimal("0.01")


@dataclass(frozen=True, slots=True)
class _Priced:
    """
    A product with its live offer for the need, and the offer as the response shows it.
    """

    product: Product
    # For the need's quantity in the buyer unit: what is ranked, compared and previewed
    offer: OfferLine
    # With a quantity only when the request had one
    shown: OfferLine


async def find_substitutes(
    session: AsyncSession,
    valio_aimo: ValioAimoClient,
    cache: OfferCache,
    *,
    organization_id: int,
    agent_id: int,
    product_code: str,
    request: SubstitutesRequest,
    now: datetime,
    ignore_closing_time: bool = False,
) -> Substitutes:
    """
    Raises `ProductNotFoundError`, `UnknownCodesError` for filters naming unknown codes,
    `MandateNotFoundError`, and whatever `offers.services.get_offers` raises.

    Records SUBSTITUTES_REQUESTED. A composable building block: the caller owns the commit.
    """
    found = await catalog_crud.get_products_with_facts(session, [product_code])
    if not found:
        raise ProductNotFoundError(product_code)
    original = found[0]
    if unknown := await catalog_services.unknown_filter_codes(session, request.filters):
        raise UnknownCodesError(unknown)

    mandate = await mandate_services.get_agent_mandate(
        session, organization_id=organization_id, agent_id=agent_id, now=now
    )
    # The one date the backend picks (ADR 0002), echoed in the response
    deliver_by = request.deliver_by or now.astimezone(BUYER_TIMEZONE).date() + timedelta(days=1)

    async def offers_for(requested: Sequence[RequestedProduct]) -> list[OfferLine]:
        offers = await offer_services.get_offers(
            session,
            valio_aimo,
            cache,
            organization_id=organization_id,
            deliver_by=deliver_by,
            requested=requested,
            language=request.language,
            now=now,
            ignore_closing_time=ignore_closing_time,
        )
        return offers.lines

    # Without a quantity, prices are compared, and previews judged, for one buyer unit
    quantity, buyer_unit = request.quantity, request.unit
    if quantity is None:
        [probe] = await offers_for([RequestedProduct(original.code)])
        quantity, buyer_unit = Decimal(1), _comparison_unit(probe)
    buyer_unit = (buyer_unit or original.sales_unit).upper()

    products, curated = await _candidates(session, original, mandate.terms, request, buyer_unit)
    all_products = [original, *products.values()]
    requested = [RequestedProduct(p.code, quantity, buyer_unit) for p in all_products]
    if request.quantity is None:
        # The same products without a quantity, as the response shows them
        requested += [RequestedProduct(p.code) for p in all_products]
    lines = await offers_for(requested)
    offers = lines[: len(all_products)]
    shown = lines[len(all_products) :] if request.quantity is None else offers
    original_priced, *candidates_priced = (
        _Priced(product, offer, shown_offer)
        for product, offer, shown_offer in zip(all_products, offers, shown, strict=True)
    )

    # The live conversion is decisive: a candidate it can't express is no candidate
    expressible = {c.product.code: c for c in candidates_priced if _expressible(c.offer)}
    ranked = rank_candidates(
        [
            _candidate_facts(candidate, original, code in curated)
            for code, candidate in expressible.items()
        ]
    )[: request.limit]

    candidates: list[Substitute] = []
    for ranked_candidate in ranked:
        candidate = expressible[ranked_candidate.facts.product_code]
        candidates.append(
            Substitute(
                ranked=ranked_candidate,
                offer=candidate.shown,
                trade_offs=_trade_offs(candidate, original_priced),
                policy_preview=_preview(candidate, original_priced, mandate, deliver_by),
            )
        )
    substitutes = Substitutes(
        original=original_priced.shown,
        deliver_by=deliver_by,
        buyer_unit=buyer_unit,
        evaluated_at=now,
        candidates=candidates,
        reason_codes=() if candidates else (SubstitutesReasonCode.NO_SUBSTITUTES_FOUND,),
        mandate_version=mandate.version,
    )

    await audit_services.record_event(
        session,
        organization_id=organization_id,
        event_type=AuditEventType.SUBSTITUTES_REQUESTED,
        agent_id=agent_id,
        payload=_audit_payload(
            product_code, request, substitutes, priced_candidates=list(products)
        ),
    )
    return substitutes


def _comparison_unit(offer: OfferLine) -> str | None:
    unit = offer.price.comparison_unit if offer.price else None
    return unit.upper() if unit and unit.upper() in BUYER_UNITS else None


def _requirements(terms: MandateTerms, filters: ProductFilters) -> ProductFilters | None:
    """
    The mandate's requirements with the request's filters added, and its blocked
    categories and vendors left out: required codes and excluded allergens are united,
    allowed origins intersected. None when the two origin lists share no country, so
    nothing can satisfy both.

    The mandate's minimum reliability is left out: unlike a search filter, it lets
    products without reliability data through (see `_meets_reliability`).
    """
    countries = filters.countries_of_origin or terms.allowed_countries_of_origin
    if terms.allowed_countries_of_origin and filters.countries_of_origin:
        countries = tuple(
            c for c in filters.countries_of_origin if c in terms.allowed_countries_of_origin
        )
        if not countries:
            return None

    return ProductFilters(
        required_claims=_union(terms.required_claims, filters.required_claims),
        required_diets=_union(terms.required_diets, filters.required_diets),
        required_labels=_union(terms.required_labels, filters.required_labels),
        excluded_allergens=_union(terms.excluded_allergens, filters.excluded_allergens),
        allergen_strictness=terms.allergen_strictness,
        countries_of_origin=countries,
        min_delivery_reliability=filters.min_delivery_reliability,
        # The policy rejects these whatever an approver says. Categories and vendors
        # merely not on the allowed lists stay, for a human to decide (NEEDS_HUMAN)
        excluded_category_codes=terms.blocked_category_codes,
        excluded_vendors=terms.blocked_vendors,
    )


async def _candidates(
    session: AsyncSession,
    original: Product,
    terms: MandateTerms,
    request: SubstitutesRequest,
    buyer_unit: str,
) -> tuple[dict[str, Product], set[str]]:
    """
    Up to `MAX_CANDIDATES` products by code, curated substitutes first, then the rest of
    the category, most reliable first; and the curated codes.
    """
    filters = _requirements(terms, request.filters)
    if filters is None:
        return {}, set()

    curated = await catalog_crud.curated_substitute_codes(session, original.id)
    matches = [
        *(
            await catalog_crud.matching_product_codes(
                session, replace(filters, product_codes=tuple(curated))
            )
            if curated
            else []
        ),
        *await catalog_crud.matching_product_codes(
            session, replace(filters, category_codes=(original.category.code,))
        ),
    ]
    codes = [code for code in dict.fromkeys(matches) if code != original.code]
    products = {p.code: p for p in await catalog_crud.get_products_with_facts(session, codes)}
    eligible = [
        code
        for code in codes
        if _meets_reliability(products[code], terms.min_delivery_reliability)
        and may_express(buyer_unit, offer_services.product_measures(products[code]))
    ]
    return {code: products[code] for code in eligible[:MAX_CANDIDATES]}, set(curated)


def _meets_reliability(product: Product, minimum: Decimal | None) -> bool:
    # As the policy judges it: no reliability data doesn't trigger the minimum
    reliability = product.delivery_reliability
    return minimum is None or reliability is None or reliability >= minimum


def _expressible(offer: OfferLine) -> bool:
    """
    Whether the live conversion could express the need in the product's sales units.
    """
    return offer.quantity is not None and offer.quantity.converted.sales_units is not None


def _candidate_facts(candidate: _Priced, original: Product, curated: bool) -> CandidateFacts:
    product, offer = candidate.product, candidate.offer
    availability = offer.availability
    quantity = offer.quantity
    return CandidateFacts(
        product_code=product.code,
        curated=curated,
        meets_deadline=bool(
            availability and availability.meets_deadline and not availability.sales_blocked
        ),
        # An unknown available amount (TERMINAL) counts as covering
        covers_quantity=availability is not None
        and not (quantity and quantity.covered_by_availability is False),
        price_per_buyer_unit=line_offer(offer).price_per_buyer_unit,
        delivery_reliability=product.delivery_reliability,
        labels_gained=len(_labels(product) - _labels(original)),
        carbon_footprint=product.carbon_footprint,
    )


def _trade_offs(candidate: _Priced, original_priced: _Priced) -> TradeOffs:
    product, offer = candidate.product, candidate.offer
    original, original_offer = original_priced.product, original_priced.offer
    price = line_offer(offer).price_per_buyer_unit
    original_price = line_offer(original_offer).price_per_buyer_unit
    earliest = offer.availability.earliest_date if offer.availability else None
    original_earliest = (
        original_offer.availability.earliest_date if original_offer.availability else None
    )
    claims, original_claims = _claims(product), _claims(original)
    labels, original_labels = _labels(product), _labels(original)
    return TradeOffs(
        price_per_buyer_unit_delta_pct=(
            ((price - original_price) / original_price * 100).quantize(
                _PCT_STEP, rounding=ROUND_HALF_UP
            )
            if price is not None and original_price
            else None
        ),
        earliest_date_delta=_days_between(original_earliest, earliest),
        reliability_delta=_delta(original.delivery_reliability, product.delivery_reliability),
        claims_kept=_sorted_claims(c for c in original_claims if c in claims),
        claims_lost=_sorted_claims(c for c in original_claims if c not in claims),
        labels_gained=sorted(labels - original_labels),
        labels_lost=sorted(original_labels - labels),
        carbon_footprint_delta=_delta(original.carbon_footprint, product.carbon_footprint),
    )


def _preview(
    candidate: _Priced, original: _Priced, mandate: AgentMandate, deliver_by: date
) -> PolicyJudgement:
    return evaluate(
        PolicyInput(
            mandate=mandate.terms,
            lines=(
                PolicyLine(
                    line_ref=_PREVIEW_LINE_REF,
                    product=product_facts(candidate.product),
                    offer=line_offer(candidate.offer),
                    substitutes_for=SubstitutedProduct(
                        original.product.code, line_offer(original.offer)
                    ),
                ),
            ),
            deliver_by=deliver_by,
            period_spend=mandate.period_spend.committed,
            category_period_spend=mandate.period_spend.committed_by_category,
        )
    )


def _audit_payload(
    product_code: str,
    request: SubstitutesRequest,
    substitutes: Substitutes,
    *,
    priced_candidates: list[str],
) -> dict[str, Any]:
    """
    The request, which candidates were priced, and those returned with their ranks,
    scores and previews. In the API's JSON shape: amounts as numbers, camelCase keys.
    """
    filters = request.filters
    return {
        "productCode": product_code,
        "request": {
            "quantity": float(request.quantity) if request.quantity is not None else None,
            "unit": request.unit,
            "deliverBy": request.deliver_by.isoformat() if request.deliver_by else None,
            "requiredClaims": [
                {"type": c.type, "element": c.element} for c in filters.required_claims
            ],
            "requiredLabels": list(filters.required_labels),
            "requiredDiets": list(filters.required_diets),
            "excludedAllergens": list(filters.excluded_allergens),
            "countriesOfOrigin": list(filters.countries_of_origin),
            "minDeliveryReliability": float(filters.min_delivery_reliability)
            if filters.min_delivery_reliability is not None
            else None,
            "limit": request.limit,
        },
        "deliverBy": substitutes.deliver_by.isoformat(),
        "buyerUnit": substitutes.buyer_unit,
        "mandateVersion": substitutes.mandate_version,
        "pricedCandidates": priced_candidates,
        "candidates": [
            {
                "rank": substitute.ranked.rank,
                "tier": substitute.ranked.tier.value,
                "productCode": substitute.product_code,
                "curated": substitute.curated,
                "score": float(substitute.ranked.score),
                "policyPreview": {
                    "outcome": substitute.policy_preview.outcome.value,
                    "reasons": [
                        PolicyReasonOut.from_reason(reason).model_dump(mode="json", by_alias=True)
                        for reason in substitute.policy_preview.reasons
                    ],
                },
            }
            for substitute in substitutes.candidates
        ],
        "reasonCodes": [code.value for code in substitutes.reason_codes],
    }


def _union[T](first: Iterable[T], second: Iterable[T]) -> tuple[T, ...]:
    return tuple(dict.fromkeys([*first, *second]))


def _labels(product: Product) -> set[str]:
    return {label.label_code for label in product.labels}


def _claims(product: Product) -> list[ClaimCode]:
    return [ClaimCode(type=c.claim_type_code, element=c.claim_element_code) for c in product.claims]


def _sorted_claims(claims: Iterable[ClaimCode]) -> list[ClaimCode]:
    return sorted(claims, key=lambda c: (c.type, c.element))


def _delta(original: Decimal | None, candidate: Decimal | None) -> Decimal | None:
    return candidate - original if original is not None and candidate is not None else None


def _days_between(original: date | None, candidate: date | None) -> int | None:
    return (candidate - original).days if original is not None and candidate is not None else None
