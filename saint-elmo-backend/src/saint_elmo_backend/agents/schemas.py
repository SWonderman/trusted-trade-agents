from datetime import datetime
from typing import Self

from pydantic import UUID4, Field, model_validator

from saint_elmo_backend.agents.enums import AgentStatus, Scope, ScopePreset
from saint_elmo_backend.agents.models import Agent, AgentCredential
from saint_elmo_backend.core.schema import CamelBaseModel


class AgentResponse(CamelBaseModel):
    id: UUID4
    name: str
    status: AgentStatus = Field(description="A DISABLED agent's tokens are all refused")

    @classmethod
    def from_agent(cls, agent: Agent) -> "AgentResponse":
        return cls(id=agent.public_id, name=agent.name, status=agent.status)


class AgentListResponse(CamelBaseModel):
    items: list[AgentResponse] = Field(description="By name")


class AgentTokenIn(CamelBaseModel):
    label: str = Field(
        min_length=1, max_length=255, description="What the token is for, e.g. where it runs"
    )
    scopes: list[Scope] | None = Field(
        default=None, min_length=1, description="The scopes to grant; or give `preset`"
    )
    preset: ScopePreset | None = Field(
        default=None,
        description="A named set of scopes: 'Research only' = catalog:read offers:read "
        "mandate:read order:read; 'Purchasing' = all scopes. Or give `scopes`",
    )
    expires_in_days: int = Field(default=7, ge=1, le=30)

    @model_validator(mode="after")
    def _scopes_or_preset(self) -> Self:
        if (self.scopes is None) == (self.preset is None):
            raise ValueError("Give exactly one of `scopes` or `preset`")
        return self

    @property
    def granted_scopes(self) -> frozenset[Scope]:
        if self.preset is not None:
            return self.preset.scopes
        assert self.scopes is not None
        return frozenset(self.scopes)


class IssuedAgentTokenResponse(CamelBaseModel):
    token: str = Field(description="The Agent token. Shown only this once and never stored")
    jti: UUID4 = Field(description="The token's id, to list or revoke it by")
    scopes: list[Scope]
    expires_at: datetime


class TokenIssuer(CamelBaseModel):
    id: UUID4
    name: str


class AgentTokenResponse(CamelBaseModel):
    """
    An issued Agent token, without its value, which is never stored.
    """

    jti: UUID4
    label: str
    scopes: list[Scope]
    expires_at: datetime
    created_at: datetime
    created_by: TokenIssuer = Field(description="The buyer admin who issued it")
    last_used_at: datetime | None = Field(description="Its most recent accepted request")
    revoked_at: datetime | None = Field(description="Set once revoked; refused from then on")

    @classmethod
    def from_credential(cls, credential: AgentCredential) -> "AgentTokenResponse":
        issuer = credential.created_by
        return cls(
            jti=credential.jti,
            label=credential.label,
            scopes=sorted(credential.scopes),
            expires_at=credential.expires_at,
            created_at=credential.created_at,
            created_by=TokenIssuer(
                id=issuer.public_id, name=f"{issuer.first_name} {issuer.last_name}"
            ),
            last_used_at=credential.last_used_at,
            revoked_at=credential.revoked_at,
        )


class AgentTokenListResponse(CamelBaseModel):
    items: list[AgentTokenResponse] = Field(description="Most recent first")
