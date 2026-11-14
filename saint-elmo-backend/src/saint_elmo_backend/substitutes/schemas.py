from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal, Self

from pydantic import Field, StringConstraints, model_validator

from saint_elmo_backend.catalog.dtos import ClaimCode, ProductFilters
from saint_elmo_backend.catalog.enums import Language
from saint_elmo_backend.catalog.schemas import Claim
from saint_elmo_backend.core.schema import CamelBaseModel, DecimalNumber
from saint_elmo_backend.offers.schemas import OfferOut
from saint_elmo_backend.policy.dtos import PolicyJudgement
from saint_elmo_backend.policy.enums import PolicyOutcome
from saint_elmo_backend.policy.schemas import PolicyReasonOut
from saint_elmo_backend.substitutes.dtos import (
    Substitute,
    Substitutes,
    SubstitutesRequest,
    TradeOffs,
)
from saint_elmo_backend.substitutes.enums import SubstitutesReasonCode, Tier

# Request

MAX_LIMIT = 10


class SubstitutesIn(CamelBaseModel):
    """
    Every field is optional. The filters only add to the mandate's requirements: none of
    them can drop one.
    """

    quantity: Decimal | None = Field(
        default=None,
        gt=0,
        description="With it, candidates are judged on covering this quantity, and their "
        "offers converted and priced for it",
        examples=[1000],
    )
    unit: str | None = Field(
        default=None,
        min_length=1,
        max_length=10,
        description="`L`, `KG`, or a unit code such as `KI`. Without it the quantity is in "
        "the original's sales unit. Candidates that can't be expressed in it are left out",
        examples=["L"],
    )
    deliver_by: date | None = Field(
        default=None,
        description="Delivery date, already resolved by the agent. Without it, offers are "
        "evaluated for tomorrow (Europe/Helsinki)",
    )
    required_claims: list[Claim] = Field(
        default_factory=list, description="Added to the mandate's; a candidate must carry all"
    )
    required_labels: list[str] = Field(
        default_factory=list, description="Packaging label codes, added to the mandate's"
    )
    required_diets: list[str] = Field(
        default_factory=list, description="GS1 diet codes, added to the mandate's"
    )
    excluded_allergens: list[str] = Field(
        default_factory=list,
        description="GS1 allergen codes, added to the mandate's and excluded as strictly as "
        "the mandate's allergen strictness says",
    )
    countries_of_origin: list[Annotated[str, StringConstraints(pattern=r"^[A-Za-z]{2}$")]] = Field(
        default_factory=list,
        description="ISO 3166-1 alpha-2; a candidate must come from one of them, and from "
        "the mandate's allowed origins if it has any",
    )
    min_delivery_reliability: Decimal | None = Field(
        default=None,
        ge=0,
        le=1,
        description="Excludes candidates below this share and candidates with no delivery "
        "history; the mandate's own minimum still applies",
    )
    limit: int = Field(default=3, ge=1, le=MAX_LIMIT)
    language: Language = Field(
        default=Language.EN, description="Language of product names; falls back to fi"
    )

    @model_validator(mode="after")
    def _unit_needs_quantity(self) -> Self:
        if self.unit is not None and self.quantity is None:
            raise ValueError("unit is only meaningful together with quantity")
        return self

    def to_request(self) -> SubstitutesRequest:
        return SubstitutesRequest(
            quantity=self.quantity,
            unit=self.unit.upper() if self.unit else None,
            deliver_by=self.deliver_by,
            filters=ProductFilters(
                required_claims=tuple(
                    ClaimCode(type=claim.type, element=claim.element)
                    for claim in self.required_claims
                ),
                required_diets=tuple(self.required_diets),
                required_labels=tuple(self.required_labels),
                countries_of_origin=tuple(country.lower() for country in self.countries_of_origin),
                min_delivery_reliability=self.min_delivery_reliability,
                excluded_allergens=tuple(self.excluded_allergens),
            ),
            limit=self.limit,
            language=self.language,
        )


# Response


class OriginalOut(CamelBaseModel):
    product_code: str
    name: str | None
    offer: OfferOut


class CarbonFootprintDelta(CamelBaseModel):
    value: DecimalNumber = Field(description="kg CO2-eq per kg, candidate minus original")
    basis: Literal["PRODUCT_GROUP_AVERAGE"] = Field(
        default="PRODUCT_GROUP_AVERAGE",
        description="Both values are averages of the products' groups, not of the products",
    )


class TradeOffsOut(CamelBaseModel):
    """
    The candidate against the original. A delta is null when either side is unknown.
    """

    price_per_buyer_unit_delta_pct: DecimalNumber | None = Field(
        description="Percent; positive when the candidate costs more per buyer unit"
    )
    earliest_date_delta: int | None = Field(
        description="Days; positive when the candidate arrives later"
    )
    reliability_delta: DecimalNumber | None
    claims_kept: list[Claim] = Field(description="The original's claims the candidate carries")
    claims_lost: list[Claim] = Field(description="The original's claims the candidate lacks")
    labels_gained: list[str]
    labels_lost: list[str]
    carbon_footprint_delta: CarbonFootprintDelta | None

    @classmethod
    def from_trade_offs(cls, trade_offs: TradeOffs) -> "TradeOffsOut":
        return cls(
            price_per_buyer_unit_delta_pct=trade_offs.price_per_buyer_unit_delta_pct,
            earliest_date_delta=trade_offs.earliest_date_delta,
            reliability_delta=trade_offs.reliability_delta,
            claims_kept=[Claim.from_code(claim) for claim in trade_offs.claims_kept],
            claims_lost=[Claim.from_code(claim) for claim in trade_offs.claims_lost],
            labels_gained=trade_offs.labels_gained,
            labels_lost=trade_offs.labels_lost,
            carbon_footprint_delta=(
                CarbonFootprintDelta(value=trade_offs.carbon_footprint_delta)
                if trade_offs.carbon_footprint_delta is not None
                else None
            ),
        )


class PolicyPreviewOut(CamelBaseModel):
    outcome: PolicyOutcome = Field(
        description="What quoting this candidate as a substitute line for the original "
        "would give now; a preview, not a commitment"
    )
    reasons: list[PolicyReasonOut]

    @classmethod
    def from_judgement(cls, judgement: PolicyJudgement) -> "PolicyPreviewOut":
        return cls(
            outcome=judgement.outcome,
            reasons=[PolicyReasonOut.from_reason(reason) for reason in judgement.reasons],
        )


class CandidateOut(CamelBaseModel):
    rank: int = Field(description="From 1")
    tier: Tier = Field(description="BEST, BETTER, then GOOD, in rank order")
    score: DecimalNumber = Field(description="Out of 100; see the operation's description")
    curated: bool = Field(description="A curated substitute Valio Aimo lists for the original")
    product_code: str
    name: str | None
    offer: OfferOut
    trade_offs: TradeOffsOut
    policy_preview: PolicyPreviewOut

    @classmethod
    def from_substitute(cls, substitute: Substitute) -> "CandidateOut":
        ranked = substitute.ranked
        return cls(
            rank=ranked.rank,
            tier=ranked.tier,
            score=ranked.score,
            curated=substitute.curated,
            product_code=substitute.product_code,
            name=substitute.offer.name,
            offer=OfferOut.from_line(substitute.offer),
            trade_offs=TradeOffsOut.from_trade_offs(substitute.trade_offs),
            policy_preview=PolicyPreviewOut.from_judgement(substitute.policy_preview),
        )


class SubstitutesResponse(CamelBaseModel):
    original: OriginalOut
    deliver_by: date = Field(description="The requested deliverBy, or the default used")
    buyer_unit: str = Field(
        description="The unit candidates were compared in: the requested unit, or without "
        "a quantity the original's comparison unit (L or KG) or sales unit"
    )
    evaluated_at: datetime
    candidates: list[CandidateOut] = Field(description="In rank order, at most `limit`")
    reason_codes: list[SubstitutesReasonCode] = Field(
        description="NO_SUBSTITUTES_FOUND when no candidate qualified"
    )

    @classmethod
    def from_substitutes(cls, substitutes: Substitutes) -> "SubstitutesResponse":
        original = substitutes.original
        return cls(
            original=OriginalOut(
                product_code=original.product.code,
                name=original.name,
                offer=OfferOut.from_line(original),
            ),
            deliver_by=substitutes.deliver_by,
            buyer_unit=substitutes.buyer_unit,
            evaluated_at=substitutes.evaluated_at,
            candidates=[CandidateOut.from_substitute(s) for s in substitutes.candidates],
            reason_codes=list(substitutes.reason_codes),
        )
