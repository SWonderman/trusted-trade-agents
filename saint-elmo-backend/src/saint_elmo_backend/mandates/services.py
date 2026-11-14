from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from saint_elmo_backend.agents.models import Agent
from saint_elmo_backend.catalog import services as catalog_services
from saint_elmo_backend.catalog.dtos import ClaimCode
from saint_elmo_backend.catalog.exceptions import UnknownCodesError
from saint_elmo_backend.catalog.models import Allergen, Category, Diet, Label
from saint_elmo_backend.mandates import crud
from saint_elmo_backend.mandates.dtos import (
    AgentMandate,
    CategorySpendCap,
    MandateTerms,
    PeriodSpend,
)
from saint_elmo_backend.mandates.enums import SpendPeriod
from saint_elmo_backend.mandates.exceptions import MandateNotFoundError
from saint_elmo_backend.mandates.models import Mandate

# Spend periods follow the buyer organizations' calendar, which is Finnish
SPEND_PERIOD_TIMEZONE = ZoneInfo("Europe/Helsinki")


def spend_period_bounds(period: SpendPeriod, now: datetime) -> tuple[datetime, datetime]:
    """
    The spend period containing `now`, from its start (inclusive) to its end
    (exclusive), both at midnight in `SPEND_PERIOD_TIMEZONE`.
    """

    today = now.astimezone(SPEND_PERIOD_TIMEZONE).date()
    match period:
        case SpendPeriod.WEEK:
            start = today - timedelta(days=today.weekday())
            end = start + timedelta(weeks=1)
        case SpendPeriod.MONTH:
            start = today.replace(day=1)
            end = date(start.year + start.month // 12, start.month % 12 + 1, 1)

    return _midnight(start), _midnight(end)


def _midnight(day: date) -> datetime:
    return datetime(day.year, day.month, day.day, tzinfo=SPEND_PERIOD_TIMEZONE)


def _terms_of(mandate: Mandate) -> MandateTerms:
    return MandateTerms(
        max_order_total=mandate.max_order_total,
        period_spend_cap=mandate.period_spend_cap,
        spend_period=mandate.spend_period,
        category_spend_caps=tuple(
            CategorySpendCap(category_code=cap["categoryCode"], cap=Decimal(cap["cap"]))
            for cap in mandate.category_spend_caps
        ),
        allowed_category_codes=tuple(mandate.allowed_category_codes),
        blocked_category_codes=tuple(mandate.blocked_category_codes),
        allowed_vendors=tuple(mandate.allowed_vendors),
        blocked_vendors=tuple(mandate.blocked_vendors),
        allowed_countries_of_origin=tuple(mandate.allowed_countries_of_origin),
        required_claims=tuple(
            ClaimCode(type=claim["type"], element=claim["element"])
            for claim in mandate.required_claims
        ),
        required_labels=tuple(mandate.required_labels),
        required_diets=tuple(mandate.required_diets),
        excluded_allergens=tuple(mandate.excluded_allergens),
        allergen_strictness=mandate.allergen_strictness,
        substitution_policy=mandate.substitution_policy,
        max_substitute_price_increase_pct=mandate.max_substitute_price_increase_pct,
        later_delivery_needs_approval=mandate.later_delivery_needs_approval,
        min_delivery_reliability=mandate.min_delivery_reliability,
        auto_approve_up_to=mandate.auto_approve_up_to,
    )


def _apply_terms(mandate: Mandate, terms: MandateTerms) -> None:
    mandate.max_order_total = terms.max_order_total
    mandate.period_spend_cap = terms.period_spend_cap
    mandate.spend_period = terms.spend_period
    # JSON has no decimal type: caps are stored as strings so they stay exact
    mandate.category_spend_caps = [
        {"categoryCode": cap.category_code, "cap": str(cap.cap)}
        for cap in terms.category_spend_caps
    ]
    mandate.allowed_category_codes = list(terms.allowed_category_codes)
    mandate.blocked_category_codes = list(terms.blocked_category_codes)
    mandate.allowed_vendors = list(terms.allowed_vendors)
    mandate.blocked_vendors = list(terms.blocked_vendors)
    mandate.allowed_countries_of_origin = [
        country.lower() for country in terms.allowed_countries_of_origin
    ]
    mandate.required_claims = [
        {"type": claim.type, "element": claim.element} for claim in terms.required_claims
    ]
    mandate.required_labels = list(terms.required_labels)
    mandate.required_diets = list(terms.required_diets)
    mandate.excluded_allergens = list(terms.excluded_allergens)
    mandate.allergen_strictness = terms.allergen_strictness
    mandate.substitution_policy = terms.substitution_policy
    mandate.max_substitute_price_increase_pct = terms.max_substitute_price_increase_pct
    mandate.later_delivery_needs_approval = terms.later_delivery_needs_approval
    mandate.min_delivery_reliability = terms.min_delivery_reliability
    mandate.auto_approve_up_to = terms.auto_approve_up_to


async def _unknown_codes(session: AsyncSession, terms: MandateTerms) -> dict[str, list[str]]:
    """
    Unknown codes per field, checked like product search filters: a code is known when
    its code list has it. Vendors and countries are not checked.
    """

    unknown = {
        "allowed_category_codes": await catalog_services.unknown_codes(
            session, Category.code, terms.allowed_category_codes
        ),
        "blocked_category_codes": await catalog_services.unknown_codes(
            session, Category.code, terms.blocked_category_codes
        ),
        "category_spend_caps": await catalog_services.unknown_codes(
            session, Category.code, [cap.category_code for cap in terms.category_spend_caps]
        ),
        "required_claims": await catalog_services.unknown_claim_codes(
            session, terms.required_claims
        ),
        "required_labels": await catalog_services.unknown_codes(
            session, Label.code, terms.required_labels
        ),
        "required_diets": await catalog_services.unknown_codes(
            session, Diet.code, terms.required_diets
        ),
        "excluded_allergens": await catalog_services.unknown_codes(
            session, Allergen.code, terms.excluded_allergens
        ),
    }
    return {name: codes for name, codes in unknown.items() if codes}


async def write_mandate(session: AsyncSession, agent: Agent, terms: MandateTerms) -> Mandate:
    """
    Give `agent` its mandate, or replace the terms of the one it has. Every change of
    terms bumps its version; writing the same terms again changes nothing. Raises UnknownCodesError, before changing anything, if the terms name
    codes the catalogue does not know.

    A composable building block: the caller owns the commit.
    """

    if unknown := await _unknown_codes(session, terms):
        raise UnknownCodesError(unknown)

    mandate = await crud.get_mandate_for_agent(
        session, organization_id=agent.org_id, agent_id=agent.id
    )
    if mandate is None:
        mandate = Mandate(agent_id=agent.id, org_id=agent.org_id)
        session.add(mandate)

    _apply_terms(mandate, terms)
    await session.flush()
    return mandate


async def get_agent_mandate(
    session: AsyncSession,
    *,
    organization_id: int,
    agent_id: int,
    now: datetime | None = None,
    excluding_order_id: int | None = None,
) -> AgentMandate:
    """
    With the period spend committed by the agent's orders in the spend period containing
    `now` (default: the current time), leaving out `excluding_order_id`, e.g. the
    pending order being re-checked.
    """
    mandate = await crud.get_mandate_for_agent(
        session, organization_id=organization_id, agent_id=agent_id
    )
    if mandate is None:
        raise MandateNotFoundError()

    terms = _terms_of(mandate)
    start, end = spend_period_bounds(terms.spend_period, now or datetime.now(UTC))
    committed, by_category = await crud.committed_spend(
        session,
        organization_id=organization_id,
        agent_id=agent_id,
        start=start,
        end=end,
        excluding_order_id=excluding_order_id,
    )
    return AgentMandate(
        public_id=mandate.public_id,
        version=mandate.version,
        terms=terms,
        period_spend=PeriodSpend(
            period_start=start,
            period_end=end,
            committed=committed,
            remaining=max(terms.period_spend_cap - committed, Decimal(0)),
            committed_by_category=by_category,
        ),
    )
