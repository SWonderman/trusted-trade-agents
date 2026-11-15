from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from saint_elmo_backend.agents.models import Agent
from saint_elmo_backend.db import annotations
from saint_elmo_backend.db.base import Base
from saint_elmo_backend.db.mixins import OrgOwnedMixin, PublicIdMixin, TimestampMixin
from saint_elmo_backend.db.types import JSONB_
from saint_elmo_backend.orders.enums import OrderStatus
from saint_elmo_backend.policy.enums import PolicyOutcome
from saint_elmo_backend.quotes.models import Quote


class Order(Base, PublicIdMixin, TimestampMixin, OrgOwnedMixin):
    """
    A commitment made from exactly one quote, priced and judged on live data when it was
    placed and again when a human approved it. Lines, totals and policy are those of the
    latest re-check; `changes` says how its live data differs from the quote's.

    Offers, reasons and changes are kept as the camelCase JSON the API returns.
    """

    __tablename__ = "orders"

    # Unique: the quote id is the idempotency key for placing an order (ADR 0002)
    quote_id: Mapped[int] = mapped_column(ForeignKey("quotes.id", ondelete="RESTRICT"), unique=True)
    quote: Mapped[Quote] = relationship()
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id", ondelete="RESTRICT"), index=True)
    agent: Mapped[Agent] = relationship()

    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus, name="order_status"))

    # The policy judgement of the latest re-check and the mandate version it used
    outcome: Mapped[PolicyOutcome] = mapped_column(Enum(PolicyOutcome, name="policy_outcome"))
    mandate_version: Mapped[int] = mapped_column()
    reasons: Mapped[list[dict[str, Any]]] = mapped_column(JSONB_)
    # [{"lineRef": "1", "field": "unitPrice", "quoted": 31.31, "now": 34.1}]
    changes: Mapped[list[dict[str, Any]]] = mapped_column(JSONB_)

    net_total: Mapped[annotations.money] = mapped_column()
    gross_total: Mapped[annotations.money] = mapped_column()
    currency: Mapped[str] = mapped_column(String(3))
    deposits: Mapped[list[dict[str, str]]] = mapped_column(JSONB_)

    # The human decision, once an approver approved or rejected it
    decided_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approver_note: Mapped[str | None] = mapped_column(Text)

    lines: Mapped[list["OrderLine"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="OrderLine.position",
    )
    status_history: Mapped[list["OrderStatusChange"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="OrderStatusChange.id",
    )


class OrderLine(Base, OrgOwnedMixin):
    __tablename__ = "order_lines"
    __table_args__ = (UniqueConstraint("order_id", "position"),)

    # 1-based, as in the quote; the policy's line ref
    position: Mapped[int] = mapped_column()
    product_code: Mapped[str] = mapped_column(String(20))
    substitutes_for: Mapped[str | None] = mapped_column(String(20))
    # The product's category, so category spend caps can sum the order book
    category_code: Mapped[str] = mapped_column(String(20))
    # Net EUR; None without a price or sales units
    net_total: Mapped[Decimal | None] = mapped_column(Numeric(19, 4))

    outcome: Mapped[PolicyOutcome] = mapped_column(Enum(PolicyOutcome, name="policy_outcome"))
    # The live offer as returned by POST /offers
    offer: Mapped[dict[str, Any]] = mapped_column(JSONB_)
    reasons: Mapped[list[dict[str, Any]]] = mapped_column(JSONB_)

    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    order: Mapped[Order] = relationship(back_populates="lines")


class OrderStatusChange(Base, OrgOwnedMixin):
    """
    One step of an order's status history. Appended, never changed.
    """

    __tablename__ = "order_status_changes"

    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus, name="order_status"))
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # "agent:<name>", "user:<first and last name>" or "system", as when the step happened
    by: Mapped[str] = mapped_column(String(300))

    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    order: Mapped[Order] = relationship(back_populates="status_history")
