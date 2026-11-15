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
    AUDIT_READ = "audit:read"


class ScopePreset(StrEnum):
    """
    A named set of scopes to issue an Agent token with.
    """

    RESEARCH_ONLY = "Research only"
    PURCHASING = "Purchasing"

    @property
    def scopes(self) -> frozenset[Scope]:
        match self:
            case ScopePreset.RESEARCH_ONLY:
                return frozenset(
                    {
                        Scope.CATALOG_READ,
                        Scope.OFFERS_READ,
                        Scope.MANDATE_READ,
                        Scope.ORDER_READ,
                        Scope.AUDIT_READ,
                    }
                )
            case ScopePreset.PURCHASING:
                return frozenset(Scope)
