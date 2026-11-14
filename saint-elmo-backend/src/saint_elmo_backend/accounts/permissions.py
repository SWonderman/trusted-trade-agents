from saint_elmo_backend.accounts.enums import Permission, Role

ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    # Manages the buyer organization's agents, their mandates and Agent tokens
    Role.BUYER_ADMIN: frozenset(Permission),
    # Signs off orders that need approval
    Role.APPROVER: frozenset({Permission.ORDER_APPROVE}),
}


def role_has_permission(role: Role, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, frozenset())
