from decimal import Decimal
from typing import Any

from sqlalchemy import ARRAY, CheckConstraint, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from saint_elmo_backend.agents.models import Agent
from saint_elmo_backend.catalog.enums import AllergenStrictness
from saint_elmo_backend.catalog.models import CODE_LENGTH
from saint_elmo_backend.db import annotations
from saint_elmo_backend.db.base import Base
from saint_elmo_backend.db.mixins import OrgOwnedMixin, PublicIdMixin, TimestampMixin
from saint_elmo_backend.db.types import JSONB_
from saint_elmo_backend.mandates.enums import SpendPeriod, SubstitutionPolicy


def _string_array_column(length: int) -> Any:
    """
    A list of strings, empty by default.
    """
    return mapped_column(ARRAY(String(length)), default=list, server_default="{}")


class Mandate(Base, PublicIdMixin, TimestampMixin, OrgOwnedMixin):
    """
    An agent's `MandateTerms`, which document each limit, plus a version. Read and
    written through `services`, which map it to and from those terms.
    """

    __tablename__ = "mandates"
    __table_args__ = (
        CheckConstraint("auto_approve_up_to <= max_order_total", name="auto_approve_up_to"),
        CheckConstraint(
            "min_delivery_reliability BETWEEN 0 AND 1", name="min_delivery_reliability"
        ),
    )
    # Bumped by the ORM on every UPDATE, so quotes and orders can record which
    # version they were judged against
    version: Mapped[int] = mapped_column()
    __mapper_args__ = {"version_id_col": version}

    # Spend
    max_order_total: Mapped[annotations.money] = mapped_column()
    period_spend_cap: Mapped[annotations.money] = mapped_column()
    spend_period: Mapped[SpendPeriod] = mapped_column(Enum(SpendPeriod, name="spend_period"))
    # [{"categoryCode": "10400", "cap": "800.00"}], per spend period
    category_spend_caps: Mapped[list[dict[str, str]]] = mapped_column(
        JSONB_, default=list, server_default="[]"
    )

    # Assortment; an empty allow-list allows anything
    allowed_category_codes: Mapped[list[str]] = _string_array_column(CODE_LENGTH)
    blocked_category_codes: Mapped[list[str]] = _string_array_column(CODE_LENGTH)
    allowed_vendors: Mapped[list[str]] = _string_array_column(255)
    blocked_vendors: Mapped[list[str]] = _string_array_column(255)
    allowed_countries_of_origin: Mapped[list[str]] = _string_array_column(2)

    # Requirements
    # [{"type": "FREE_FROM", "element": "LACTOSE"}]
    required_claims: Mapped[list[dict[str, str]]] = mapped_column(
        JSONB_, default=list, server_default="[]"
    )
    required_labels: Mapped[list[str]] = _string_array_column(CODE_LENGTH)
    required_diets: Mapped[list[str]] = _string_array_column(CODE_LENGTH)
    excluded_allergens: Mapped[list[str]] = _string_array_column(CODE_LENGTH)
    allergen_strictness: Mapped[AllergenStrictness] = mapped_column(
        Enum(
            AllergenStrictness,
            native_enum=False,
            length=16,
            values_callable=lambda values: [value.value for value in values],
        )
    )

    # Substitution
    substitution_policy: Mapped[SubstitutionPolicy] = mapped_column(
        Enum(SubstitutionPolicy, name="substitution_policy")
    )
    max_substitute_price_increase_pct: Mapped[Decimal] = mapped_column(Numeric(6, 2))

    # Delivery
    later_delivery_needs_approval: Mapped[bool] = mapped_column()
    min_delivery_reliability: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))

    # Approval: a compliant order below this total needs no human
    auto_approve_up_to: Mapped[annotations.money] = mapped_column()

    # One mandate per agent
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"), unique=True)
    agent: Mapped[Agent] = relationship(back_populates="mandate")
