"""
Lines priced from live offers and judged by the policy against an agent's mandate: what
a quote is, and what an order re-checks when it is placed and when it is approved.

Results are kept in the API's JSON shape (camelCase keys, amounts as numbers), so what
is stored and audited is exactly what the agent and the approver are shown.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from saint_elmo_backend.catalog import crud as catalog_crud
from saint_elmo_backend.catalog.enums import Language
from saint_elmo_backend.mandates.dtos import AgentMandate
from saint_elmo_backend.offers import services as offer_services
from saint_elmo_backend.offers.cache import OfferCache
from saint_elmo_backend.offers.dtos import Money, OfferLine, RequestedProduct
from saint_elmo_backend.offers.exceptions import UnknownProductsError
from saint_elmo_backend.offers.schemas import DepositOut, OfferOut
from saint_elmo_backend.policy.dtos import (
    LineRequest,
    PolicyInput,
    PolicyJudgement,
    PolicyLine,
    SubstitutedProduct,
)
from saint_elmo_backend.policy.engine import evaluate
from saint_elmo_backend.policy.enums import PolicyOutcome
from saint_elmo_backend.policy.facts import line_offer, product_facts
from saint_elmo_backend.policy.schemas import PolicyReasonOut
from saint_elmo_backend.valio_aimo.client import ValioAimoClient


@dataclass(frozen=True, slots=True)
class PricedLine:
    # The line's 1-based position, which is also its line ref in policy reasons
    position: int
    request: LineRequest
    offer: OfferLine
    # The offer for the product it is a substitute for, at the same quantity
    substituted_offer: OfferLine | None
    # The category of the line's product, for category spend caps
    category_code: str

    @property
    def line_ref(self) -> str:
        return str(self.position)

    @property
    def offer_json(self) -> dict[str, Any]:
        """
        The offer as `POST /offers` returns it.
        """
        return offer_json(self.offer)

    @property
    def net_total(self) -> Decimal | None:
        """
        Net EUR; None without a price or sales units.
        """
        quantity = self.offer.quantity
        return quantity.line_total.net if quantity and quantity.line_total else None


@dataclass(frozen=True, slots=True)
class Assessment:
    lines: list[PricedLine]
    judgement: PolicyJudgement
    # The mandate version the lines were judged against
    mandate_version: int

    @property
    def outcome(self) -> PolicyOutcome:
        return self.judgement.outcome

    @property
    def reasons(self) -> list[dict[str, Any]]:
        """
        Lines in order, then the quote-wide ones, in the API's JSON shape.
        """
        return [
            PolicyReasonOut.from_reason(reason).model_dump(mode="json", by_alias=True)
            for reason in self.judgement.reasons
        ]

    def line_reasons(self, line: PricedLine) -> list[dict[str, Any]]:
        return [reason for reason in self.reasons if reason["lineRef"] == line.line_ref]

    def line_outcome(self, line: PricedLine) -> PolicyOutcome:
        return next(o.outcome for o in self.judgement.lines if o.line_ref == line.line_ref)

    @property
    def totals(self) -> Money:
        """
        Net and gross EUR of the lines that have a total.
        """
        totals = [line.offer.quantity.line_total for line in self.lines if line.offer.quantity]
        return Money(
            net=sum((total.net for total in totals if total), Decimal(0)),
            gross=sum((total.gross for total in totals if total), Decimal(0)),
        )

    @property
    def deposits(self) -> list[dict[str, Any]]:
        """
        Returnable packaging per material and unit, summed over the lines' sales units.
        """
        amounts: dict[tuple[str, str], Decimal] = {}
        for line in self.lines:
            quantity = line.offer.quantity
            sales_units = quantity.converted.sales_units if quantity else None
            if sales_units is None:
                continue
            for deposit in line.offer.product.deposits:
                key = (deposit.material_code, deposit.unit)
                amounts[key] = amounts.get(key, Decimal(0)) + deposit.quantity * sales_units
        return [
            DepositOut(material_code=material, quantity=quantity, unit=unit).model_dump(
                mode="json", by_alias=True
            )
            for (material, unit), quantity in amounts.items()
        ]

    def audit_record(self) -> dict[str, Any]:
        """
        The offers used, with their conversions and provenance, and the policy result
        with the mandate version, so the judgement can be replayed.
        """
        return {
            "lines": [
                {
                    "lineRef": line.line_ref,
                    "offer": line.offer_json,
                    "substitutedOffer": offer_json(line.substituted_offer)
                    if line.substituted_offer
                    else None,
                }
                for line in self.lines
            ],
            "policy": {
                "outcome": self.outcome.value,
                "reasons": self.reasons,
                "mandateVersion": self.mandate_version,
                "lines": [
                    {"lineRef": outcome.line_ref, "outcome": outcome.outcome.value}
                    for outcome in self.judgement.lines
                ],
            },
        }


def offer_json(offer: OfferLine) -> dict[str, Any]:
    return OfferOut.from_line(offer).model_dump(mode="json", by_alias=True)


async def assess(
    session: AsyncSession,
    valio_aimo: ValioAimoClient,
    cache: OfferCache,
    *,
    organization_id: int,
    deliver_by: date,
    lines: Sequence[LineRequest],
    mandate: AgentMandate,
    now: datetime,
    ignore_closing_time: bool = False,
    use_cache: bool = True,
) -> Assessment:
    """
    Price `lines` from live offers and judge them against `mandate` and its period
    spend. `use_cache=False` fetches every offer fresh from the Valio Aimo API.

    Raises `UnknownProductsError` listing every unknown code (substituted products
    included), and whatever `offers.services.get_offers` raises.
    """
    codes = list(
        dict.fromkeys(
            code
            for line in lines
            for code in (line.product_code, line.substitutes_for)
            if code is not None
        )
    )
    products = {p.code: p for p in await catalog_crud.get_products_with_facts(session, codes)}
    if unknown := [code for code in codes if code not in products]:
        raise UnknownProductsError(unknown)

    priced = await _price_lines(
        session,
        valio_aimo,
        cache,
        organization_id=organization_id,
        deliver_by=deliver_by,
        lines=lines,
        category_codes={code: product.category.code for code, product in products.items()},
        now=now,
        ignore_closing_time=ignore_closing_time,
        use_cache=use_cache,
    )
    judgement = evaluate(
        PolicyInput(
            mandate=mandate.terms,
            lines=tuple(
                PolicyLine(
                    line_ref=line.line_ref,
                    product=product_facts(products[line.request.product_code]),
                    offer=line_offer(line.offer),
                    substitutes_for=(
                        SubstitutedProduct(
                            line.substituted_offer.product.code, line_offer(line.substituted_offer)
                        )
                        if line.substituted_offer is not None
                        else None
                    ),
                )
                for line in priced
            ),
            deliver_by=deliver_by,
            period_spend=mandate.period_spend.committed,
            category_period_spend=mandate.period_spend.committed_by_category,
        )
    )
    return Assessment(lines=priced, judgement=judgement, mandate_version=mandate.version)


async def _price_lines(
    session: AsyncSession,
    valio_aimo: ValioAimoClient,
    cache: OfferCache,
    *,
    organization_id: int,
    deliver_by: date,
    lines: Sequence[LineRequest],
    category_codes: dict[str, str],
    now: datetime,
    ignore_closing_time: bool,
    use_cache: bool,
) -> list[PricedLine]:
    """
    One offers request for every line and every substituted product. A substituted
    product is priced for the line's quantity, so the policy can compare the two per
    buyer unit.
    """
    substituted = [
        RequestedProduct(line.substitutes_for, line.quantity, line.unit)
        for line in lines
        if line.substitutes_for is not None
    ]
    offers = await offer_services.get_offers(
        session,
        valio_aimo,
        cache,
        organization_id=organization_id,
        deliver_by=deliver_by,
        requested=[
            *(RequestedProduct(line.product_code, line.quantity, line.unit) for line in lines),
            *substituted,
        ],
        language=Language.EN,
        now=now,
        ignore_closing_time=ignore_closing_time,
        use_cache=use_cache,
    )
    # Offers come back in request order: the lines', then the substituted products'
    line_offers = offers.lines[: len(lines)]
    substituted_offers = iter(offers.lines[len(lines) :])
    return [
        PricedLine(
            position=position,
            request=line,
            offer=offer,
            substituted_offer=next(substituted_offers) if line.substitutes_for else None,
            category_code=category_codes[line.product_code],
        )
        for position, (line, offer) in enumerate(zip(lines, line_offers, strict=True), 1)
    ]
