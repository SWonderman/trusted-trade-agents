"""
Row-Level-Security request context.

`current_org_id` carries the acting organization for the request. The `after_begin`
listener re-applies it as a transaction-local Postgres GUC (`app.current_org`) on
EVERY transaction, so tenant isolation survives mid-request commits (services commit)
and lazy loads. RLS policies read this GUC.
"""

from contextvars import ContextVar

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

TENANT_GUC = "app.current_org"

current_org_id: ContextVar[int | None] = ContextVar("current_org_id", default=None)


@event.listens_for(Session, "after_begin")
def _apply_tenant_guc_on_begin(session, transaction, connection) -> None:
    org_id = current_org_id.get()
    if org_id is None:
        return
    # SET LOCAL via set_config(..., is_local=true): auto-clears at transaction end,
    # so nothing leaks across pooled connections.
    connection.execute(
        text(f"SELECT set_config('{TENANT_GUC}', :value, true)"),
        {"value": str(org_id)},
    )


async def apply_tenant_guc(session: AsyncSession, org_id: int) -> None:
    """
    Apply the GUC to the already-open transaction (the listener only fires on begin)
    """
    await session.execute(
        text(f"SELECT set_config('{TENANT_GUC}', :value, true)"),
        {"value": str(org_id)},
    )
