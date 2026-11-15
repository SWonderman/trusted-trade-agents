from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from saint_elmo_backend.db import annotations
from saint_elmo_backend.db.base import Base
from saint_elmo_backend.db.mixins import OrgOwnedMixin, PublicIdMixin
from saint_elmo_backend.db.types import JSONB_
from saint_elmo_backend.policy.enums import PolicyOutcome


class Quote(Base, PublicIdMixin, OrgOwnedMixin):
    """
    Priced quote lines the policy judged against the agent's mandate, as they were quoted.
    Never changed after it is created; whether it has expired follows from `expires_at`.

    Offers and reasons are kept as the camelCase JSON the API returned, so reading a
    quote back shows exactly what the agent was told.
    """

    __tablename__ = "quotes"

    created_at: Mapped[annotations.created_at] = mapped_column()
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    deliver_by: Mapped[date] = mapped_column(Date)

    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id", ondelete="RESTRICT"), index=True)
    # The quote this one revises
    previous_quote_id: Mapped[int | None] = mapped_column(
        ForeignKey("quotes.id", ondelete="SET NULL")
    )
    previous_quote: Mapped["Quote | None"] = relationship(remote_side="Quote.id")

    buyer_request: Mapped[str] = mapped_column(Text)
    rationale: Mapped[str] = mapped_column(Text)

    # The policy judgment and the mandate version it was judged against
    outcome: Mapped[PolicyOutcome] = mapped_column(Enum(PolicyOutcome, name="policy_outcome"))
    mandate_version: Mapped[int] = mapped_column()
    reasons: Mapped[list[dict[str, Any]]] = mapped_column(JSONB_)

    net_total: Mapped[annotations.money] = mapped_column()
    gross_total: Mapped[annotations.money] = mapped_column()
    currency: Mapped[str] = mapped_column(String(3))
    # [{"materialCode": "...", "quantity": 50, "unit": "ST"}], not in the totals
    deposits: Mapped[list[dict[str, str]]] = mapped_column(JSONB_)

    lines: Mapped[list["QuoteLine"]] = relationship(
        back_populates="quote",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="QuoteLine.position",
    )


class QuoteLine(Base, OrgOwnedMixin):
    __tablename__ = "quote_lines"
    __table_args__ = (UniqueConstraint("quote_id", "position"),)

    # 1-based, in request order; the policy's line ref
    position: Mapped[int] = mapped_column()
    product_code: Mapped[str] = mapped_column(String(20))
    substitutes_for: Mapped[str | None] = mapped_column(String(20))
    # As requested; a None unit is the product's sales unit
    requested_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    requested_unit: Mapped[str | None] = mapped_column(String(10))

    outcome: Mapped[PolicyOutcome] = mapped_column(Enum(PolicyOutcome, name="policy_outcome"))
    # The offer as returned by POST /offers: price, availability, quantity, provenance
    offer: Mapped[dict[str, Any]] = mapped_column(JSONB_)
    reasons: Mapped[list[dict[str, Any]]] = mapped_column(JSONB_)

    quote_id: Mapped[int] = mapped_column(ForeignKey("quotes.id", ondelete="CASCADE"), index=True)
    quote: Mapped[Quote] = relationship(back_populates="lines")
