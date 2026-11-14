class AgentError(Exception):
    """Base class for agents-domain errors."""


class InvalidAgentTokenError(AgentError):
    """
    The Agent token is malformed, forged, expired, revoked, for another audience, or its
    agent or buyer organization is no longer active.

    Deliberately one error: callers learn nothing about which check failed.
    """
