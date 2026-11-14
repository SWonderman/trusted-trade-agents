class InvalidAgentTokenError(Exception):
    """
    The Agent token is malformed, forged, expired, revoked, for another audience, or its
    agent or buyer organization is no longer active.

    Deliberately one error: callers learn nothing about which check failed.
    """


class AgentNotFoundError(Exception):
    """
    No agent with this public id in the buyer organization.
    """


class AgentCredentialNotFoundError(Exception):
    """
    The agent has no Agent token with this `jti`.
    """
