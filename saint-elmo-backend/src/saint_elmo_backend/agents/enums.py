from enum import StrEnum


class AgentStatus(StrEnum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"


class Scope(StrEnum):
    """
    What kinds of operation an Agent token may call at all, independent of any mandate limit.
    """

    CATALOG_READ = "catalog:read"
    OFFERS_READ = "offers:read"
    MANDATE_READ = "mandate:read"
    QUOTE_CREATE = "quote:create"
    ORDER_PLACE = "order:place"
    ORDER_READ = "order:read"
