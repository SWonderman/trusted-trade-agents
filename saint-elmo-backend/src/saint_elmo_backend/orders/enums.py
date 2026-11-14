from enum import StrEnum


class OrderStatus(StrEnum):
    """
    The order lifecycle (design §3.5). PLACED and REJECTED are final.
    """

    # Auto-approved by the policy, about to be placed
    CONFIRMED = "CONFIRMED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    # A human approved it, about to be placed
    APPROVED = "APPROVED"
    # Recorded in Saint Elmo's order book; the Valio Aimo API takes no orders
    PLACED = "PLACED"
    REJECTED = "REJECTED"


# What counts toward the mandate's period spend: committed, or waiting to be
COMMITTING_STATUSES = (OrderStatus.PENDING_APPROVAL, OrderStatus.APPROVED, OrderStatus.PLACED)

# How long an agent should wait before polling a pending order again
CHECK_AGAIN_AFTER_SECONDS = 30
