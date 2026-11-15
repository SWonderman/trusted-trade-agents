from collections.abc import AsyncIterator

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from saint_elmo_backend.accounts.tests.factories import make_organization
from saint_elmo_backend.agents.enums import Scope
from saint_elmo_backend.agents.tests.factories import bearer, issue_token, make_agent


@pytest.fixture
async def client(client: AsyncClient, session: AsyncSession) -> AsyncIterator[AsyncClient]:
    """
    The root `client`, authenticated as an agent holding only `catalog:read`.

    Authentication itself is tested in agents/tests and accounts/tests.
    """

    agent = await make_agent(session, await make_organization(session))
    token = await issue_token(session, agent, scopes=[Scope.CATALOG_READ])
    await session.commit()

    client.headers.update(bearer(token))
    yield client
