from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from saint_elmo_backend.catalog import crud
from saint_elmo_backend.catalog.dtos import (
    CatalogProvenance,
    ProductFilters,
    ProductSearchHit,
    ProductSearchResult,
)
from saint_elmo_backend.catalog.enums import Language
from saint_elmo_backend.catalog.exceptions import UnknownCodesError
from saint_elmo_backend.catalog.models import (
    Category,
    ClaimElement,
    ClaimType,
    Diet,
    Label,
    Product,
)
from saint_elmo_backend.core.settings import get_settings

CATALOG_SOURCE = "Valio Aimo static catalog + GS1 Synkka"


def catalog_provenance() -> CatalogProvenance:
    return CatalogProvenance(
        source=CATALOG_SOURCE,
        catalog_snapshot_date=get_settings().catalog_snapshot_date,
    )


def product_name(product: Product, language: Language) -> str | None:
    names = {translation.language: translation.name for translation in product.translations}
    # Fall back to Finnish when no name was found
    return names.get(language) or names.get(Language.FI)


async def _unknown_codes(
    session: AsyncSession, column: InstrumentedAttribute[str], codes: Sequence[str]
) -> list[str]:
    known = await crud.existing_codes(session, column, codes)
    return list(dict.fromkeys(code for code in codes if code not in known))


async def _unknown_filter_codes(
    session: AsyncSession, filters: ProductFilters
) -> dict[str, list[str]]:
    """
    Unknown codes per filter, so an agent can fix them all at once. A code is known
    when its code list has it, even if no product uses it. Vendors and countries are
    not checked.
    """
    claim_types = [claim_type for claim_type, _ in filters.required_claims]
    claim_elements = [element for _, element in filters.required_claims]
    known_types = await crud.existing_codes(session, ClaimType.code, claim_types)
    known_elements = await crud.existing_codes(session, ClaimElement.code, claim_elements)
    unknown_claim_codes = [
        code
        for claim_type, element in filters.required_claims
        for code, known in ((claim_type, known_types), (element, known_elements))
        if code not in known
    ]

    unknown = {
        "category_codes": await _unknown_codes(session, Category.code, filters.category_codes),
        "required_claims": list(dict.fromkeys(unknown_claim_codes)),
        "required_diets": await _unknown_codes(session, Diet.code, filters.required_diets),
        "required_labels": await _unknown_codes(session, Label.code, filters.required_labels),
    }
    return {name: codes for name, codes in unknown.items() if codes}


async def search_products(
    session: AsyncSession,
    *,
    query: str | None,
    filters: ProductFilters,
    language: Language,
    limit: int,
    offset: int,
) -> ProductSearchResult:
    # A blank search is still treated as a search
    if query is not None and not query.strip():
        query = None

    if unknown := await _unknown_filter_codes(session, filters):
        raise UnknownCodesError(unknown)

    matches = await crud.search_products(
        session, query=query, filters=filters, limit=limit, offset=offset
    )
    total = await crud.count_products(session, query=query, filters=filters)

    return ProductSearchResult(
        total=total,
        hits=[
            ProductSearchHit(
                product=match.product,
                name=product_name(match.product, language),
                relevance=match.relevance,
            )
            for match in matches
        ],
        provenance=catalog_provenance(),
    )
