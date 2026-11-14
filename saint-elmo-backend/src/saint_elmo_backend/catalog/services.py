from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from saint_elmo_backend.catalog import crud
from saint_elmo_backend.catalog.dtos import (
    CatalogProvenance,
    CatalogVocabulary,
    CuratedSubstitute,
    HitAllergen,
    ProductDetail,
    ProductFilters,
    ProductSearchHit,
    ProductSearchResult,
)
from saint_elmo_backend.catalog.enums import AllergenContainment, AllergenStatus, Language
from saint_elmo_backend.catalog.exceptions import ProductNotFoundError, UnknownCodesError
from saint_elmo_backend.catalog.models import (
    Allergen,
    Category,
    ClaimElement,
    ClaimType,
    Diet,
    Label,
    Product,
    ProductDiet,
    ProductLabel,
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


def hit_allergens(product: Product, excluded: Sequence[str]) -> list[HitAllergen]:
    """
    Every excluded allergen, in request order, with UNKNOWN where the product has no
    row for it; then every other allergen the product CONTAINS, by code, so the agent
    sees what it is buying around.
    """
    containments = {allergen.allergen_code: allergen.containment for allergen in product.allergens}
    contained = sorted(
        code
        for code, containment in containments.items()
        if containment is AllergenContainment.CONTAINS and code not in excluded
    )
    return [
        HitAllergen(code=code, status=AllergenStatus.of(containments.get(code)))
        for code in [*dict.fromkeys(excluded), *contained]
    ]


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
    unknown_claim_codes = await _unknown_codes(
        session, ClaimType.code, claim_types
    ) + await _unknown_codes(session, ClaimElement.code, claim_elements)

    unknown = {
        "category_codes": await _unknown_codes(session, Category.code, filters.category_codes),
        "required_claims": list(dict.fromkeys(unknown_claim_codes)),
        "required_diets": await _unknown_codes(session, Diet.code, filters.required_diets),
        "required_labels": await _unknown_codes(session, Label.code, filters.required_labels),
        "excluded_allergens": await _unknown_codes(
            session, Allergen.code, filters.excluded_allergens
        ),
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
                allergens=hit_allergens(match.product, filters.excluded_allergens),
            )
            for match in matches
        ],
        provenance=catalog_provenance(),
    )


async def get_product(session: AsyncSession, *, code: str, language: Language) -> ProductDetail:
    product = await crud.get_product_by_code(session, code)
    if product is None:
        raise ProductNotFoundError(code)

    return ProductDetail(
        product=product,
        name=product_name(product, language),
        curated_substitutes=sorted(
            (
                CuratedSubstitute(
                    code=substitution.substitute.code,
                    name=product_name(substitution.substitute, language),
                )
                for substitution in product.substitutions
            ),
            key=lambda substitute: substitute.code,
        ),
        provenance=catalog_provenance(),
    )


async def get_vocabulary(session: AsyncSession) -> CatalogVocabulary:
    return CatalogVocabulary(
        claims=await crud.used_claims(session),
        diets=await crud.used_codes(
            session, Diet, code=ProductDiet.diet_code, product_id=ProductDiet.product_id
        ),
        labels=await crud.used_codes(
            session, Label, code=ProductLabel.label_code, product_id=ProductLabel.product_id
        ),
        allergens=await crud.used_allergens(session),
        categories=await crud.used_categories(session),
    )
