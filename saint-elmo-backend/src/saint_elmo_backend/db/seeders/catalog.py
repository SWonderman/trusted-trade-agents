from pathlib import Path
from typing import Any

from loguru import logger

from sqlalchemy import Table, insert, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from saint_elmo_backend.catalog import source
from saint_elmo_backend.catalog.models import (
    ActivityType,
    Allergen,
    Brand,
    Category,
    ClaimElement,
    ClaimType,
    Diet,
    FishCatchMethod,
    IngredientOrigin,
    Label,
    MeasurementUnit,
    Nutrient,
    Producer,
    Product,
    ProductAllergen,
    ProductClaim,
    ProductDeposit,
    ProductDiet,
    ProductFishSpecies,
    ProductIngredient,
    ProductLabel,
    ProductMedia,
    ProductNutrient,
    ProductPackagingLevel,
    ProductProducer,
    ProductSafetySheet,
    ProductSubstitution,
    ProductTranslation,
    ProductUnit,
    SafetyStatement,
    Vendor,
)

_LOADED_TABLES = [
    model.__tablename__
    for model in (
        Category,
        Vendor,
        Brand,
        Producer,
        Product,
        ProductTranslation,
        ProductUnit,
        ProductPackagingLevel,
        ProductDeposit,
        ProductAllergen,
        ProductClaim,
        ProductDiet,
        ProductLabel,
        ProductNutrient,
        ProductMedia,
        ProductProducer,
        ProductSubstitution,
        ProductIngredient,
        IngredientOrigin,
        ProductFishSpecies,
        FishCatchMethod,
        ProductSafetySheet,
        SafetyStatement,
    )
]


async def _insert(session: AsyncSession, model: type, rows: list[dict[str, Any]]) -> None:
    if rows:
        await session.execute(insert(model), rows)


async def _ensure_codes(session: AsyncSession, model: type, codes: set[str]) -> int:
    """
    Add codes the data uses that the GS1 code list lacks, so product rows can
    reference them. Returns how many were missing.
    """
    codes.discard("")
    if not codes:
        return 0

    result = await session.execute(
        pg_insert(model)
        .values([{"code": code, "is_standard": False} for code in sorted(codes)])
        .on_conflict_do_nothing(index_elements=["code"])
        .returning(model.code)  # type: ignore[attr-defined]
    )
    missing = list(result.scalars())
    if missing:
        table = model.__tablename__  # type: ignore[attr-defined]
        logger.warning(f"Codes not in the {table} code list: {', '.join(missing)}")
    return len(missing)


async def _insert_returning_ids(
    session: AsyncSession, model: type, rows: list[dict[str, Any]]
) -> list[int]:
    """
    Insert rows and return their new ids, in the order the rows were given.
    """
    if not rows:
        return []

    table: Table = model.__table__  # type: ignore[attr-defined]
    result = await session.execute(
        insert(table).returning(table.c.id, sort_by_parameter_order=True), rows
    )
    return list(result.scalars())


async def _insert_lookup(
    session: AsyncSession, model: type, key: str, values: dict[str, dict[str, Any]]
) -> dict[str, int]:
    """
    Insert one row per distinct key and return {key: id}.
    """
    keys = sorted(values)
    ids = await _insert_returning_ids(
        session, model, [{key: k, **values[k]} for k in keys]
    )
    return dict(zip(keys, ids, strict=True))


async def seed_catalog(session: AsyncSession, data_dir: Path) -> None:
    if await session.scalar(select(Product.id).limit(1)) is not None:
        logger.info("Catalogue already loaded, skipping")
        return

    products = source.load_products(data_dir)
    reliability = source.load_product_values(data_dir / source.DELIVERY_RELIABILITY_FILE)
    footprint = source.load_product_values(data_dir / source.CARBON_FOOTPRINT_FILE)

    category_ids = await _insert_lookup(
        session, Category, "code", {p.category: {} for p in products}
    )
    vendor_ids = await _insert_lookup(
        session, Vendor, "name", {p.vendor_name: {} for p in products}
    )
    brand_ids = await _insert_lookup(
        session,
        Brand,
        "name",
        {p.synkka_data.brand: {} for p in products if p.synkka_data.brand},
    )
    producer_ids = await _insert_lookup(
        session,
        Producer,
        "gln",
        {
            producer.id: {"name": producer.name}
            for p in products
            for producer in p.synkka_data.producers
        },
    )

    product_ids = await _insert_returning_ids(
        session,
        Product,
        [
            {
                "code": p.id,
                "sales_unit": p.sales_unit,
                "base_unit": p.base_unit,
                "allowed_lot_size": p.allowed_lot_size,
                "sales_unit_gtin": p.sales_unit_gtin,
                "temperature_condition": p.temperature_condition,
                "min_temperature": p.synkka_data.min_temperature,
                "max_temperature": p.synkka_data.max_temperature,
                "variable_unit": p.synkka_data.variable_unit,
                "country_of_origin": p.country_of_origin,
                "origin_countries": p.synkka_data.countries_of_origin,
                "vat_code": source.normalize_vat_code(p.synkka_data.vat_code),
                "delivery_reliability": reliability.get(p.id),
                "carbon_footprint": footprint.get(p.id),
                "gtin": p.synkka_data.gtin,
                "synkka_updated_at": p.synkka_data.last_updated,
                "media_updated_at": p.synkka_data.medias_last_updated,
                "category_id": category_ids[p.category],
                "vendor_id": vendor_ids[p.vendor_name],
                "brand_id": brand_ids.get(p.synkka_data.brand or ""),
            }
            for p in products
        ],
    )
    id_by_code = {p.id: pid for p, pid in zip(products, product_ids, strict=True)}

    translations: list[dict[str, Any]] = []
    units: list[dict[str, Any]] = []
    packaging_levels: list[dict[str, Any]] = []
    deposits: list[dict[str, Any]] = []
    allergens: list[dict[str, Any]] = []
    claims: list[dict[str, Any]] = []
    diets: list[dict[str, Any]] = []
    labels: list[dict[str, Any]] = []
    nutrients: list[dict[str, Any]] = []
    media: list[dict[str, Any]] = []
    product_producers: list[dict[str, Any]] = []
    substitutions: list[dict[str, Any]] = []
    ingredients: list[tuple[dict[str, Any], source.IngredientSource]] = []
    fish_species: list[tuple[dict[str, Any], source.FishingReport]] = []
    safety_sheets: list[tuple[dict[str, Any], source.SafetyData]] = []
    skipped_substitutions = 0
    skipped_units = 0

    for p in products:
        product_id = id_by_code[p.id]
        synkka = p.synkka_data

        translations += [
            {"product_id": product_id, "language": language, **texts}
            for language, texts in source.collect_translations(synkka).items()
        ]
        # A zero-size unit cannot convert quantities; one occurs in the source
        valid_units = [u for u in p.units if u.size_in_base_units > 0]
        skipped_units += len(p.units) - len(valid_units)
        units += [
            {
                "product_id": product_id,
                "unit_code": u.unit_id,
                "size_in_base_units": u.size_in_base_units,
                "gtin": u.gtin,
            }
            for u in valid_units
        ]
        packaging_levels += [
            {
                "product_id": product_id,
                "level": c.synkka_packaging_type,
                "length_mm": source.to_mm(c.length),
                "width_mm": source.to_mm(c.width),
                "height_mm": source.to_mm(c.height),
                "gross_weight_g": source.to_grams(c.gross_weight),
                "net_weight_g": source.to_grams(c.net_weight),
                "volume_value": c.volume.value if c.volume else None,
                "volume_unit": c.volume.unit if c.volume else None,
            }
            for c in synkka.unit_conversions
        ]
        deposits += [
            {
                "product_id": product_id,
                "material_code": d.material,
                "quantity": d.quantity,
                "unit": d.unit,
            }
            for d in p.deposits
        ]
        allergens += [
            {"product_id": product_id, "allergen_code": code, "containment": containment}
            for code, containment in source.collect_allergens(synkka).items()
        ]
        claims += [
            {
                "product_id": product_id,
                "claim_type_code": claim_type,
                "claim_element_code": element,
            }
            for claim_type, element in sorted(source.collect_claims(synkka))
        ]
        diets += [
            {"product_id": product_id, "diet_code": code}
            for code in sorted(source.collect_diets(synkka))
        ]
        labels += [
            {"product_id": product_id, "label_code": code}
            for code in sorted(source.collect_codes(synkka, "packagingMarkedLabel"))
        ]
        nutrients += [
            {"product_id": product_id, **row} for row in source.collect_nutrients(synkka)
        ]

        # The same media item can be listed twice; it is primary if either says so
        primary_by_media: dict[int, bool] = {}
        for m in synkka.medias:
            primary_by_media[m.id] = primary_by_media.get(m.id, False) or m.primary
        media += [
            {"product_id": product_id, "media_id": media_id, "is_primary": is_primary}
            for media_id, is_primary in primary_by_media.items()
        ]

        product_producers += [
            {"product_id": product_id, "producer_id": producer_ids[producer.id]}
            for producer in synkka.producers
        ]

        for s in p.substitutions:
            if s.substitute_product == p.id or s.substitute_product not in id_by_code:
                skipped_substitutions += 1
                continue
            substitutions.append(
                {"product_id": product_id, "substitute_id": id_by_code[s.substitute_product]}
            )

        ingredients += [
            (
                {
                    "product_id": product_id,
                    "sequence": i.sequence,
                    "percentage": i.percentage,
                    "names": {n.language: n.value for n in i.names},
                },
                i,
            )
            for i in synkka.ingredients
        ]
        fish_species += [
            (
                {"product_id": product_id, "species_code": f.id, "latin_name": f.name},
                f,
            )
            for f in synkka.fishing_reports
        ]
        safety_sheets += [
            ({"product_id": product_id, "sheet_id": sd.sheet_id}, sd)
            for sd in synkka.safety_data
        ]

    non_standard = 0
    for model, codes in (
        (Allergen, {r["allergen_code"] for r in allergens}),
        (ClaimType, {r["claim_type_code"] for r in claims}),
        (ClaimElement, {r["claim_element_code"] for r in claims}),
        (Diet, {r["diet_code"] for r in diets}),
        (Label, {r["label_code"] for r in labels}),
        (Nutrient, {r["nutrient_code"] for r in nutrients}),
        (
            MeasurementUnit,
            {
                r[column]
                for r in nutrients
                for column in ("unit", "basis_unit", "serving_size_unit")
                if r[column]
            },
        ),
        (ActivityType, {o.type for _, i in ingredients for o in i.origins}),
    ):
        non_standard += await _ensure_codes(session, model, codes)

    await _insert(session, ProductTranslation, translations)
    await _insert(session, ProductUnit, units)
    await _insert(session, ProductPackagingLevel, packaging_levels)
    await _insert(session, ProductDeposit, deposits)
    await _insert(session, ProductAllergen, allergens)
    await _insert(session, ProductClaim, claims)
    await _insert(session, ProductDiet, diets)
    await _insert(session, ProductLabel, labels)
    await _insert(session, ProductNutrient, nutrients)
    await _insert(session, ProductMedia, media)
    await _insert(session, ProductProducer, product_producers)
    await _insert(session, ProductSubstitution, substitutions)

    ingredient_ids = await _insert_returning_ids(
        session, ProductIngredient, [row for row, _ in ingredients]
    )
    await _insert(
        session,
        IngredientOrigin,
        [
            {"ingredient_id": ingredient_id, "stage": o.type, "country": o.country}
            for ingredient_id, (_, i) in zip(ingredient_ids, ingredients, strict=True)
            for o in i.origins
        ],
    )

    fish_species_ids = await _insert_returning_ids(
        session, ProductFishSpecies, [row for row, _ in fish_species]
    )
    await _insert(
        session,
        FishCatchMethod,
        [
            {
                "fish_species_id": fish_species_id,
                "production_method": source.normalize_production_method(
                    m.production_method
                ),
                "method_codes": m.methods,
                "area_codes": m.areas,
            }
            for fish_species_id, (_, f) in zip(fish_species_ids, fish_species, strict=True)
            for m in f.catch_methods
        ],
    )

    sheet_ids = await _insert_returning_ids(
        session, ProductSafetySheet, [row for row, _ in safety_sheets]
    )
    await _insert(
        session,
        SafetyStatement,
        [
            {
                "sheet_id": sheet_id,
                "code": v.id,
                "type": source.normalize_statement_type(v.type),
            }
            for sheet_id, (_, sd) in zip(sheet_ids, safety_sheets, strict=True)
            for v in sd.values
        ],
    )

    # Fresh tables have no planner statistics until autovacuum gets to them, and the
    # first queries after a load get pathological plans. ANALYZE counts the rows this
    # transaction inserted, so it can run before the commit.
    await session.execute(text(f"ANALYZE {', '.join(_LOADED_TABLES)}"))

    logger.info(
        f"Catalogue loaded: {len(products)} products, {len(category_ids)} categories,"
        f" {len(vendor_ids)} vendors, {len(brand_ids)} brands,"
        f" {len(producer_ids)} producers, {len(nutrients)} nutrient values,"
        f" {non_standard} codes outside the GS1 lists"
        f" (skipped {skipped_substitutions} invalid substitution rules,"
        f" {skipped_units} zero-size units)"
    )
