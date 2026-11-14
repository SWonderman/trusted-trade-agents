from dataclasses import dataclass

from saint_elmo_backend.accounts.dtos import AuthenticatedUser
from saint_elmo_backend.agents.models import Agent


@dataclass(frozen=True, slots=True)
class Actor:
    """
    Who an order step is credited to: an agent, a user, or the system for automatic steps.
    """

    # "agent:<name>", "user:<first and last name>" or "system", as shown in status history
    label: str
    agent_id: int | None = None
    user_id: int | None = None

    @classmethod
    def of_agent(cls, agent: Agent) -> "Actor":
        return cls(label=f"agent:{agent.name}", agent_id=agent.id)

    @classmethod
    def of_user(cls, user: AuthenticatedUser) -> "Actor":
        return cls(label=f"user:{user.first_name} {user.last_name}", user_id=user.id)


SYSTEM = Actor(label="system")
