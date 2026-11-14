from datetime import datetime
from typing import Literal

from pydantic import UUID4, Field

from saint_elmo_backend.agents.dtos import AuthenticatedAgent
from saint_elmo_backend.catalog.enums import AllergenStrictness
from saint_elmo_backend.catalog.schemas import Claim
from saint_elmo_backend.core.schema import CamelBaseModel, DecimalNumber
from saint_elmo_backend.mandates.dtos import AgentMandate
from saint_elmo_backend.mandates.enums import SpendPeriod, SubstitutionPolicy


class MandateAgent(CamelBaseModel):
    id: UUID4
    name: str


class MandateBuyerOrganisation(CamelBaseModel):
    name: str


class CategorySpendCapOutput(CamelBaseModel):
    category_code: str
    cap: DecimalNumber = Field(description="EUR excluding VAT, per spend period")


class PeriodSpendOutput(CamelBaseModel):
    period_start: datetime = Field(description="Start of the current spend period, inclusive")
    period_end: datetime = Field(description="End of the current spend period, exclusive")
    committed: DecimalNumber = Field(
        description="Total of the agent's placed, approved and pending-approval orders in "
        "the period"
    )
    remaining: DecimalNumber = Field(description="periodSpendCap minus committed, at least 0")


class MandateResponse(CamelBaseModel):
    """
    The agent's whole mandate, with nothing hidden, so it can pre-check proposals.
    Saint Elmo's policy applies it again to every quote and order.
    """

    id: UUID4
    version: int = Field(
        description="Increments on every edit; quotes and orders record the version "
        "they were judged against"
    )
    agent: MandateAgent
    buyer_organisation: MandateBuyerOrganisation
    currency: Literal["EUR"] = Field(
        default="EUR", description="Every amount is in this currency, excluding VAT"
    )

    # Spend
    max_order_total: DecimalNumber = Field(description="Maximum total of one order")
    period_spend_cap: DecimalNumber = Field(
        description="Maximum the agent's orders may commit in one spend period"
    )
    spend_period: SpendPeriod = Field(
        description="WEEK runs Monday to Sunday, MONTH a calendar month, both in "
        "Europe/Helsinki time"
    )
    category_spend_caps: list[CategorySpendCapOutput] = Field(
        description="Maximum per category per spend period"
    )

    # Assortment
    allowed_category_codes: list[str] = Field(description="Empty allows every category")
    blocked_category_codes: list[str]
    allowed_vendors: list[str] = Field(description="Vendor names; empty allows every vendor")
    blocked_vendors: list[str]
    allowed_countries_of_origin: list[str] = Field(
        description="ISO 3166-1 alpha-2, lowercase; empty allows every origin"
    )

    # Requirements
    required_claims: list[Claim] = Field(description="Every product must carry all of these")
    required_labels: list[str] = Field(description="Every product must carry all of these")
    required_diets: list[str] = Field(description="Every product must carry all of these")
    excluded_allergens: list[str] = Field(description="GS1 allergen codes")
    allergen_strictness: AllergenStrictness = Field(
        description="contains: a product declared CONTAINS is excluded; may_contain: "
        "MAY_CONTAIN too; declared_free: only products declared FREE_FROM every excluded "
        "allergen are allowed"
    )

    # Substitution
    substitution_policy: SubstitutionPolicy
    max_substitute_price_increase_pct: DecimalNumber = Field(
        description="How much more a substitute may cost than the product it replaces, in %"
    )

    # Delivery
    later_delivery_needs_approval: bool = Field(
        description="A delivery later than requested needs a human"
    )
    min_delivery_reliability: DecimalNumber | None = Field(
        description="0-1; products below it, or without delivery history, need a human"
    )

    # Approval
    auto_approve_up_to: DecimalNumber = Field(
        description="A compliant order below this total needs no human; at most maxOrderTotal"
    )

    period_spend: PeriodSpendOutput

    @classmethod
    def from_mandate(cls, agent: AuthenticatedAgent, mandate: AgentMandate) -> "MandateResponse":
        terms = mandate.terms
        return cls(
            id=mandate.public_id,
            version=mandate.version,
            agent=MandateAgent(id=agent.public_id, name=agent.name),
            buyer_organisation=MandateBuyerOrganisation(name=agent.organization.name),
            max_order_total=terms.max_order_total,
            period_spend_cap=terms.period_spend_cap,
            spend_period=terms.spend_period,
            category_spend_caps=[
                CategorySpendCapOutput(category_code=cap.category_code, cap=cap.cap)
                for cap in terms.category_spend_caps
            ],
            allowed_category_codes=list(terms.allowed_category_codes),
            blocked_category_codes=list(terms.blocked_category_codes),
            allowed_vendors=list(terms.allowed_vendors),
            blocked_vendors=list(terms.blocked_vendors),
            allowed_countries_of_origin=list(terms.allowed_countries_of_origin),
            required_claims=[
                Claim(type=claim.type, element=claim.element) for claim in terms.required_claims
            ],
            required_labels=list(terms.required_labels),
            required_diets=list(terms.required_diets),
            excluded_allergens=list(terms.excluded_allergens),
            allergen_strictness=terms.allergen_strictness,
            substitution_policy=terms.substitution_policy,
            max_substitute_price_increase_pct=terms.max_substitute_price_increase_pct,
            later_delivery_needs_approval=terms.later_delivery_needs_approval,
            min_delivery_reliability=terms.min_delivery_reliability,
            auto_approve_up_to=terms.auto_approve_up_to,
            period_spend=PeriodSpendOutput(
                period_start=mandate.period_spend.period_start,
                period_end=mandate.period_spend.period_end,
                committed=mandate.period_spend.committed,
                remaining=mandate.period_spend.remaining,
            ),
        )
