"""add agent management audit events

Revision ID: 3f7c2a9e5b10
Revises: be35175a4d11
Create Date: 2026-11-15 12:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3f7c2a9e5b10"
down_revision: str | Sequence[str] | None = "be35175a4d11"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Autogenerate doesn't see new enum values
    for event_type in ("AGENT_TOKEN_ISSUED", "AGENT_TOKEN_REVOKED", "AGENT_DISABLED"):
        op.execute(f"ALTER TYPE audit_event_type ADD VALUE IF NOT EXISTS '{event_type}'")


def downgrade() -> None:
    """Downgrade schema."""
    # Postgres can't drop enum values: the AGENT_* audit event types stay, unused
