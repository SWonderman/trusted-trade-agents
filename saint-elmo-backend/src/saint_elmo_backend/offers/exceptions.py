class UnknownProductsError(Exception):
    """
    Some requested product codes are not in the catalog. `codes` lists all of them, in
    request order.
    """

    def __init__(self, codes: list[str]) -> None:
        self.codes = codes
        super().__init__(f"Unknown product codes: {', '.join(codes)}")


class CustomerNumberMissingError(Exception):
    """
    The buyer organisation has no Valio Aimo customer number, so it can't be priced.
    """

    def __init__(self, organization_id: int) -> None:
        self.organization_id = organization_id
        super().__init__(f"Organization {organization_id} has no Valio Aimo customer number")
