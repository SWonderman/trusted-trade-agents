from enum import StrEnum


class Role(StrEnum):
    BUYER_ADMIN = "BUYER_ADMIN"
    APPROVER = "APPROVER"


class Permission(StrEnum):
    AGENT_MANAGE = "AGENT_MANAGE"
    MANDATE_MANAGE = "MANDATE_MANAGE"
    ORDER_APPROVE = "ORDER_APPROVE"
