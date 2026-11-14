"""
Valio Aimo product catalogue, loaded from the static challenge data.

Global (shared by all tenants): no TenantMixin and no row-level security. Read-only at
runtime - rows are written only by the catalogue seeder.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    ARRAY,
    BigInteger,
    CheckConstraint,
    Computed,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from saint_elmo_backend.db.base import Base
from saint_elmo_backend.db.types import JSONB_

from saint_elmo_backend.catalog.enums import (
    AllergenContainment,
    FishProductionMethod,
    PackagingLevel,
    SafetyStatementType,
    VatCode,
)


class Category(Base):
    """
    Category names are not part of the source data, only the codes.
    """

    __tablename__ = "categories"

    code: Mapped[str] = mapped_column(String(10), unique=True)

    products: Mapped[list["Product"]] = relationship(back_populates="category")


class Vendor(Base):
    """
    The supplier Valio Aimo buys the product from.
    """

    __tablename__ = "vendors"

    name: Mapped[str] = mapped_column(String(255), unique=True)

    products: Mapped[list["Product"]] = relationship(back_populates="vendor")


class Brand(Base):
    __tablename__ = "brands"

    name: Mapped[str] = mapped_column(String(255), unique=True)

    products: Mapped[list["Product"]] = relationship(back_populates="brand")


class Producer(Base):
    """
    Manufacturer, identified by its GS1 Global Location Number.
    """

    __tablename__ = "producers"

    gln: Mapped[str] = mapped_column(String(13), unique=True)
    name: Mapped[str] = mapped_column(String(255))


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint(
            "delivery_reliability BETWEEN 0 AND 1", name="delivery_reliability_range"
        ),
        CheckConstraint("allowed_lot_size > 0", name="allowed_lot_size_positive"),
    )

    code: Mapped[str] = mapped_column(
        String(20), unique=True, comment="Valio Aimo product code, used by the API"
    )

    # Ordering
    sales_unit: Mapped[str] = mapped_column(
        String(10), comment="Unit the product is ordered and priced in, e.g. KI"
    )
    base_unit: Mapped[str] = mapped_column(String(10))
    allowed_lot_size: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), comment="Order quantity must be a multiple of this, in sales units"
    )
    sales_unit_gtin: Mapped[str | None] = mapped_column(String(14), unique=True)

    # Logistics
    temperature_condition: Mapped[int | None] = mapped_column(
        SmallInteger, comment="Aimo storage/transport class code; meanings not published"
    )
    min_temperature: Mapped[Decimal | None] = mapped_column(Numeric(5, 1))
    max_temperature: Mapped[Decimal | None] = mapped_column(Numeric(5, 1))
    variable_unit: Mapped[bool | None] = mapped_column(
        comment="Sold by variable weight, so the actual quantity of a unit varies"
    )

    # Origin
    country_of_origin: Mapped[str | None] = mapped_column(
        String(2), comment="ISO 3166-1 alpha-2, lowercase"
    )
    origin_countries: Mapped[list[str]] = mapped_column(
        ARRAY(String(10)),
        server_default="{}",
        comment="Manufacturer-declared countries, ISO 3166-1 numeric",
    )

    vat_code: Mapped[VatCode | None] = mapped_column(Enum(VatCode, name="vat_code"))

    # Supplementary data sets (CSV), not every product has a value
    delivery_reliability: Mapped[Decimal | None] = mapped_column(
        Numeric(4, 3), comment="Share of historical orders delivered as ordered, 0-1"
    )
    carbon_footprint: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 3),
        comment="kg CO2-eq per kg, average of the product group (not this product)",
    )

    # Manufacturer data (GS1 Synkka)
    gtin: Mapped[str | None] = mapped_column(
        String(14), index=True, comment="GTIN of the consumer unit; not unique"
    )
    synkka_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    media_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), index=True
    )
    category: Mapped["Category"] = relationship(back_populates="products")

    vendor_id: Mapped[int] = mapped_column(
        ForeignKey("vendors.id", ondelete="RESTRICT"), index=True
    )
    vendor: Mapped["Vendor"] = relationship(back_populates="products")

    brand_id: Mapped[int | None] = mapped_column(
        ForeignKey("brands.id", ondelete="SET NULL"), index=True
    )
    brand: Mapped["Brand | None"] = relationship(back_populates="products")

    producers: Mapped[list["Producer"]] = relationship(
        secondary="product_producers", order_by="Producer.name"
    )

    translations: Mapped[list["ProductTranslation"]] = relationship(
        back_populates="product", cascade="all, delete-orphan", passive_deletes=True
    )
    units: Mapped[list["ProductUnit"]] = relationship(
        back_populates="product", cascade="all, delete-orphan", passive_deletes=True
    )
    packaging_levels: Mapped[list["ProductPackagingLevel"]] = relationship(
        back_populates="product", cascade="all, delete-orphan", passive_deletes=True
    )
    deposits: Mapped[list["ProductDeposit"]] = relationship(
        back_populates="product", cascade="all, delete-orphan", passive_deletes=True
    )
    allergens: Mapped[list["ProductAllergen"]] = relationship(
        back_populates="product", cascade="all, delete-orphan", passive_deletes=True
    )
    claims: Mapped[list["ProductClaim"]] = relationship(
        back_populates="product", cascade="all, delete-orphan", passive_deletes=True
    )
    labels: Mapped[list["ProductLabel"]] = relationship(
        back_populates="product", cascade="all, delete-orphan", passive_deletes=True
    )
    nutrients: Mapped[list["ProductNutrient"]] = relationship(
        back_populates="product", cascade="all, delete-orphan", passive_deletes=True
    )
    ingredients: Mapped[list["ProductIngredient"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ProductIngredient.sequence",
    )
    media: Mapped[list["ProductMedia"]] = relationship(
        back_populates="product", cascade="all, delete-orphan", passive_deletes=True
    )
    fish_species: Mapped[list["ProductFishSpecies"]] = relationship(
        back_populates="product", cascade="all, delete-orphan", passive_deletes=True
    )
    safety_sheets: Mapped[list["ProductSafetySheet"]] = relationship(
        back_populates="product", cascade="all, delete-orphan", passive_deletes=True
    )
    substitutions: Mapped[list["ProductSubstitution"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        passive_deletes=True,
        foreign_keys="ProductSubstitution.product_id",
    )


class ProductProducer(Base):
    __tablename__ = "product_producers"
    __table_args__ = (UniqueConstraint("product_id", "producer_id"),)

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE")
    )
    producer_id: Mapped[int] = mapped_column(
        ForeignKey("producers.id", ondelete="CASCADE"), index=True
    )


# Postgres text search configuration per ISO 639-1 language; others fall back to simple
_SEARCH_CONFIG = (
    "CASE language"
    " WHEN 'fi' THEN 'pg_catalog.finnish'::regconfig"
    " WHEN 'sv' THEN 'pg_catalog.swedish'::regconfig"
    " WHEN 'en' THEN 'pg_catalog.english'::regconfig"
    " ELSE 'pg_catalog.simple'::regconfig END"
)


class ProductTranslation(Base):
    """
    Texts of one product in one language.

    Not every language has every text: some rows only carry key ingredients.
    """

    __tablename__ = "product_translations"
    __table_args__ = (
        UniqueConstraint("product_id", "language"),
        Index("product_translations_search_idx", "search_vector", postgresql_using="gin"),
        Index(
            "product_translations_name_trgm_idx",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ),
    )

    language: Mapped[str] = mapped_column(String(2), comment="ISO 639-1")
    name: Mapped[str | None] = mapped_column(Text)
    marketing_text: Mapped[str | None] = mapped_column(Text)
    key_ingredients: Mapped[str | None] = mapped_column(Text)
    additional_description: Mapped[str | None] = mapped_column(
        Text, comment="e.g. contents of a multipack"
    )
    storage_instructions: Mapped[str | None] = mapped_column(Text)
    usage_instructions: Mapped[str | None] = mapped_column(Text)
    preparation_instructions: Mapped[str | None] = mapped_column(Text)
    disposal_information: Mapped[str | None] = mapped_column(Text)

    search_vector: Mapped[Any] = mapped_column(
        TSVECTOR,
        Computed(
            f"setweight(to_tsvector({_SEARCH_CONFIG}, coalesce(name, '')), 'A')"
            f" || setweight(to_tsvector({_SEARCH_CONFIG}, coalesce(key_ingredients, '')), 'B')"
            f" || setweight(to_tsvector({_SEARCH_CONFIG}, coalesce(marketing_text, '')), 'C')",
            persisted=True,
        ),
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE")
    )
    product: Mapped["Product"] = relationship(back_populates="translations")


class ProductUnit(Base):
    """
    One level of the packaging hierarchy the product can be handled in (e.g. ST, KI,
    PAL). Converts sales units to base units: the base unit always has size 1.
    """

    __tablename__ = "product_units"
    __table_args__ = (
        UniqueConstraint("product_id", "unit_code"),
        CheckConstraint("size_in_base_units > 0", name="size_positive"),
    )

    unit_code: Mapped[str] = mapped_column(String(10))
    size_in_base_units: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    gtin: Mapped[str | None] = mapped_column(String(14))

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE")
    )
    product: Mapped["Product"] = relationship(back_populates="units")


class ProductPackagingLevel(Base):
    """
    Manufacturer-declared dimensions and weights, normalized to mm and grams.
    """

    __tablename__ = "product_packaging_levels"
    __table_args__ = (UniqueConstraint("product_id", "level"),)

    level: Mapped[PackagingLevel] = mapped_column(
        Enum(PackagingLevel, name="packaging_level")
    )
    length_mm: Mapped[Decimal | None] = mapped_column(Numeric(10, 1))
    width_mm: Mapped[Decimal | None] = mapped_column(Numeric(10, 1))
    height_mm: Mapped[Decimal | None] = mapped_column(Numeric(10, 1))
    gross_weight_g: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    net_weight_g: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    # Kept as declared: the source mixes volume, weight and count units here
    volume_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    volume_unit: Mapped[str | None] = mapped_column(String(20))

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE")
    )
    product: Mapped["Product"] = relationship(back_populates="packaging_levels")


class ProductDeposit(Base):
    """
    Returnable packaging charged together with each sales unit.
    """

    __tablename__ = "product_deposits"
    __table_args__ = (UniqueConstraint("product_id", "material_code"),)

    material_code: Mapped[str] = mapped_column(
        String(20), comment="Deposit material code; not a catalogue product"
    )
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(10, 3), comment="Deposit units per sales unit"
    )
    unit: Mapped[str] = mapped_column(String(10))

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE")
    )
    product: Mapped["Product"] = relationship(back_populates="deposits")


class ProductAllergen(Base):
    """
    Declared relation of a product to a GS1 allergen code (e.g. AM milk, AW gluten
    cereals). Missing row = unknown, see AllergenContainment.
    """

    __tablename__ = "product_allergens"
    __table_args__ = (
        UniqueConstraint("product_id", "allergen_code"),
        Index("product_allergens_lookup_idx", "allergen_code", "containment"),
    )

    allergen_code: Mapped[str] = mapped_column(String(5))
    containment: Mapped[AllergenContainment] = mapped_column(
        Enum(AllergenContainment, name="allergen_containment")
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE")
    )
    product: Mapped["Product"] = relationship(back_populates="allergens")


class ProductClaim(Base):
    """
    Nutritional or dietary claim, e.g. FREE_FROM_LACTOSE, VEGAN, HIGH_PROTEIN.
    """

    __tablename__ = "product_claims"
    __table_args__ = (UniqueConstraint("product_id", "claim_code"),)

    claim_code: Mapped[str] = mapped_column(String(50), index=True)

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE")
    )
    product: Mapped["Product"] = relationship(back_populates="claims")


class ProductLabel(Base):
    """
    Label marked on the packaging: certifications (EU_ORGANIC_FARMING, SVANEN, ...)
    and storage-temperature marks (warmTemperature, coolTemperature, ...).
    """

    __tablename__ = "product_labels"
    __table_args__ = (UniqueConstraint("product_id", "label_code"),)

    label_code: Mapped[str] = mapped_column(String(50), index=True)

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE")
    )
    product: Mapped["Product"] = relationship(back_populates="labels")


class ProductNutrient(Base):
    """
    One nutrient value per basis quantity (usually per 100 g or 100 ml). Basis is
    NULL when the manufacturer gave the value without one.
    """

    __tablename__ = "product_nutrients"
    __table_args__ = (
        UniqueConstraint(
            "product_id",
            "nutrient_code",
            "basis_quantity",
            "basis_unit",
            postgresql_nulls_not_distinct=True,
        ),
    )

    nutrient_code: Mapped[str] = mapped_column(
        String(20), comment="GS1 code, e.g. ENER-KJO, FAT, LACS (lactose)"
    )
    value: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    unit: Mapped[str] = mapped_column(String(10), comment="e.g. GRM, MGM, KJO, E14")
    precision: Mapped[str | None] = mapped_column(
        String(30), comment="e.g. APPROXIMATELY, LESS_THAN"
    )
    basis_quantity: Mapped[Decimal | None] = mapped_column(Numeric(10, 3))
    basis_unit: Mapped[str | None] = mapped_column(String(10))
    daily_value_percent: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    serving_size: Mapped[Decimal | None] = mapped_column(Numeric(10, 3))
    serving_size_unit: Mapped[str | None] = mapped_column(String(10))

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE")
    )
    product: Mapped["Product"] = relationship(back_populates="nutrients")


class ProductIngredient(Base):
    __tablename__ = "product_ingredients"
    __table_args__ = (UniqueConstraint("product_id", "sequence"),)

    sequence: Mapped[int] = mapped_column(
        SmallInteger, comment="Position in the ingredient list, from 1"
    )
    percentage: Mapped[Decimal | None] = mapped_column(Numeric(6, 3))
    names: Mapped[dict[str, str]] = mapped_column(
        JSONB_, comment="Name per ISO 639-1 language"
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE")
    )
    product: Mapped["Product"] = relationship(back_populates="ingredients")

    origins: Mapped[list["IngredientOrigin"]] = relationship(
        back_populates="ingredient", cascade="all, delete-orphan", passive_deletes=True
    )


class IngredientOrigin(Base):
    __tablename__ = "ingredient_origins"
    __table_args__ = (UniqueConstraint("ingredient_id", "stage", "country"),)

    stage: Mapped[str] = mapped_column(
        String(30), comment="e.g. FARMING, MILKING, LAST_PROCESSING"
    )
    country: Mapped[str] = mapped_column(
        String(10), comment="ISO 3166-1 numeric, or NON_EU"
    )

    ingredient_id: Mapped[int] = mapped_column(
        ForeignKey("product_ingredients.id", ondelete="CASCADE")
    )
    ingredient: Mapped["ProductIngredient"] = relationship(back_populates="origins")


class ProductMedia(Base):
    """
    Reference to a product image; the files are not part of the data set.
    """

    __tablename__ = "product_media"
    __table_args__ = (UniqueConstraint("product_id", "media_id"),)

    media_id: Mapped[int] = mapped_column(BigInteger)
    is_primary: Mapped[bool]

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE")
    )
    product: Mapped["Product"] = relationship(back_populates="media")


class ProductFishSpecies(Base):
    __tablename__ = "product_fish_species"
    __table_args__ = (UniqueConstraint("product_id", "species_code"),)

    species_code: Mapped[str] = mapped_column(
        String(10), comment="FAO 3-alpha code, e.g. SAL"
    )
    latin_name: Mapped[str] = mapped_column(String(255))

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE")
    )
    product: Mapped["Product"] = relationship(back_populates="fish_species")

    catch_methods: Mapped[list["FishCatchMethod"]] = relationship(
        back_populates="fish_species",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class FishCatchMethod(Base):
    __tablename__ = "fish_catch_methods"

    production_method: Mapped[FishProductionMethod] = mapped_column(
        Enum(FishProductionMethod, name="fish_production_method")
    )
    method_codes: Mapped[list[str]] = mapped_column(ARRAY(String(10)))
    area_codes: Mapped[list[str]] = mapped_column(
        ARRAY(String(10)), comment="FAO fishing area codes"
    )

    fish_species_id: Mapped[int] = mapped_column(
        ForeignKey("product_fish_species.id", ondelete="CASCADE"), index=True
    )
    fish_species: Mapped["ProductFishSpecies"] = relationship(
        back_populates="catch_methods"
    )


class ProductSafetySheet(Base):
    __tablename__ = "product_safety_sheets"
    __table_args__ = (UniqueConstraint("product_id", "sheet_id"),)

    sheet_id: Mapped[str] = mapped_column(String(50))

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE")
    )
    product: Mapped["Product"] = relationship(back_populates="safety_sheets")

    statements: Mapped[list["SafetyStatement"]] = relationship(
        back_populates="sheet", cascade="all, delete-orphan", passive_deletes=True
    )


class SafetyStatement(Base):
    """
    GHS hazard (H) or precautionary (P) statement code, e.g. h319.
    """

    __tablename__ = "safety_statements"
    __table_args__ = (UniqueConstraint("sheet_id", "code"),)

    code: Mapped[str] = mapped_column(String(20))
    type: Mapped[SafetyStatementType] = mapped_column(
        Enum(SafetyStatementType, name="safety_statement_type")
    )

    sheet_id: Mapped[int] = mapped_column(
        ForeignKey("product_safety_sheets.id", ondelete="CASCADE")
    )
    sheet: Mapped["ProductSafetySheet"] = relationship(back_populates="statements")


class ProductSubstitution(Base):
    """
    Curated rule: `substitute` may be offered when `product` is unavailable.
    """

    __tablename__ = "product_substitutions"
    __table_args__ = (
        UniqueConstraint("product_id", "substitute_id"),
        CheckConstraint("product_id <> substitute_id", name="not_self"),
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE")
    )
    product: Mapped["Product"] = relationship(
        back_populates="substitutions", foreign_keys=[product_id]
    )

    substitute_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    substitute: Mapped["Product"] = relationship(foreign_keys=[substitute_id])
