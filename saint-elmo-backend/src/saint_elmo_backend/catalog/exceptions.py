class ProductNotFoundError(Exception):
    """
    No product has the given product code.
    """

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(f"No product with code {code!r}")


class UnknownCodesError(Exception):
    """
    Codes the catalog does not know, so they could never match a product.

    `unknown` maps each field that names codes (e.g. of ProductFilters) to its unknown
    codes, in the order given.
    """

    def __init__(self, unknown: dict[str, list[str]]) -> None:
        self.unknown = unknown
        super().__init__(unknown)
