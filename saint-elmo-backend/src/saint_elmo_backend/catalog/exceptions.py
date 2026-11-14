class ProductNotFoundError(Exception):
    """
    No product has the given product code.
    """

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(f"No product with code {code!r}")
