"""
The two demo buyer organizations, each with a buyer admin and one agent
with its mandate.
"""

from dataclasses import dataclass
from decimal import Decimal

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from saint_elmo_backend.accounts.enums import Role
from saint_elmo_backend.accounts.models import Organization, User
from saint_elmo_backend.agents.models import Agent
from saint_elmo_backend.catalog.dtos import ClaimCode
from saint_elmo_backend.catalog.enums import AllergenStrictness
from saint_elmo_backend.core.passwords import hash_password
from saint_elmo_backend.mandates import services as mandate_services
from saint_elmo_backend.mandates.dtos import MandateTerms
from saint_elmo_backend.mandates.enums import SpendPeriod, SubstitutionPolicy

# Development and demo only, printed by the seeder so the frontend can log in
DEMO_PASSWORD = "saint-elmo-demo"

HOTEL_CHAIN = "Aurora Hotels"
HOTEL_BUYER_ADMIN_EMAIL = "buyer.admin@aurora-hotels.example"
HOSPITAL_KITCHEN = "Kuusikko Hospital Kitchen"
HOSPITAL_BUYER_ADMIN_EMAIL = "buyer.admin@kuusikko-hospital.example"

# Milk, cream, milk powder, fermented milk, yoghurt, sour milk products, quark,
# butter and cheese. Plant-based drinks and spreads are not dairy.
DAIRY_CATEGORY_CODES = (
    "10400",
    "10401",
    "10404",
    "10405",
    "10411",
    "10412",
    "10419",
    "10430",
    "10500",
    "10501",
    "10600",
    "10602",
    "10603",
    "10630",
    "10631",
    "10632",
    "10633",
    "10635",
    "10636",
    "10637",
    "10639",
    "10640",
)


@dataclass(frozen=True, slots=True)
class _DemoBuyerAdmin:
    email: str
    first_name: str
    last_name: str


@dataclass(frozen=True, slots=True)
class _DemoBuyer:
    name: str
    customer_number: str
    buyer_admin: _DemoBuyerAdmin
    agent_name: str
    mandate: MandateTerms


_DEMO_BUYERS = (
    _DemoBuyer(
        name=HOTEL_CHAIN,
        customer_number="DEMO-HOTEL-001",
        buyer_admin=_DemoBuyerAdmin(
            email=HOTEL_BUYER_ADMIN_EMAIL, first_name="Helmi", last_name="Virtanen"
        ),
        agent_name="dairy-restock",
        mandate=MandateTerms(
            max_order_total=Decimal("2000"),
            period_spend_cap=Decimal("5000"),
            spend_period=SpendPeriod.WEEK,
            auto_approve_up_to=Decimal("1500"),
            substitution_policy=SubstitutionPolicy.IF_REQUIREMENTS_HOLD,
            max_substitute_price_increase_pct=Decimal("10"),
            allowed_category_codes=DAIRY_CATEGORY_CODES,
            required_claims=(ClaimCode(type="FREE_FROM", element="LACTOSE"),),
        ),
    ),
    _DemoBuyer(
        name=HOSPITAL_KITCHEN,
        customer_number="DEMO-HOSPITAL-001",
        buyer_admin=_DemoBuyerAdmin(
            email=HOSPITAL_BUYER_ADMIN_EMAIL, first_name="Onni", last_name="Korhonen"
        ),
        agent_name="ward-kitchen",
        mandate=MandateTerms(
            max_order_total=Decimal("3000"),
            period_spend_cap=Decimal("12000"),
            spend_period=SpendPeriod.MONTH,
            auto_approve_up_to=Decimal("1000"),
            substitution_policy=SubstitutionPolicy.ALWAYS_NEEDS_APPROVAL,
            max_substitute_price_increase_pct=Decimal("5"),
            excluded_allergens=("AM", "AW"),
            allergen_strictness=AllergenStrictness.DECLARED_FREE,
        ),
    ),
)


async def _seed_buyer(session: AsyncSession, buyer: _DemoBuyer) -> None:
    organization = Organization(name=buyer.name, customer_number=buyer.customer_number)
    session.add(organization)
    session.add(
        User(
            first_name=buyer.buyer_admin.first_name,
            last_name=buyer.buyer_admin.last_name,
            email=buyer.buyer_admin.email,
            password_hash=hash_password(DEMO_PASSWORD),
            role=Role.BUYER_ADMIN,
            organization=organization,
        )
    )
    agent = Agent(name=buyer.agent_name, organization=organization)
    session.add(agent)
    await session.flush()

    await mandate_services.write_mandate(session, agent, buyer.mandate)


async def seed_demo(session: AsyncSession) -> None:
    for buyer in _DEMO_BUYERS:
        exists = await session.scalar(
            select(Organization.id).where(Organization.customer_number == buyer.customer_number)
        )
        if exists is not None:
            logger.info(f"Demo buyer organisation {buyer.name} already seeded, skipping")
            continue

        await _seed_buyer(session, buyer)
        logger.info(
            f"Demo buyer organisation {buyer.name}: agent {buyer.agent_name}, buyer admin "
            f"{buyer.buyer_admin.email} with password {DEMO_PASSWORD!r}"
        )
