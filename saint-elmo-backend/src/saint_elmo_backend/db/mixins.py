from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from saint_elmo_backend.db import annotations


class TimestampMixin:
    created_at: Mapped[annotations.created_at] = mapped_column()
    updated_at: Mapped[annotations.updated_at] = mapped_column()


class SoftDeletableMixin:
    deleted_at: Mapped[annotations.deleted_at] = mapped_column()


class PublicIdMixin:
    public_id: Mapped[annotations.public_id] = mapped_column()


class TenantMixin:
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
