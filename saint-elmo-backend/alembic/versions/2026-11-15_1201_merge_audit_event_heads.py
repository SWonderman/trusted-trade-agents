"""merge audit event heads

Revision ID: 1462a33823e2
Revises: 3f7c2a9e5b10, 3f9c2a7d5e18
Create Date: 2026-11-15 12:01:00.000000

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "1462a33823e2"
down_revision: str | Sequence[str] | None = ("3f7c2a9e5b10", "3f9c2a7d5e18")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Both parents only add audit event types; nothing to reconcile


def downgrade() -> None:
    """Downgrade schema."""
    # Nothing to undo: the parents downgrade on their own
