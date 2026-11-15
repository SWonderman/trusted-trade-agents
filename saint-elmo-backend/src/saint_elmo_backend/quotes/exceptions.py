from uuid import UUID


class QuoteNotFoundError(Exception):
    """
    No quote with this id in the buyer organization.
    """


class QuoteExpiredError(Exception):
    """
    The quote is past its `expires_at`, so no order can be placed from it.
    """


class QuoteAlreadyOrderedError(Exception):
    """
    An order was already placed from this quote: one quote gives at most one order.
    """

    def __init__(self, order_public_id: UUID) -> None:
        super().__init__(f"Quote already ordered as {order_public_id}")
        self.order_public_id: UUID = order_public_id
