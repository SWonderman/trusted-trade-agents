"""add substitutes requested audit event

Revision ID: 3f9c2a7d5e18
Revises: be35175a4d11
Create Date: 2026-11-15 12:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3f9c2a7d5e18"
down_revision: str | Sequence[str] | None = "be35175a4d11"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Autogenerate doesn't see new enum values
    op.execute("ALTER TYPE audit_event_type ADD VALUE IF NOT EXISTS 'SUBSTITUTES_REQUESTED'")


def downgrade() -> None:
    """Downgrade schema."""
    # Postgres can't drop enum values: SUBSTITUTES_REQUESTED stays, unused
