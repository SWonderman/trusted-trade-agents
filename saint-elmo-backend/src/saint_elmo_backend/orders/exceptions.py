from saint_elmo_backend.orders.enums import OrderStatus


class OrderNotFoundError(Exception):
    """
    No order with this id that the caller may see.
    """


class OrderNotPendingError(Exception):
    """
    Only a PENDING_APPROVAL order can be approved or rejected.
    """

    def __init__(self, status: OrderStatus) -> None:
        super().__init__(f"The order is {status}, not PENDING_APPROVAL")
        self.status: OrderStatus = status
