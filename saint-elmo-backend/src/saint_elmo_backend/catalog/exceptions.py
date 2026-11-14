class UnknownCodesError(Exception):
    """
    Search filters name codes the catalog does not know, so they could never match.

    `unknown` maps each ProductFilters field to its unknown codes, in request order.
    """

    def __init__(self, unknown: dict[str, list[str]]) -> None:
        self.unknown = unknown
        super().__init__(f"Unknown codes: {unknown}")
