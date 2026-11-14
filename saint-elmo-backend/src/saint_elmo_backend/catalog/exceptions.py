class ProductNotFoundError(Exception):
    """
    No product has the given product code.
    """

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(f"No product with code {code!r}")


class UnknownCodesError(Exception):
    """
    Search filters name codes the catalog does not know, so they could never match.

    `unknown` maps each ProductFilters field to its unknown codes, in request order.
    """

    def __init__(self, unknown: dict[str, list[str]]) -> None:
        self.unknown = unknown
        super().__init__(unknown)
