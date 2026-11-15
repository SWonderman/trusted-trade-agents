"""
Issue an Agent token for a seeded agent from the command line, for development and as
a fallback for the demo. Run through `just issue-agent-token`.

The token is printed once and never stored, exactly as when a buyer admin issues it.
"""

import argparse
import asyncio
import sys
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import saint_elmo_backend.db.registry  # noqa: F401
from saint_elmo_backend.accounts import crud as account_crud
from saint_elmo_backend.accounts.enums import Permission
from saint_elmo_backend.accounts.permissions import role_has_permission
from saint_elmo_backend.agents import crud, services
from saint_elmo_backend.agents.dtos import IssuedAgentToken
from saint_elmo_backend.agents.enums import ScopePreset
from saint_elmo_backend.core.settings import get_settings
from saint_elmo_backend.mandates.exceptions import MandateNotFoundError

LIFETIME = timedelta(days=30)
LABEL = "Issued from the command line"


class IssueTokenRefusedError(Exception):
    """
    The buyer admin or agent doesn't allow issuing this token.
    """


async def issue_token_for_seeded_agent(
    session: AsyncSession,
    *,
    agent_name: str,
    buyer_admin_email: str,
    preset: ScopePreset = ScopePreset.PURCHASING,
) -> IssuedAgentToken:
    """
    Issue a token for `agent_name` in the buyer admin's own buyer organisation,
    recording that buyer admin as its issuer.

    The caller owns the commit.
    """

    user = await account_crud.get_user_by_email(session, buyer_admin_email.strip().lower())
    if (
        user is None
        or not user.is_active
        or not role_has_permission(user.role, Permission.AGENT_MANAGE)
    ):
        raise IssueTokenRefusedError(f"{buyer_admin_email} is not an active buyer admin")

    # Looked up in the buyer admin's own buyer organisation only, so an agent of
    # another one is refused
    agent = await crud.get_agent_by_name(session, organization_id=user.org_id, name=agent_name)
    if agent is None:
        raise IssueTokenRefusedError(
            f"{user.organization.name} has no agent {agent_name!r}. A buyer admin can only "
            "issue tokens for their own buyer organisation's agents, never for another "
            "buyer organisation's"
        )

    try:
        return await services.issue_agent_token(
            session,
            agent,
            label=LABEL,
            scopes=preset.scopes,
            lifetime=LIFETIME,
            created_by_user_id=user.id,
        )
    except MandateNotFoundError:
        raise IssueTokenRefusedError(
            f"{agent_name} has no mandate; set one before issuing a token"
        ) from None


async def _main(agent_name: str, buyer_admin_email: str, preset: ScopePreset) -> None:
    engine = create_async_engine(get_settings().db_url)
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            try:
                issued = await issue_token_for_seeded_agent(
                    session,
                    agent_name=agent_name,
                    buyer_admin_email=buyer_admin_email,
                    preset=preset,
                )
            except IssueTokenRefusedError as exc:
                sys.exit(f"Refused: {exc}")
            await session.commit()
    finally:
        await engine.dispose()

    print(
        f"Agent token for {agent_name} ({preset}), expires {issued.expires_at:%Y-%m-%d %H:%M %Z}."
        " It is shown only this once:",
        file=sys.stderr,
    )
    print(issued.token)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Issue an Agent token for a seeded agent")
    parser.add_argument("agent", help="Agent name, e.g. dairy-restock")
    parser.add_argument("buyer_admin_email", help="The issuing buyer admin")
    parser.add_argument(
        "preset",
        nargs="?",
        type=ScopePreset,
        default=ScopePreset.PURCHASING,
        choices=list(ScopePreset),
        help="The scopes to issue (default: %(default)s)",
    )
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()

    asyncio.run(_main(args.agent, args.buyer_admin_email, args.preset))


if __name__ == "__main__":
    main()
